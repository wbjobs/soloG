using Microsoft.Extensions.DependencyInjection;

namespace ConfigCenter.Client;

public static class ServiceCollectionExtensions
{
    public static IServiceCollection AddConfigCenterClient(this IServiceCollection services, string serverAddress)
    {
        services.AddSingleton(_ => new ConfigCenterClient(serverAddress));
        return services;
    }
}
