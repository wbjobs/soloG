namespace ConfigCenter.Core.Entities;

public class ConfigEntry
{
    public Guid Id { get; set; }
    public string Key { get; set; } = string.Empty;
    public string Value { get; set; } = string.Empty;
    public string Description { get; set; } = string.Empty;
    public Core.Enums.EnvironmentType Environment { get; set; }
    public Core.Enums.ValueType ValueType { get; set; }
    public bool IsEncrypted { get; set; }
    public int Version { get; set; }
    public bool IsDeleted { get; set; }
    public DateTime CreatedAt { get; set; }
    public DateTime UpdatedAt { get; set; }
    public string CreatedBy { get; set; } = string.Empty;
    public string UpdatedBy { get; set; } = string.Empty;
}

public class ConfigVersion
{
    public Guid Id { get; set; }
    public Guid ConfigEntryId { get; set; }
    public string Key { get; set; } = string.Empty;
    public string Value { get; set; } = string.Empty;
    public Core.Enums.EnvironmentType Environment { get; set; }
    public int Version { get; set; }
    public string ChangeReason { get; set; } = string.Empty;
    public DateTime CreatedAt { get; set; }
    public string CreatedBy { get; set; } = string.Empty;
}
