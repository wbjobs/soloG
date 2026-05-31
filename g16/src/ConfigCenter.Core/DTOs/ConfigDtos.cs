using ConfigCenter.Core.Enums;

namespace ConfigCenter.Core.DTOs;

public class AuditLogDto
{
    public Guid Id { get; set; }
    public Guid? ConfigEntryId { get; set; }
    public string ConfigKey { get; set; } = string.Empty;
    public EnvironmentType Environment { get; set; }
    public string Action { get; set; } = string.Empty;
    public string OldValue { get; set; } = string.Empty;
    public string NewValue { get; set; } = string.Empty;
    public string ChangeReason { get; set; } = string.Empty;
    public string Operator { get; set; } = string.Empty;
    public DateTime CreatedAt { get; set; }
    public string IpAddress { get; set; } = string.Empty;
    public string UserAgent { get; set; } = string.Empty;
}

public class AuditLogQueryDto
{
    public Guid? ConfigEntryId { get; set; }
    public string? ConfigKey { get; set; }
    public EnvironmentType? Environment { get; set; }
    public string? Action { get; set; }
    public string? Operator { get; set; }
    public DateTime? StartTime { get; set; }
    public DateTime? EndTime { get; set; }
    public int Page { get; set; } = 1;
    public int PageSize { get; set; } = 50;
}

public class PagedResult<T>
{
    public List<T> Items { get; set; } = [];
    public int Total { get; set; }
    public int Page { get; set; }
    public int PageSize { get; set; }
}

public class DependencyDto
{
    public string SourceKey { get; set; } = string.Empty;
    public string TargetKey { get; set; } = string.Empty;
    public string ReferencePattern { get; set; } = string.Empty;
    public DependencyType Type { get; set; }
}

public enum DependencyType
{
    Direct,
    Transitive,
    Circular
}

public class DependencyGraphDto
{
    public List<string> Nodes { get; set; } = [];
    public List<DependencyDto> Edges { get; set; } = [];
    public List<string> CircularDependencies { get; set; } = [];
    public Dictionary<string, List<string>> Dependents { get; set; } = [];
    public Dictionary<string, List<string>> Dependencies { get; set; } = [];
}

public class ConfigDto
{
    public Guid Id { get; set; }
    public string Key { get; set; } = string.Empty;
    public string Value { get; set; } = string.Empty;
    public string Description { get; set; } = string.Empty;
    public EnvironmentType Environment { get; set; }
    public ValueType ValueType { get; set; }
    public bool IsEncrypted { get; set; }
    public int Version { get; set; }
    public DateTime UpdatedAt { get; set; }
    public string UpdatedBy { get; set; } = string.Empty;
}

public class CreateConfigDto
{
    public string Key { get; set; } = string.Empty;
    public string Value { get; set; } = string.Empty;
    public string Description { get; set; } = string.Empty;
    public EnvironmentType Environment { get; set; }
    public ValueType ValueType { get; set; }
    public bool IsEncrypted { get; set; }
    public string CreatedBy { get; set; } = "system";
}

public class UpdateConfigDto
{
    public string Value { get; set; } = string.Empty;
    public string Description { get; set; } = string.Empty;
    public bool IsEncrypted { get; set; }
    public string ChangeReason { get; set; } = string.Empty;
    public string UpdatedBy { get; set; } = "system";
}

public class ConfigVersionDto
{
    public Guid Id { get; set; }
    public Guid ConfigEntryId { get; set; }
    public string Key { get; set; } = string.Empty;
    public string Value { get; set; } = string.Empty;
    public int Version { get; set; }
    public string ChangeReason { get; set; } = string.Empty;
    public DateTime CreatedAt { get; set; }
    public string CreatedBy { get; set; } = string.Empty;
}

public class ConfigChangeEvent
{
    public Guid ConfigId { get; set; }
    public string Key { get; set; } = string.Empty;
    public string Value { get; set; } = string.Empty;
    public EnvironmentType Environment { get; set; }
    public int Version { get; set; }
    public DateTime ChangeTime { get; set; }
    public string ChangeType { get; set; } = string.Empty;
}
