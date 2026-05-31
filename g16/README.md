# ConfigCenter - .NET 8 配置中心服务

一个基于 .NET 8 + gRPC + SQLite 的本地优先配置中心服务。

## 功能特性

- ✅ **多环境支持**: Dev/Test/Prod 三套环境配置隔离
- ✅ **配置版本管理**: 每次修改自动保存版本，支持一键回滚
- ✅ **配置热更新**: 客户端通过 gRPC 流式订阅实时接收配置变更
- ✅ **加密存储**: 敏感配置使用 AES-256 加密存储
- ✅ **Blazor Web UI**: 现代化的管理界面，支持配置CRUD、版本查看、回滚
- ✅ **导入导出**: 支持 JSON 格式批量导入导出配置
- ✅ **本地优先**: SQLite 数据库，无外部依赖，开箱即用

## 架构设计

```
┌─────────────────────────────────────────────────────┐
│           ConfigCenter.Server (ASP.NET Core)        │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │  gRPC    │  │  Blazor  │  │  REST API (可选)  │  │
│  │  Service │  │  Web UI  │  │                  │  │
│  └────┬─────┘  └────┬─────┘  └────────┬─────────┘  │
│       │             │                  │            │
│  ┌────▼─────────────▼──────────────────▼─────────┐  │
│  │          Application Services Layer           │  │
│  │  ConfigService | ChangeNotifier | Encryption  │  │
│  │  ImportExportService                          │  │
│  └───────────────────────┬───────────────────────┘  │
│                          │                          │
│              ┌───────────▼───────────┐              │
│              │  EF Core / SQLite DB  │              │
│              └───────────────────────┘              │
└─────────────────────────────────────────────────────┘
```

## 项目结构

```
ConfigCenter/
├── src/
│   ├── ConfigCenter.Core/          # 领域模型、DTO、接口
│   ├── ConfigCenter.Infrastructure/ # 数据访问、服务实现
│   ├── ConfigCenter.Grpc/          # gRPC 服务实现 + proto 定义
│   ├── ConfigCenter.Client/        # gRPC 客户端库
│   └── ConfigCenter.Server/        # 主服务端 (Blazor + gRPC)
├── samples/
│   └── ConfigCenter.SampleClient/  # 客户端使用示例
└── ConfigCenter.sln
```

## 快速开始

### 前置要求

- .NET 8 SDK
- 可选: Visual Studio 2022 / VS Code

### 构建运行

```bash
# 1. 恢复依赖
dotnet restore

# 2. 构建
dotnet build

# 3. 运行服务端
cd src/ConfigCenter.Server
dotnet run --launch-profile https
```

服务启动后：
- Web UI: https://localhost:5001
- gRPC 服务: https://localhost:5001 (same port, HTTP/2)

### 使用示例客户端

```bash
cd samples/ConfigCenter.SampleClient
dotnet run
```

## gRPC 服务 API

| 方法 | 说明 |
|------|------|
| `GetConfig` | 获取单个配置 |
| `GetConfigs` | 流式获取配置列表 |
| `CreateConfig` | 创建配置 |
| `UpdateConfig` | 更新配置 |
| `DeleteConfig` | 删除配置 |
| `RollbackConfig` | 回滚到指定版本 |
| `GetConfigVersions` | 获取配置历史版本 |
| `SubscribeConfigChanges` | 流式订阅配置变更 |
| `GetAllConfigValues` | 获取环境所有配置键值对 |

## 客户端使用

### 安装 NuGet 包（项目内引用）

```csharp
// 在客户端项目中引用 ConfigCenter.Client
using ConfigCenter.Client;
using ConfigCenter.Grpc;

// 1. 创建客户端
using var client = new ConfigCenterClient("https://localhost:5001");

// 2. 获取配置
var config = await client.GetConfigAsync("db.connectionString", EnvironmentType.Dev);
Console.WriteLine(config.Value);

// 3. 获取所有配置
var allValues = await client.GetAllConfigValuesAsync(EnvironmentType.Dev);

// 4. 订阅配置变更（热更新）
await foreach (var change in client.SubscribeChangesAsync(EnvironmentType.Dev))
{
    Console.WriteLine($"配置变更: {change.Key} = {change.Value}");
}

// 5. 创建配置
var newConfig = await client.CreateConfigAsync(new CreateConfigRequest
{
    Key = "app.timeout",
    Value = "30",
    Environment = EnvironmentType.Dev,
    ValueType = ValueType.Int,
    IsEncrypted = false
});

// 6. 更新配置
var updated = await client.UpdateConfigAsync(new UpdateConfigRequest
{
    Id = newConfig.Id,
    Value = "60",
    ChangeReason = "调整超时时间"
});

// 7. 回滚配置
await client.RollbackConfigAsync(new RollbackConfigRequest
{
    ConfigId = newConfig.Id,
    TargetVersion = 1
});
```

## 配置说明

### appsettings.json

```json
{
  "ConnectionStrings": {
    "DefaultConnection": "Data Source=configcenter.db"
  },
  "EncryptionKey": "你的AES-256加密密钥（请修改为自己的密钥）"
}
```

**重要**: 生产环境请务必修改 `EncryptionKey`，并使用环境变量或密钥管理服务存储。

### 数据存储

- SQLite 数据库文件: `configcenter.db`
- 自动创建: 首次运行时自动创建数据库和表结构

## Web UI 功能

1. **仪表盘**: 查看各环境配置数量统计、最近更新记录
2. **配置列表**: 按环境筛选、搜索、编辑、删除、查看版本
3. **新建配置**: 支持选择环境、值类型、是否加密
4. **版本管理**: 查看历史变更、一键回滚到任意版本
5. **导入导出**: 批量导入导出 JSON 格式配置文件

## 安全特性

- AES-256 加密存储敏感配置
- 数据库层面唯一索引防止重复配置
- 支持配置软删除
- 所有变更操作留痕（版本历史）

## 本地优先设计

- 单文件 SQLite 数据库，无需外部数据库服务
- 进程内内存通知（Channel）实现配置变更广播
- 可单机部署，也可扩展为分布式部署
- 导入导出功能支持配置迁移

## 性能优化

- gRPC 流式通信减少连接开销
- 无状态服务端设计，支持水平扩展
- SQLite 适用于中小规模配置场景（建议 < 10k 配置项）
- 加密/解密使用内存流避免明文泄露

## 生产部署建议

1. 修改默认加密密钥
2. 配置 HTTPS 证书
3. 考虑使用分布式缓存替代内存通知（如 Redis Pub/Sub）
4. 定期备份 SQLite 数据库文件
5. 配置防火墙限制 gRPC 端口访问

## License

MIT
