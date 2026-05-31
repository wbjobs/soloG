# Time Series Database (TSDB)

基于 C++ + Drogon + Eigen + RocksDB 实现的实时时序数据库，专门用于存储物联网设备上报的数据。

## 功能特性

- **多租户支持**: 数据按租户隔离，支持独立的命名空间
- **标签索引**: 支持多维标签索引，快速检索时序数据
- **降采样聚合**: 支持 1分钟、5分钟、1小时 三个级别的自动降采样
- **丰富的查询接口**: 支持范围查询和多种聚合函数 (avg/max/min/sum/count)
- **高性能持久化**: 基于 RocksDB 实现高效的数据持久化
- **Eigen 加速**: 使用 Eigen 库进行高效的数值计算

## 架构设计

```
┌───────────────────────────────────────────────────────────┐
│                     HTTP API Layer                        │
│                 (Drogon Web Framework)                    │
└─────────────────────┬─────────────────────────────────────┘
                      │
┌─────────────────────▼─────────────────────────────────────┐
│                     Query Engine                          │
│              (Range Queries, Aggregations)                │
└─────────────────────┬─────────────────────────────────────┘
                      │
┌─────────────────────▼─────────────────────────────────────┐
│                   Downsampling Engine                     │
│               (1min / 5min / 1hour buckets)               │
└─────────────────────┬─────────────────────────────────────┘
                      │
┌─────────────────────▼─────────────────────────────────────┐
│                   Tag Index Manager                       │
│              (Inverted index for tags)                    │
└─────────────────────┬─────────────────────────────────────┘
                      │
┌─────────────────────▼─────────────────────────────────────┐
│                   RocksDB Storage Engine                  │
│              (Persistent key-value storage)               │
└───────────────────────────────────────────────────────────┘
```

## 依赖要求

- C++17 编译器 (GCC 7+, Clang 5+, MSVC 2017+)
- CMake >= 3.14
- Drogon >= 1.8.0
- RocksDB >= 6.0.0
- Eigen3 >= 3.3.0
- jsoncpp >= 1.9.0

## 编译构建

```bash
mkdir build && cd build
cmake ..
make -j$(nproc)
```

## 运行

```bash
# 使用默认参数运行 (监听 0.0.0.0:8080, 数据目录 ./tsdb_data)
./bin/tsdb

# 自定义参数
./bin/tsdb --host 127.0.0.1 --port 9000 --data-dir /data/tsdb

# 禁用认证 (仅用于开发)
./bin/tsdb --no-auth

# 设置 JWT 密钥
./bin/tsdb --jwt-secret "your_secure_secret_key"
```

## 安全与认证

### JWT 认证

所有 API 接口（除 `/api/v1/login`）都需要在请求头中携带 JWT token：

```
Authorization: Bearer <your_jwt_token>
```

### 登录获取 Token

**POST** `/api/v1/login`

请求体:
```json
{
    "tenant": "iot_tenant_001",
    "username": "user001",
    "password": "password123"
}
```

响应:
```json
{
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "tenant": "iot_tenant_001",
    "expires_in": 86400
}
```

### 多租户隔离

系统强制实施租户隔离：
- 租户 ID 从 JWT token 中提取，**不**信任请求体中的 `tenant` 字段
- 即使请求体中指定了其他租户 ID，系统也会忽略并使用 token 中的租户
- 每个租户的数据完全隔离，无法跨租户访问

## API 接口

### 1. 写入数据

**POST** `/api/v1/write`

请求头:
```
Authorization: Bearer <jwt_token>
```

请求体:
```json
{
    "tenant": "iot_tenant_001",
    "metric": "temperature",
    "tags": {
        "device": "sensor_001",
        "location": "factory_a"
    },
    "value": 25.5,
    "timestamp": 1716000000000
}
```

**注意**: `tenant` 字段会被忽略，实际使用 JWT token 中的租户 ID

响应:
```json
{
    "status": "success",
    "series_id": "1234567890"
}
```

### 2. 聚合查询

**POST** `/api/v1/query`

请求体:
```json
{
    "tenant": "iot_tenant_001",
    "metric": "temperature",
    "tags": {
        "device": "sensor_001"
    },
    "start": "1716000000000",
    "end": "1716003600000",
    "aggregation": "avg",
    "downsample": "1m"
}
```

参数说明:
- `aggregation`: `avg`, `max`, `min`, `sum`, `count`
- `downsample`: `raw`, `1m`, `5m`, `1h`

响应:
```json
{
    "tenant": "iot_tenant_001",
    "metric": "temperature",
    "points": [
        {"timestamp": 1716000000000, "value": 25.5},
        {"timestamp": 1716000060000, "value": 25.7}
    ]
}
```

### 3. 原始数据查询

**POST** `/api/v1/query_raw`

请求体:
```json
{
    "tenant": "iot_tenant_001",
    "metric": "temperature",
    "tags": {
        "device": "sensor_001"
    },
    "start": "1716000000000",
    "end": "1716000100000"
}
```

## 测试

运行测试脚本:

```bash
python3 test_api.py
```

## 项目结构

```
.
├── CMakeLists.txt
├── include/tsdb/
│   ├── types.h                    # 核心类型定义
│   ├── storage/rocksdb_engine.h   # RocksDB 存储引擎
│   ├── index/tag_index.h          # 标签索引
│   ├── downsampling/downsampler.h # 降采样引擎
│   ├── query/query_engine.h       # 查询引擎
│   ├── api/http_handler.h         # HTTP API 处理器
│   └── utils/
│       ├── serializer.h           # 序列化工具
│       └── time_utils.h           # 时间工具
├── src/
│   ├── main.cpp                   # 程序入口
│   ├── storage/rocksdb_engine.cpp
│   ├── index/tag_index.cpp
│   ├── downsampling/downsampler.cpp
│   ├── query/query_engine.cpp
│   ├── api/http_handler.cpp
│   └── utils/
│       ├── serializer.cpp
│       └── time_utils.cpp
└── test_api.py                    # API 测试脚本
```

## 数据格式

### 原始数据 Key 格式

```
[tenant]\0[metric]\0[tags]\0[timestamp(8 bytes big-endian)]
```

### 降采样数据 Key 格式

```
ds\0[interval]\0[tenant]\0[metric]\0[tags]\0[bucket_timestamp]
```

### 标签索引 Key 格式

```
idx\0[tenant]\0[metric]\0[tag_key]\0[tag_value]\0[series_id]
```

## 性能优化建议

1. **批量写入**: 尽可能批量写入数据以提高吞吐量
2. **合理选择降采样粒度**: 根据查询模式选择合适的降采样间隔
3. **标签设计**: 避免高基数标签，控制标签数量
4. **RocksDB 调优**: 根据硬件配置调整 RocksDB 参数

## License

MIT License
