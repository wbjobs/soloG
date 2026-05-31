using ConfigCenter.Core.DTOs;
using ConfigCenter.Core.Entities;
using ConfigCenter.Core.Enums;
using ConfigCenter.Core.Interfaces;
using ConfigCenter.Infrastructure.Data;
using Microsoft.EntityFrameworkCore;

namespace ConfigCenter.Infrastructure.Services;

public class AuditService : IAuditService
{
    private readonly ConfigCenterDbContext _db;

    public AuditService(ConfigCenterDbContext db)
    {
        _db = db;
    }

    public async Task LogAsync(string action, Guid? configId, string configKey, EnvironmentType environment,
        string oldValue, string newValue, string reason, string operatorName,
        string? ipAddress = null, string? userAgent = null, CancellationToken ct = default)
    {
        var log = new AuditLog
        {
            Id = Guid.NewGuid(),
            ConfigEntryId = configId,
            ConfigKey = configKey,
            Environment = environment,
            Action = action,
            OldValue = oldValue ?? string.Empty,
            NewValue = newValue ?? string.Empty,
            ChangeReason = reason ?? string.Empty,
            Operator = operatorName ?? "system",
            CreatedAt = DateTime.UtcNow,
            IpAddress = ipAddress ?? string.Empty,
            UserAgent = userAgent ?? string.Empty
        };
        _db.AuditLogs.Add(log);
        await _db.SaveChangesAsync(ct);
    }

    public async Task<PagedResult<AuditLogDto>> QueryAsync(AuditLogQueryDto query, CancellationToken ct = default)
    {
        var q = _db.AuditLogs.AsNoTracking();

        if (query.ConfigEntryId.HasValue)
            q = q.Where(x => x.ConfigEntryId == query.ConfigEntryId.Value);
        if (!string.IsNullOrEmpty(query.ConfigKey))
            q = q.Where(x => x.ConfigKey.Contains(query.ConfigKey));
        if (query.Environment.HasValue)
            q = q.Where(x => x.Environment == query.Environment.Value);
        if (!string.IsNullOrEmpty(query.Action))
            q = q.Where(x => x.Action == query.Action);
        if (!string.IsNullOrEmpty(query.Operator))
            q = q.Where(x => x.Operator.Contains(query.Operator));
        if (query.StartTime.HasValue)
            q = q.Where(x => x.CreatedAt >= query.StartTime.Value);
        if (query.EndTime.HasValue)
            q = q.Where(x => x.CreatedAt <= query.EndTime.Value);

        var total = await q.CountAsync(ct);
        var items = await q
            .OrderByDescending(x => x.CreatedAt)
            .Skip((query.Page - 1) * query.PageSize)
            .Take(query.PageSize)
            .Select(x => new AuditLogDto
            {
                Id = x.Id,
                ConfigEntryId = x.ConfigEntryId,
                ConfigKey = x.ConfigKey,
                Environment = x.Environment,
                Action = x.Action,
                OldValue = x.OldValue,
                NewValue = x.NewValue,
                ChangeReason = x.ChangeReason,
                Operator = x.Operator,
                CreatedAt = x.CreatedAt,
                IpAddress = x.IpAddress,
                UserAgent = x.UserAgent
            })
            .ToListAsync(ct);

        return new PagedResult<AuditLogDto>
        {
            Items = items,
            Total = total,
            Page = query.Page,
            PageSize = query.PageSize
        };
    }

    public async Task<IEnumerable<AuditLogDto>> GetConfigHistoryAsync(Guid configId, CancellationToken ct = default)
    {
        return await _db.AuditLogs
            .AsNoTracking()
            .Where(x => x.ConfigEntryId == configId)
            .OrderByDescending(x => x.CreatedAt)
            .Select(x => new AuditLogDto
            {
                Id = x.Id,
                ConfigEntryId = x.ConfigEntryId,
                ConfigKey = x.ConfigKey,
                Environment = x.Environment,
                Action = x.Action,
                OldValue = x.OldValue,
                NewValue = x.NewValue,
                ChangeReason = x.ChangeReason,
                Operator = x.Operator,
                CreatedAt = x.CreatedAt,
                IpAddress = x.IpAddress,
                UserAgent = x.UserAgent
            })
            .ToListAsync(ct);
    }
}
