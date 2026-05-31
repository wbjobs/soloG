using System.Text;
using System.Text.Json;
using ConfigCenter.Core.Entities;
using ConfigCenter.Core.Enums;
using ConfigCenter.Core.Interfaces;
using ConfigCenter.Infrastructure.Caching;
using ConfigCenter.Infrastructure.Data;
using Microsoft.EntityFrameworkCore;

namespace ConfigCenter.Infrastructure.Services;

public class ImportExportService : IImportExportService
{
    private readonly ConfigCenterDbContext _db;
    private readonly IEncryptionService _encryption;
    private readonly IConfigCache _cache;

    public ImportExportService(ConfigCenterDbContext db, IEncryptionService encryption, IConfigCache cache)
    {
        _db = db;
        _encryption = encryption;
        _cache = cache;
    }

    public async Task<byte[]> ExportConfigsAsync(EnvironmentType? environment = null, CancellationToken cancellationToken = default)
    {
        var query = _db.ConfigEntries.Where(c => !c.IsDeleted).AsNoTracking();
        if (environment.HasValue)
            query = query.Where(c => c.Environment == environment.Value);

        var configs = await query.ToListAsync(cancellationToken);

        var exportData = configs.Select(c => new ExportItem
        {
            Key = c.Key,
            Value = GetDecryptedValue(c),
            Description = c.Description,
            Environment = c.Environment,
            ValueType = c.ValueType,
            IsEncrypted = c.IsEncrypted,
            Version = c.Version,
            CreatedAt = c.CreatedAt,
            UpdatedAt = c.UpdatedAt,
            CreatedBy = c.CreatedBy,
            UpdatedBy = c.UpdatedBy
        }).ToList();

        var json = JsonSerializer.Serialize(exportData, new JsonSerializerOptions
        {
            WriteIndented = true,
            PropertyNamingPolicy = JsonNamingPolicy.CamelCase
        });

        return Encoding.UTF8.GetBytes(json);
    }

    public async Task<int> ImportConfigsAsync(byte[] data, bool overwrite = false, CancellationToken cancellationToken = default)
    {
        var json = Encoding.UTF8.GetString(data);
        var items = JsonSerializer.Deserialize<List<ExportItem>>(json, new JsonSerializerOptions
        {
            PropertyNameCaseInsensitive = true
        });

        if (items == null || items.Count == 0) return 0;

        var importedCount = 0;

        foreach (var item in items)
        {
            var existing = await _db.ConfigEntries
                .FirstOrDefaultAsync(c => c.Key == item.Key && c.Environment == item.Environment && !c.IsDeleted, cancellationToken);

            if (existing != null)
            {
                if (!overwrite) continue;
                existing.Value = item.IsEncrypted ? _encryption.Encrypt(item.Value) : item.Value;
                existing.Description = item.Description;
                existing.ValueType = item.ValueType;
                existing.IsEncrypted = item.IsEncrypted;
                existing.Version += 1;
                existing.UpdatedAt = DateTime.UtcNow;
                existing.UpdatedBy = "import";
                _cache.Set(existing.Key, existing.Environment, item.Value, existing.Version);
            }
            else
            {
                var config = new ConfigEntry
                {
                    Id = Guid.NewGuid(),
                    Key = item.Key,
                    Value = item.IsEncrypted ? _encryption.Encrypt(item.Value) : item.Value,
                    Description = item.Description,
                    Environment = item.Environment,
                    ValueType = item.ValueType,
                    IsEncrypted = item.IsEncrypted,
                    Version = 1,
                    IsDeleted = false,
                    CreatedAt = DateTime.UtcNow,
                    UpdatedAt = DateTime.UtcNow,
                    CreatedBy = "import",
                    UpdatedBy = "import"
                };
                _db.ConfigEntries.Add(config);
                _cache.Set(config.Key, config.Environment, item.Value, config.Version);
            }
            importedCount++;
        }

        await _db.SaveChangesAsync(cancellationToken);
        return importedCount;
    }

    private string GetDecryptedValue(ConfigEntry config)
    {
        if (!config.IsEncrypted)
            return config.Value;

        if (_cache.TryGet(config.Key, config.Environment, out var cached, out var cachedVersion))
        {
            if (cachedVersion == config.Version)
                return cached!;
        }

        var decrypted = _encryption.Decrypt(config.Value);
        _cache.Set(config.Key, config.Environment, decrypted, config.Version);
        return decrypted;
    }

    private class ExportItem
    {
        public string Key { get; set; } = string.Empty;
        public string Value { get; set; } = string.Empty;
        public string Description { get; set; } = string.Empty;
        public EnvironmentType Environment { get; set; }
        public ValueType ValueType { get; set; }
        public bool IsEncrypted { get; set; }
        public int Version { get; set; }
        public DateTime CreatedAt { get; set; }
        public DateTime UpdatedAt { get; set; }
        public string CreatedBy { get; set; } = string.Empty;
        public string UpdatedBy { get; set; } = string.Empty;
    }
}
