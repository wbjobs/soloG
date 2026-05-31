using System.Collections.Concurrent;
using ConfigCenter.Core.DTOs;
using ConfigCenter.Core.Enums;
using ConfigCenter.Core.Interfaces;

namespace ConfigCenter.Infrastructure.Services;

public class InMemoryConfigChangeNotifier : IConfigChangeNotifier
{
    private readonly ConcurrentDictionary<Guid, Subscription> _subscriptions = new();

    public Task NotifyChangeAsync(ConfigChangeEvent changeEvent, CancellationToken cancellationToken = default)
    {
        foreach (var subscription in _subscriptions.Values)
        {
            if (cancellationToken.IsCancellationRequested) break;
            if (subscription.Environment != changeEvent.Environment) continue;
            if (!string.IsNullOrEmpty(subscription.KeyPrefix) &&
                !changeEvent.Key.StartsWith(subscription.KeyPrefix, StringComparison.Ordinal)) continue;

            subscription.Writer.TryWrite(changeEvent);
        }
        return Task.CompletedTask;
    }

    public IAsyncEnumerable<ConfigChangeEvent> SubscribeAsync(EnvironmentType environment, string? keyPrefix = null,
        CancellationToken cancellationToken = default)
    {
        var subscriptionId = Guid.NewGuid();
        var channel = System.Threading.Channels.Channel.CreateUnbounded<ConfigChangeEvent>();

        var subscription = new Subscription
        {
            Id = subscriptionId,
            Environment = environment,
            KeyPrefix = keyPrefix,
            Writer = channel.Writer
        };

        _subscriptions.TryAdd(subscriptionId, subscription);

        cancellationToken.Register(() =>
        {
            _subscriptions.TryRemove(subscriptionId, out _);
            channel.Writer.TryComplete();
        });

        return channel.Reader.ReadAllAsync(cancellationToken);
    }

    private class Subscription
    {
        public Guid Id { get; set; }
        public EnvironmentType Environment { get; set; }
        public string? KeyPrefix { get; set; }
        public System.Threading.Channels.ChannelWriter<ConfigChangeEvent> Writer { get; set; } = null!;
    }
}
