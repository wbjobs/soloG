using ConfigCenter.Core.DTOs;
using ConfigCenter.Core.Enums;

namespace ConfigCenter.Core.Interfaces;

public interface IConfigService
{
    Task<ConfigDto> GetConfigAsync(string key, EnvironmentType environment, CancellationToken cancellationToken = default);
    Task<IEnumerable<ConfigDto>> GetAllConfigsAsync(EnvironmentType? environment = null, CancellationToken cancellationToken = default);
    Task<ConfigDto> CreateConfigAsync(CreateConfigDto dto, CancellationToken cancellationToken = default);
    Task<ConfigDto> UpdateConfigAsync(Guid id, UpdateConfigDto dto, CancellationToken cancellationToken = default);
    Task<bool> DeleteConfigAsync(Guid id, CancellationToken cancellationToken = default);
    Task<ConfigDto> RollbackConfigAsync(Guid configId, int targetVersion, CancellationToken cancellationToken = default);
    Task<IEnumerable<ConfigVersionDto>> GetConfigVersionsAsync(Guid configId, CancellationToken cancellationToken = default);
    Task<IDictionary<string, string>> GetAllConfigValuesAsync(EnvironmentType environment, CancellationToken cancellationToken = default);
}

public interface IConfigChangeNotifier
{
    Task NotifyChangeAsync(ConfigChangeEvent changeEvent, CancellationToken cancellationToken = default);
    IAsyncEnumerable<ConfigChangeEvent> SubscribeAsync(EnvironmentType environment, string? keyPrefix = null, CancellationToken cancellationToken = default);
}

public interface IEncryptionService
{
    string Encrypt(string plainText);
    string Decrypt(string cipherText);
}

public interface IImportExportService
{
    Task<byte[]> ExportConfigsAsync(EnvironmentType? environment = null, CancellationToken cancellationToken = default);
    Task<int> ImportConfigsAsync(byte[] data, bool overwrite = false, CancellationToken cancellationToken = default);
}

public interface IAuditService
{
    Task LogAsync(string action, Guid? configId, string configKey, EnvironmentType environment,
        string oldValue, string newValue, string reason, string operatorName,
        string? ipAddress = null, string? userAgent = null, CancellationToken ct = default);
    Task<PagedResult<AuditLogDto>> QueryAsync(AuditLogQueryDto query, CancellationToken ct = default);
    Task<IEnumerable<AuditLogDto>> GetConfigHistoryAsync(Guid configId, CancellationToken ct = default);
}

public interface IDependencyAnalyzer
{
    Task<DependencyGraphDto> AnalyzeAsync(EnvironmentType environment, CancellationToken ct = default);
    Task<List<DependencyDto>> GetDependenciesAsync(string key, EnvironmentType environment, CancellationToken ct = default);
    Task<List<DependencyDto>> GetDependentsAsync(string key, EnvironmentType environment, CancellationToken ct = default);
    Task<List<string>> FindCircularDependenciesAsync(EnvironmentType environment, CancellationToken ct = default);
}
