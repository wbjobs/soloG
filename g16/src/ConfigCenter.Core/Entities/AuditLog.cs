namespace ConfigCenter.Core.Entities;

public class AuditLog
{
    public Guid Id { get; set; }
    public Guid? ConfigEntryId { get; set; }
    public string ConfigKey { get; set; } = string.Empty;
    public Core.Enums.EnvironmentType Environment { get; set; }
    public string Action { get; set; } = string.Empty;
    public string OldValue { get; set; } = string.Empty;
    public string NewValue { get; set; } = string.Empty;
    public string ChangeReason { get; set; } = string.Empty;
    public string Operator { get; set; } = string.Empty;
    public DateTime CreatedAt { get; set; }
    public string IpAddress { get; set; } = string.Empty;
    public string UserAgent { get; set; } = string.Empty;
}
