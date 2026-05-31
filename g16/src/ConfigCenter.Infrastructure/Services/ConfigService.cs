using ConfigCenter.Core.DTOs;
using ConfigCenter.Core.Entities;
using ConfigCenter.Core.Enums;
using ConfigCenter.Core.Interfaces;
using ConfigCenter.Infrastructure.Caching;
using ConfigCenter.Infrastructure.Data;
using Microsoft.EntityFrameworkCore;

namespace ConfigCenter.Infrastructure.Services;

public class ConfigService : IConfigService
{
    private readonly ConfigCenterDbContext _db;
    private readonly IEncryptionService _encryption;
    private readonly IConfigChangeNotifier _notifier;
    private readonly IConfigCache _cache;
    private readonly IAuditService _audit;

    public ConfigService(ConfigCenterDbContext db, IEncryptionService encryption,
        IConfigChangeNotifier notifier, IConfigCache cache, IAuditService audit)
    {
        _db = db;
        _encryption = encryption;
        _notifier = notifier;
        _cache = cache;
        _audit = audit;
    }

    public async Task<ConfigDto> GetConfigAsync(string key, EnvironmentType environment, CancellationToken cancellationToken = default)
    {
        var config = await _db.ConfigEntries
            .Where(c => c.Key == key && c.Environment == environment && !c.IsDeleted)
            .AsNoTracking()
            .FirstOrDefaultAsync(cancellationToken);

        if (config == null)
            throw new KeyNotFoundException($"Config '{key}' not found for environment {environment}");

        var decryptedValue = GetDecryptedValue(config);
        return ToDto(config, decryptedValue);
    }

    public async Task<IEnumerable<ConfigDto>> GetAllConfigsAsync(EnvironmentType? environment = null, CancellationToken cancellationToken = default)
    {
        var query = _db.ConfigEntries.Where(c => !c.IsDeleted).AsNoTracking();
        if (environment.HasValue)
            query = query.Where(c => c.Environment == environment.Value);

        var configs = await query.ToListAsync(cancellationToken);
        return configs.Select(c => ToDto(c, GetDecryptedValue(c)));
    }

    public async Task<IDictionary<string, string>> GetAllConfigValuesAsync(EnvironmentType environment, CancellationToken cancellationToken = default)
    {
        var configs = await _db.ConfigEntries
            .Where(c => c.Environment == environment && !c.IsDeleted)
            .AsNoTracking()
            .Select(c => new { c.Key, c.Value, c.IsEncrypted, c.Version })
            .ToListAsync(cancellationToken);

        var result = new Dictionary<string, string>(configs.Count);
        foreach (var c in configs)
        {
            var value = GetDecryptedValue(c.Key, environment, c.Value, c.IsEncrypted, c.Version);
            result[c.Key] = value;
        }
        return result;
    }

    public async Task<ConfigDto> CreateConfigAsync(CreateConfigDto dto, CancellationToken cancellationToken = default)
    {
        var existing = await _db.ConfigEntries
            .AnyAsync(c => c.Key == dto.Key && c.Environment == dto.Environment && !c.IsDeleted, cancellationToken);

        if (existing)
            throw new InvalidOperationException($"Config '{dto.Key}' already exists for environment {dto.Environment}");

        var config = new ConfigEntry
        {
            Id = Guid.NewGuid(),
            Key = dto.Key,
            Value = dto.IsEncrypted ? _encryption.Encrypt(dto.Value) : dto.Value,
            Description = dto.Description,
            Environment = dto.Environment,
            ValueType = dto.ValueType,
            IsEncrypted = dto.IsEncrypted,
            Version = 1,
            IsDeleted = false,
            CreatedAt = DateTime.UtcNow,
            UpdatedAt = DateTime.UtcNow,
            CreatedBy = dto.CreatedBy,
            UpdatedBy = dto.CreatedBy
        };

        _db.ConfigEntries.Add(config);
        await SaveVersion(config, "Initial version", dto.CreatedBy, cancellationToken);
        await _db.SaveChangesAsync(cancellationToken);

        _cache.Set(config.Key, config.Environment, dto.Value, config.Version);

        await _audit.LogAsync(
            action: "Create",
            configId: config.Id,
            configKey: config.Key,
            environment: config.Environment,
            oldValue: string.Empty,
            newValue: dto.Value,
            reason: dto.Description,
            operatorName: dto.CreatedBy,
            ct: cancellationToken);

        return ToDto(config, dto.Value);
    }

    public async Task<ConfigDto> UpdateConfigAsync(Guid id, UpdateConfigDto dto, CancellationToken cancellationToken = default)
    {
        var config = await _db.ConfigEntries.FindAsync([id], cancellationToken);
        if (config == null || config.IsDeleted)
            throw new KeyNotFoundException($"Config with id {id} not found");

        var oldDecrypted = GetDecryptedValue(config);
        var newValue = dto.IsEncrypted ? _encryption.Encrypt(dto.Value) : dto.Value;

        config.Value = newValue;
        config.Description = dto.Description;
        config.IsEncrypted = dto.IsEncrypted;
        config.Version += 1;
        config.UpdatedAt = DateTime.UtcNow;
        config.UpdatedBy = dto.UpdatedBy;

        await SaveVersion(config, dto.ChangeReason, dto.UpdatedBy, cancellationToken);
        await _db.SaveChangesAsync(cancellationToken);

        _cache.Set(config.Key, config.Environment, dto.Value, config.Version);

        var changeEvent = new ConfigChangeEvent
        {
            ConfigId = config.Id,
            Key = config.Key,
            Value = dto.Value,
            Environment = config.Environment,
            Version = config.Version,
            ChangeTime = DateTime.UtcNow,
            ChangeType = "Updated"
        };
        await _notifier.NotifyChangeAsync(changeEvent, cancellationToken);

        await _audit.LogAsync(
            action: "Update",
            configId: config.Id,
            configKey: config.Key,
            environment: config.Environment,
            oldValue: oldDecrypted,
            newValue: dto.Value,
            reason: dto.ChangeReason,
            operatorName: dto.UpdatedBy,
            ct: cancellationToken);

        return ToDto(config, dto.Value);
    }

    public async Task<bool> DeleteConfigAsync(Guid id, CancellationToken cancellationToken = default)
    {
        var config = await _db.ConfigEntries.FindAsync([id], cancellationToken);
        if (config == null || config.IsDeleted) return false;

        var oldDecrypted = GetDecryptedValue(config);

        config.IsDeleted = true;
        config.UpdatedAt = DateTime.UtcNow;

        _cache.Invalidate(config.Key, config.Environment);

        var changeEvent = new ConfigChangeEvent
        {
            ConfigId = config.Id,
            Key = config.Key,
            Value = string.Empty,
            Environment = config.Environment,
            Version = config.Version,
            ChangeTime = DateTime.UtcNow,
            ChangeType = "Deleted"
        };
        await _notifier.NotifyChangeAsync(changeEvent, cancellationToken);

        await _db.SaveChangesAsync(cancellationToken);

        await _audit.LogAsync(
            action: "Delete",
            configId: config.Id,
            configKey: config.Key,
            environment: config.Environment,
            oldValue: oldDecrypted,
            newValue: string.Empty,
            reason: "Config deleted",
            operatorName: config.UpdatedBy,
            ct: cancellationToken);

        return true;
    }

    public async Task<ConfigDto> RollbackConfigAsync(Guid configId, int targetVersion, CancellationToken cancellationToken = default)
    {
        var config = await _db.ConfigEntries.FindAsync([configId], cancellationToken);
        if (config == null || config.IsDeleted)
            throw new KeyNotFoundException($"Config with id {configId} not found");

        var version = await _db.ConfigVersions
            .FirstOrDefaultAsync(v => v.ConfigEntryId == configId && v.Version == targetVersion, cancellationToken);

        if (version == null)
            throw new KeyNotFoundException($"Version {targetVersion} not found for config {configId}");

        var oldDecrypted = GetDecryptedValue(config);
        var rollbackValue = version.Value;

        config.Value = version.Value;
        config.Version += 1;
        config.UpdatedAt = DateTime.UtcNow;

        await SaveVersion(config, $"Rollback to v{targetVersion}", "rollback", cancellationToken);
        await _db.SaveChangesAsync(cancellationToken);

        var decryptedValue = config.IsEncrypted ? _encryption.Decrypt(config.Value) : config.Value;
        _cache.Set(config.Key, config.Environment, decryptedValue, config.Version);

        var changeEvent = new ConfigChangeEvent
        {
            ConfigId = config.Id,
            Key = config.Key,
            Value = decryptedValue,
            Environment = config.Environment,
            Version = config.Version,
            ChangeTime = DateTime.UtcNow,
            ChangeType = "Rollback"
        };
        await _notifier.NotifyChangeAsync(changeEvent, cancellationToken);

        await _audit.LogAsync(
            action: "Rollback",
            configId: config.Id,
            configKey: config.Key,
            environment: config.Environment,
            oldValue: oldDecrypted,
            newValue: decryptedValue,
            reason: $"Rollback to version {targetVersion}",
            operatorName: "rollback",
            ct: cancellationToken);

        return ToDto(config, decryptedValue);
    }

    public async Task<IEnumerable<ConfigVersionDto>> GetConfigVersionsAsync(Guid configId, CancellationToken cancellationToken = default)
    {
        var versions = await _db.ConfigVersions
            .Where(v => v.ConfigEntryId == configId)
            .OrderByDescending(v => v.Version)
            .AsNoTracking()
            .ToListAsync(cancellationToken);

        return versions.Select(v => new ConfigVersionDto
        {
            Id = v.Id,
            ConfigEntryId = v.ConfigEntryId,
            Key = v.Key,
            Value = v.Value,
            Version = v.Version,
            ChangeReason = v.ChangeReason,
            CreatedAt = v.CreatedAt,
            CreatedBy = v.CreatedBy
        });
    }

    private string GetDecryptedValue(ConfigEntry config)
    {
        return GetDecryptedValue(config.Key, config.Environment, config.Value, config.IsEncrypted, config.Version);
    }

    private string GetDecryptedValue(string key, EnvironmentType environment, string encryptedValue, bool isEncrypted, int version)
    {
        if (!isEncrypted)
            return encryptedValue;

        if (_cache.TryGet(key, environment, out var cached, out var cachedVersion))
        {
            if (cachedVersion == version)
                return cached!;
        }

        var decrypted = _encryption.Decrypt(encryptedValue);
        _cache.Set(key, environment, decrypted, version);
        return decrypted;
    }

    private async Task SaveVersion(ConfigEntry config, string reason, string by, CancellationToken ct)
    {
        var version = new ConfigVersion
        {
            Id = Guid.NewGuid(),
            ConfigEntryId = config.Id,
            Key = config.Key,
            Value = config.Value,
            Environment = config.Environment,
            Version = config.Version,
            ChangeReason = reason,
            CreatedAt = DateTime.UtcNow,
            CreatedBy = by
        };
        await _db.ConfigVersions.AddAsync(version, ct);
    }

    private static ConfigDto ToDto(ConfigEntry config, string decryptedValue)
    {
        return new ConfigDto
        {
            Id = config.Id,
            Key = config.Key,
            Value = decryptedValue,
            Description = config.Description,
            Environment = config.Environment,
            ValueType = config.ValueType,
            IsEncrypted = config.IsEncrypted,
            Version = config.Version,
            UpdatedAt = config.UpdatedAt,
            UpdatedBy = config.UpdatedBy
        };
    }
}
