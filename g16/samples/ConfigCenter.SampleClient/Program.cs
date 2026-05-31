using ConfigCenter.Client;
using ConfigCenter.Grpc;

Console.WriteLine("=== ConfigCenter 客户端示例 ===");
Console.WriteLine();

var serverAddress = args.Length > 0 ? args[0] : "https://localhost:5001";
Console.WriteLine($"连接到配置中心: {serverAddress}");
Console.WriteLine();

using var client = new ConfigCenterClient(serverAddress);

try
{
    await RunDemo(client);
}
catch (Exception ex)
{
    Console.WriteLine($"错误: {ex.Message}");
    Console.WriteLine("请确保配置中心服务正在运行。");
}

Console.WriteLine();
Console.WriteLine("按任意键退出...");
Console.ReadKey();

static async Task RunDemo(ConfigCenterClient client)
{
    Console.WriteLine("--- 步骤1: 创建测试配置 ---");
    try
    {
        var config = await client.CreateConfigAsync(new CreateConfigRequest
        {
            Key = "demo.connectionString",
            Value = "Server=localhost;Database=demo;User Id=sa;Password=secret123",
            Description = "演示用数据库连接字符串",
            Environment = EnvironmentType.Dev,
            ValueType = ValueType.String,
            IsEncrypted = true,
            CreatedBy = "demo"
        });
        Console.WriteLine($"创建成功: {config.Key} = {config.Value} (v{config.Version})");
    }
    catch (Exception ex)
    {
        Console.WriteLine($"创建失败（可能已存在）: {ex.Message}");
    }

    Console.WriteLine();
    Console.WriteLine("--- 步骤2: 获取单个配置 ---");
    try
    {
        var config = await client.GetConfigAsync("demo.connectionString", EnvironmentType.Dev);
        Console.WriteLine($"获取到: {config.Key} = {config.Value}");
    }
    catch (Exception ex)
    {
        Console.WriteLine($"获取失败: {ex.Message}");
    }

    Console.WriteLine();
    Console.WriteLine("--- 步骤3: 获取DEV环境所有配置 ---");
    var allValues = await client.GetAllConfigValuesAsync(EnvironmentType.Dev);
    Console.WriteLine($"DEV环境共有 {allValues.Count} 个配置:");
    foreach (var kvp in allValues.Take(5))
    {
        Console.WriteLine($"  {kvp.Key} = {kvp.Value}");
    }

    Console.WriteLine();
    Console.WriteLine("--- 步骤4: 订阅配置变更（按 Ctrl+C 停止）---");
    Console.WriteLine("在后台监听配置变更中...");
    Console.WriteLine("现在在Web UI中修改配置以查看实时推送");

    var cts = new CancellationTokenSource();
    Console.CancelKeyPress += (_, e) => { cts.Cancel(); e.Cancel = true; };

    try
    {
        await foreach (var change in client.SubscribeChangesAsync(EnvironmentType.Dev, null, cts.Token))
        {
            Console.WriteLine();
            Console.WriteLine($"收到变更 [{change.ChangeType}]");
            Console.WriteLine($"  Key: {change.Key}");
            Console.WriteLine($"  新值: {change.Value}");
            Console.WriteLine($"  版本: v{change.Version}");
            Console.WriteLine($"  时间: {change.ChangeTime.ToDateTime():yyyy-MM-dd HH:mm:ss}");
        }
    }
    catch (OperationCanceledException)
    {
        Console.WriteLine("订阅已取消");
    }
}
