using Grpc.Core;
using Google.Protobuf.WellKnownTypes;
using ConfigCenter.Core.Interfaces;
using CoreDto = ConfigCenter.Core.DTOs;
using CoreEnum = ConfigCenter.Core.Enums;
using GrpcEnv = global::ConfigCenter.Grpc.EnvironmentType;
using GrpcValType = global::ConfigCenter.Grpc.ValueType;

namespace ConfigCenter.Grpc.Services;

public class ConfigCenterGrpcService : ConfigCenterService.ConfigCenterServiceBase
{
    private readonly IConfigService _configService;
    private readonly IConfigChangeNotifier _notifier;

    public ConfigCenterGrpcService(IConfigService configService, IConfigChangeNotifier notifier)
    {
        _configService = configService;
        _notifier = notifier;
    }

    public override async Task<ConfigEntry> GetConfig(GetConfigRequest request, ServerCallContext context)
    {
        var env = (CoreEnum.EnvironmentType)((int)request.Environment - 1);
        var config = await _configService.GetConfigAsync(request.Key, env, context.CancellationToken);
        return ToGrpcConfig(config);
    }

    public override async Task GetConfigs(GetConfigsRequest request, IServerStreamWriter<ConfigEntry> responseStream, ServerCallContext context)
    {
        var env = request.Environment == GrpcEnv.EnvironmentTypeUnspecified ? null : (CoreEnum.EnvironmentType?)((int)request.Environment - 1);
        var configs = await _configService.GetAllConfigsAsync(env, context.CancellationToken);

        foreach (var config in configs)
        {
            await responseStream.WriteAsync(ToGrpcConfig(config), context.CancellationToken);
        }
    }

    public override async Task<ConfigEntry> CreateConfig(CreateConfigRequest request, ServerCallContext context)
    {
        var dto = new CoreDto.CreateConfigDto
        {
            Key = request.Key,
            Value = request.Value,
            Description = request.Description,
            Environment = (CoreEnum.EnvironmentType)((int)request.Environment - 1),
            ValueType = (CoreEnum.ValueType)((int)request.ValueType - 1),
            IsEncrypted = request.IsEncrypted,
            CreatedBy = request.CreatedBy
        };
        var config = await _configService.CreateConfigAsync(dto, context.CancellationToken);
        return ToGrpcConfig(config);
    }

    public override async Task<ConfigEntry> UpdateConfig(UpdateConfigRequest request, ServerCallContext context)
    {
        var dto = new CoreDto.UpdateConfigDto
        {
            Value = request.Value,
            Description = request.Description,
            IsEncrypted = request.IsEncrypted,
            ChangeReason = request.ChangeReason,
            UpdatedBy = request.UpdatedBy
        };
        var config = await _configService.UpdateConfigAsync(Guid.Parse(request.Id), dto, context.CancellationToken);
        return ToGrpcConfig(config);
    }

    public override async Task<DeleteConfigResponse> DeleteConfig(DeleteConfigRequest request, ServerCallContext context)
    {
        var success = await _configService.DeleteConfigAsync(Guid.Parse(request.Id), context.CancellationToken);
        return new DeleteConfigResponse { Success = success };
    }

    public override async Task<ConfigEntry> RollbackConfig(RollbackConfigRequest request, ServerCallContext context)
    {
        var config = await _configService.RollbackConfigAsync(
            Guid.Parse(request.ConfigId),
            request.TargetVersion,
            context.CancellationToken);
        return ToGrpcConfig(config);
    }

    public override async Task<ConfigVersionsResponse> GetConfigVersions(GetVersionsRequest request, ServerCallContext context)
    {
        var versions = await _configService.GetConfigVersionsAsync(Guid.Parse(request.ConfigId), context.CancellationToken);
        var response = new ConfigVersionsResponse();
        foreach (var v in versions)
        {
            response.Versions.Add(new global::ConfigCenter.Grpc.ConfigVersion
            {
                Id = v.Id.ToString(),
                ConfigEntryId = v.ConfigEntryId.ToString(),
                Key = v.Key,
                Value = v.Value,
                Version = v.Version,
                ChangeReason = v.ChangeReason,
                CreatedAt = Timestamp.FromDateTime(v.CreatedAt),
                CreatedBy = v.CreatedBy
            });
        }
        return response;
    }

    public override async Task SubscribeConfigChanges(SubscribeRequest request, IServerStreamWriter<ConfigChangeEvent> responseStream, ServerCallContext context)
    {
        var env = (CoreEnum.EnvironmentType)((int)request.Environment - 1);
        var keyPrefix = string.IsNullOrEmpty(request.KeyPrefix) ? null : request.KeyPrefix;
        var changes = _notifier.SubscribeAsync(env, keyPrefix, context.CancellationToken);

        await foreach (var change in changes)
        {
            await responseStream.WriteAsync(new ConfigChangeEvent
            {
                ConfigId = change.ConfigId.ToString(),
                Key = change.Key,
                Value = change.Value,
                Environment = (GrpcEnv)((int)change.Environment + 1),
                Version = change.Version,
                ChangeTime = Timestamp.FromDateTime(change.ChangeTime),
                ChangeType = change.ChangeType
            }, context.CancellationToken);
        }
    }

    public override async Task<AllConfigValuesResponse> GetAllConfigValues(GetConfigsRequest request, ServerCallContext context)
    {
        var env = (CoreEnum.EnvironmentType)((int)request.Environment - 1);
        var values = await _configService.GetAllConfigValuesAsync(env, context.CancellationToken);
        var response = new AllConfigValuesResponse();
        foreach (var kvp in values)
        {
            response.Values.Add(kvp.Key, kvp.Value);
        }
        return response;
    }

    private static ConfigEntry ToGrpcConfig(CoreDto.ConfigDto config)
    {
        return new ConfigEntry
        {
            Id = config.Id.ToString(),
            Key = config.Key,
            Value = config.Value,
            Description = config.Description,
            Environment = (GrpcEnv)((int)config.Environment + 1),
            ValueType = (GrpcValType)((int)config.ValueType + 1),
            IsEncrypted = config.IsEncrypted,
            Version = config.Version,
            UpdatedAt = Timestamp.FromDateTime(config.UpdatedAt),
            UpdatedBy = config.UpdatedBy
        };
    }
}
