using ConfigCenter.Core.Entities;
using Microsoft.EntityFrameworkCore;

namespace ConfigCenter.Infrastructure.Data;

public class ConfigCenterDbContext : DbContext
{
    public ConfigCenterDbContext(DbContextOptions<ConfigCenterDbContext> options) : base(options)
    {
    }

    public DbSet<ConfigEntry> ConfigEntries { get; set; }
    public DbSet<ConfigVersion> ConfigVersions { get; set; }
    public DbSet<AuditLog> AuditLogs { get; set; }

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<ConfigEntry>(b =>
        {
            b.HasKey(e => e.Id);
            b.HasIndex(e => new { e.Key, e.Environment, e.IsDeleted })
             .IsUnique()
             .HasFilter("[IsDeleted] = 0");
            b.Property(e => e.Key).IsRequired().HasMaxLength(256);
            b.Property(e => e.Value).IsRequired();
            b.Property(e => e.Description).HasMaxLength(1024);
            b.Property(e => e.CreatedBy).HasMaxLength(64);
            b.Property(e => e.UpdatedBy).HasMaxLength(64);
        });

        modelBuilder.Entity<ConfigVersion>(b =>
        {
            b.HasKey(e => e.Id);
            b.HasIndex(e => new { e.ConfigEntryId, e.Version }).IsUnique();
            b.Property(e => e.Key).IsRequired().HasMaxLength(256);
            b.Property(e => e.Value).IsRequired();
            b.Property(e => e.ChangeReason).HasMaxLength(512);
            b.Property(e => e.CreatedBy).HasMaxLength(64);
        });

        modelBuilder.Entity<AuditLog>(b =>
        {
            b.HasKey(e => e.Id);
            b.HasIndex(e => e.ConfigEntryId);
            b.HasIndex(e => e.ConfigKey);
            b.HasIndex(e => e.Environment);
            b.HasIndex(e => e.Action);
            b.HasIndex(e => e.CreatedAt);
            b.HasIndex(e => e.Operator);
            b.Property(e => e.ConfigKey).IsRequired().HasMaxLength(256);
            b.Property(e => e.Action).IsRequired().HasMaxLength(32);
            b.Property(e => e.OldValue);
            b.Property(e => e.NewValue);
            b.Property(e => e.ChangeReason).HasMaxLength(512);
            b.Property(e => e.Operator).IsRequired().HasMaxLength(64);
            b.Property(e => e.IpAddress).HasMaxLength(64);
            b.Property(e => e.UserAgent).HasMaxLength(512);
        });
    }
}
