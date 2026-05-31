using Grpc.Net.Client;
using ConfigCenter.Grpc;

namespace ConfigCenter.Client;

public class ConfigCenterClient : IDisposable
{
    private readonly ConfigCenterService.ConfigCenterServiceClient _client;
    private readonly GrpcChannel _channel;

    public ConfigCenterClient(string address)
    {
        _channel = GrpcChannel.ForAddress(address);
        _client = new ConfigCenterService.ConfigCenterServiceClient(_channel);
    }

    public ConfigCenterClient(GrpcChannel channel)
    {
        _channel = channel;
        _client = new ConfigCenterService.ConfigCenterServiceClient(_channel);
    }

    public async Task<ConfigEntry> GetConfigAsync(string key, EnvironmentType environment, CancellationToken ct = default)
    {
        return await _client.GetConfigAsync(new GetConfigRequest { Key = key, Environment = environment }, cancellationToken: ct);
    }

    public async Task<IDictionary<string, string>> GetAllConfigValuesAsync(EnvironmentType environment, CancellationToken ct = default)
    {
        var response = await _client.GetAllConfigValuesAsync(new GetConfigsRequest { Environment = environment }, cancellationToken: ct);
        return response.Values;
    }

    public async IAsyncEnumerable<ConfigChangeEvent> SubscribeChangesAsync(EnvironmentType environment, string? keyPrefix = null, [System.Runtime.CompilerServices.EnumeratorCancellation] CancellationToken ct = default)
    {
        var call = _client.SubscribeConfigChanges(new SubscribeRequest
        {
            Environment = environment,
            KeyPrefix = keyPrefix ?? string.Empty
        }, cancellationToken: ct);

        await foreach (var change in call.ResponseStream.ReadAllAsync(ct))
        {
            yield return change;
        }
    }

    public async Task<ConfigEntry> CreateConfigAsync(CreateConfigRequest request, CancellationToken ct = default)
    {
        return await _client.CreateConfigAsync(request, cancellationToken: ct);
    }

    public async Task<ConfigEntry> UpdateConfigAsync(UpdateConfigRequest request, CancellationToken ct = default)
    {
        return await _client.UpdateConfigAsync(request, cancellationToken: ct);
    }

    public async Task<bool> DeleteConfigAsync(string id, CancellationToken ct = default)
    {
        var response = await _client.DeleteConfigAsync(new DeleteConfigRequest { Id = id }, cancellationToken: ct);
        return response.Success;
    }

    public void Dispose()
    {
        _channel?.Dispose();
    }
}
