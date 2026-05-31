# 实时日志分析平台

基于 Django + Django Channels + Redis + Celery + ClickHouse 构建的实时日志分析平台。

## 功能特性

- 🔄 **多协议接收**: 支持 HTTP (JSON/Text) 和 Syslog (UDP/TCP) 格式日志
- ⚡ **实时处理**: 基于 Celery 异步解析日志，WebSocket 实时推送
- 📊 **强大存储**: ClickHouse 列式存储，支持海量日志快速查询
- 🔍 **全文搜索**: 支持日志内容全文搜索
- 🎯 **字段过滤**: 按级别、来源、主机、时间范围多维度过滤
- 📈 **聚合统计**: 支持按时间、级别、来源等多维度聚合分析
- 🎨 **可视化仪表盘**: ECharts 图表展示，HTMX + Alpine.js 轻量级交互

## 技术栈

| 组件 | 用途 |
|------|------|
| Django 4.2 | Web 框架 |
| Django Channels | WebSocket 实时通信 |
| Redis | 消息队列 + Channel Layer |
| Celery | 异步任务处理 |
| ClickHouse | 日志存储与分析 |
| HTMX | 前端轻量交互 |
| Alpine.js | 前端响应式框架 |
| ECharts | 图表可视化 |
| Tailwind CSS | 样式框架 |

## 项目结构

```
g15/
├── logplatform/              # Django 项目配置
│   ├── __init__.py
│   ├── settings.py          # 主配置文件
│   ├── urls.py              # 路由配置
│   ├── asgi.py              # ASGI 入口 (支持 WebSocket)
│   ├── wsgi.py              # WSGI 入口
│   └── celery.py            # Celery 配置 (含定时任务)
├── logs/                     # 日志应用
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py            # 告警规则/通道/事件模型
│   ├── clickhouse_client.py # ClickHouse 客户端
│   ├── parsers.py           # 日志解析器 (Syslog/Nginx/JSON)
│   ├── notifications.py     # 通知发送器 (钉钉/邮件/Webhook/飞书)
│   ├── alert_engine.py      # 告警引擎 (规则评估/Top N 聚合)
│   ├── tasks.py             # Celery 任务 (日志处理/告警检查)
│   ├── views.py             # API 视图
│   ├── urls.py              # 应用路由
│   ├── consumers.py         # WebSocket 消费者
│   ├── routing.py           # WebSocket 路由
│   ├── signals.py           # Django 信号
│   └── management/
│       └── commands/
│           ├── init_clickhouse.py
│           ├── syslog_server.py
│           └── generate_test_logs.py
├── templates/
│   ├── dashboard.html       # 主仪表盘
│   ├── alerts.html          # 告警管理页面
│   └── aggregation.html     # Top N 聚合分析页面
├── static/                  # 静态文件目录
├── requirements.txt
├── .env.example
├── test_log_sender.py       # 测试日志发送脚本
└── manage.py
```

## 快速开始

### 1. 环境准备

确保已安装以下服务：
- Redis 6+
- ClickHouse 23+
- Python 3.10+

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，配置 Redis、ClickHouse 连接信息
```

### 4. 初始化数据库

```bash
# 初始化 Django 数据库
python manage.py migrate

# 初始化 ClickHouse
python manage.py init_clickhouse
```

### 5. 启动服务

需要同时启动以下服务（建议使用多个终端）：

**终端 1 - Django ASGI 服务器:**
```bash
uvicorn logplatform.asgi:application --host 0.0.0.0 --port 8000 --reload
```

**终端 2 - Celery Worker:**
```bash
celery -A logplatform worker --loglevel=info
```

**终端 3 - Syslog 服务器 (可选):**
```bash
python manage.py syslog_server --port 5140
```

### 6. 生成测试数据

```bash
# 生成 100 条 JSON 格式测试日志
python manage.py generate_test_logs --count 100 --format json

# 或使用测试脚本持续发送
python test_log_sender.py
```

### 7. 访问仪表盘

打开浏览器访问: `http://localhost:8000`

## API 文档

### 日志接收

#### HTTP JSON 日志
```http
POST /api/v1/logs/http
Content-Type: application/json

{
    "timestamp": "2024-01-01T12:00:00",
    "hostname": "web-01",
    "source": "nginx",
    "level": "info",
    "message": "Request completed",
    "request_id": "req-12345"
}
```

#### HTTP 批量日志
```http
POST /api/v1/logs/http
Content-Type: application/json

[
    {"level": "info", "message": "log 1"},
    {"level": "error", "message": "log 2"}
]
```

#### HTTP Text 日志
```http
POST /api/v1/logs/http
Content-Type: text/plain

2024-01-01T12:00:00 [INFO] nginx: Request processed
```

#### Syslog HTTP
```http
POST /api/v1/logs/syslog
Content-Type: text/plain

<134>1 2024-01-01T12:00:00 web-01 nginx - - - Request completed
```

### 日志查询

#### 游标分页说明
> **重要**: 本 API 使用游标分页（Keyset Pagination）而非 OFFSET 分页，避免翻页到第 100 页以后的性能问题。基于 `timestamp` 字段作为游标，查询性能稳定。

#### 搜索日志（首页）
```http
GET /api/v1/logs/search?q=error&limit=100
```

#### 加载下一页（向后翻，获取更旧的日志）
```http
GET /api/v1/logs/search?q=error&limit=100&last_timestamp=2024-01-01T12:00:00&last_source=nginx&last_severity=6&direction=backward
```

#### 向前翻页（获取更新的日志）
```http
GET /api/v1/logs/search?limit=100&last_timestamp=2024-01-01T12:00:00&direction=forward
```

#### 响应格式
```json
{
    "status": "success",
    "logs": [...],
    "count": 100,
    "cursor": {
        "last_timestamp": "2024-01-01T11:55:00",
        "last_source": "nginx",
        "last_severity": 6
    },
    "has_more": true
}
```

#### 请求参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `q` | string | 搜索关键词（在 message 和 raw 字段中模糊搜索） |
| `severity` | int | 按日志级别过滤 (0-7) |
| `source` | string | 按日志来源过滤 |
| `hostname` | string | 按主机名过滤 |
| `start_time` | string | 开始时间 (ISO 8601) |
| `end_time` | string | 结束时间 (ISO 8601) |
| `limit` | int | 每页数量，默认 100，最大 500 |
| `last_timestamp` | string | 上一页最后一条的时间戳（游标） |
| `last_source` | string | 上一页最后一条的来源（用于精确游标） |
| `last_severity` | int | 上一页最后一条的级别（用于精确游标） |
| `direction` | string | `backward`=向后翻（更旧）, `forward`=向前翻（更新） |

#### 响应字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `logs` | array | 日志列表 |
| `count` | int | 当前返回的日志数量 |
| `cursor` | object | 当前页最后一条的游标，用于获取下一页 |
| `has_more` | bool | 是否还有更多数据 |

#### 聚合统计
```http
GET /api/v1/logs/aggregate?field=severity
GET /api/v1/logs/aggregate?field=source&limit=10
GET /api/v1/logs/aggregate?field=time&limit=60
```

#### 获取统计信息
```http
GET /api/v1/stats
```

### WebSocket 实时推送

连接地址: `ws://localhost:8000/ws/logs/`

接收消息格式:
```json
{
    "type": "log",
    "log": {
        "timestamp": "2024-01-01T12:00:00",
        "hostname": "web-01",
        "source": "nginx",
        "severity": 6,
        "severity_name": "Info",
        "message": "...",
        "tags": ["nginx"],
        "fields": {},
        "raw": "..."
    }
}
```

## 日志级别

| 级别 | 数值 | 名称 |
|------|------|------|
| Emergency | 0 | 紧急 |
| Alert | 1 | 警报 |
| Critical | 2 | 严重 |
| Error | 3 | 错误 |
| Warning | 4 | 警告 |
| Notice | 5 | 通知 |
| Info | 6 | 信息 |
| Debug | 7 | 调试 |

## 支持的日志格式

### 1. JSON 格式
```json
{
    "timestamp": "ISO 8601",
    "hostname": "主机名",
    "source": "来源",
    "level": "info/error/warning...",
    "message": "日志消息",
    "tags": ["tag1", "tag2"],
    "自定义字段": "值"
}
```

### 2. Syslog RFC 5424
```
<优先级>版本 时间戳 主机名 应用名 进程ID 消息ID 结构化数据 消息
<134>1 2024-01-01T12:00:00 web-01 nginx 1234 - - Request completed
```

### 3. Syslog RFC 3164
```
<优先级>时间戳 主机名 消息
<134>Jan  1 12:00:00 web-01 nginx[1234]: Request completed
```

### 4. Nginx Access Log
```
192.168.1.1 - - [01/Jan/2024:12:00:00 +0000] "GET /api HTTP/1.1" 200 1234 "-" "Mozilla/5.0"
```

## 配置 Syslog 转发

### Linux rsyslog
编辑 `/etc/rsyslog.d/99-remote.conf`:
```
*.* @@localhost:5140
```

重启服务:
```bash
systemctl restart rsyslog
```

## ClickHouse 表结构

```sql
CREATE TABLE logs (
    timestamp DateTime64(3, 'Asia/Shanghai'),
    hostname String,
    source String,
    severity UInt8,
    facility UInt8,
    message String,
    tags Array(String),
    fields Map(String, String),
    raw String
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (timestamp, source, severity)
```

## 告警规则引擎

### 功能说明

告警规则引擎支持配置灵活的告警条件，当满足条件时自动通过多种通道发送通知。

### 告警规则配置

| 字段 | 说明 |
|------|------|
| `name` | 规则名称 |
| `query` | 搜索关键词（在 message/raw 中匹配） |
| `filter_severity` | 按日志级别过滤 (0-7) |
| `filter_source` | 按日志来源过滤 |
| `filter_hostname` | 按主机名过滤 |
| `aggregation` | 聚合方式: `count` |
| `operator` | 比较符: `gt`, `gte`, `lt`, `lte`, `eq`, `neq` |
| `threshold` | 阈值 |
| `window_minutes` | 时间窗口（分钟） |
| `cooldown_minutes` | 冷却时间（分钟） |
| `channel_ids` | 通知通道 ID 列表 |
| `is_enabled` | 是否启用 |

### 示例规则

**5分钟内错误日志 > 10条**:
```json
{
    "name": "错误日志激增",
    "description": "5分钟内错误日志超过10条",
    "filter_severity": 3,
    "aggregation": "count",
    "operator": "gt",
    "threshold": 10,
    "window_minutes": 5,
    "cooldown_minutes": 10,
    "channel_ids": [1, 2]
}
```

**包含 error 关键词的日志 > 50条**:
```json
{
    "name": "error关键词告警",
    "query": "error",
    "aggregation": "count",
    "operator": "gt",
    "threshold": 50,
    "window_minutes": 10,
    "cooldown_minutes": 15,
    "channel_ids": [1]
}
```

### 通知通道

支持以下通知类型：

| 类型 | 配置项 |
|------|--------|
| **Webhook** | `webhook_url` |
| **钉钉** | `webhook_url`, `secret` (可选) |
| **飞书** | `webhook_url`, `secret` (可选) |
| **邮件** | `email_to`, `email_subject_prefix` |

邮件通知需要在 settings.py 中配置 `EMAIL_CONFIG`:
```python
EMAIL_CONFIG = {
    'host': 'smtp.example.com',
    'port': 465,
    'user': 'alert@example.com',
    'password': 'password',
    'from': 'alert@example.com',
}
```

### 告警 API

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/v1/alerts/channels` | GET | 获取所有通知通道 |
| `/api/v1/alerts/channels/create` | POST | 创建通知通道 |
| `/api/v1/alerts/channels/:id/update` | POST | 更新通知通道 |
| `/api/v1/alerts/channels/:id/delete` | POST | 删除通知通道 |
| `/api/v1/alerts/rules` | GET | 获取所有告警规则 |
| `/api/v1/alerts/rules/create` | POST | 创建告警规则 |
| `/api/v1/alerts/rules/:id/update` | POST | 更新告警规则 |
| `/api/v1/alerts/rules/:id/delete` | POST | 删除告警规则 |
| `/api/v1/alerts/rules/:id/toggle` | POST | 启用/禁用规则 |
| `/api/v1/alerts/rules/:id/silent` | POST | 静默规则 |
| `/api/v1/alerts/rules/test` | POST | 测试规则 |
| `/api/v1/alerts/events` | GET | 获取告警事件列表 |

### 启动告警检查

Celery Beat 会自动每分钟检查一次所有告警规则：

```bash
celery -A logplatform beat --loglevel=info
```

## Top N 聚合分析

### API 接口

```
GET /api/v1/logs/topn?field=<field>&limit=<N>&start_time=<time>&end_time=<time>
```

### 支持的字段

| 字段 | 说明 |
|------|------|
| `source` | 按日志来源分组 |
| `hostname` | 按主机名分组 |
| `severity` | 按日志级别分组 |
| `tag` | 按标签分组 |

### 示例

**获取最近1小时来源 Top 10**:
```
GET /api/v1/logs/topn?field=source&limit=10
```

**获取最近24小时级别分布**:
```
GET /api/v1/logs/topn?field=severity
```

### 前端页面

访问 `/aggregation` 查看可视化的 Top N 聚合分析，包括：
- 日志来源 Top N 柱状图
- 主机名 Top N 柱状图
- 日志级别分布环形图
- 标签 Top N 柱状图
- 时间趋势折线图

支持选择时间范围（15分钟/1小时/6小时/24小时/7天）和 Top N 数量（5/10/20/50）。

## 常见问题

### 1. ClickHouse 连接失败
确保 ClickHouse 服务已启动，并且配置的端口正确（默认 9000）。

### 2. WebSocket 连接失败
确保使用 ASGI 服务器（uvicorn/daphne）而不是 WSGI 服务器。

### 3. Celery 任务不执行
检查 Redis 连接是否正常，Celery Worker 是否启动。

## 生产部署建议

1. 使用 Gunicorn + Uvicorn 部署 Django
2. 使用 Supervisor 管理 Celery Worker
3. 配置 Nginx 反向代理，支持 WebSocket
4. ClickHouse 配置集群模式
5. 配置适当的日志保留策略
6. 添加认证和授权机制

## License

MIT
