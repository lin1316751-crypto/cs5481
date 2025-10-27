# 🐳 Docker Redis 配置指南

**适用场景**: Redis 运行在 Docker 容器中
**创建日期**: 2025-01-20

---

## 🎯 核心要点

当 Redis 运行在 Docker 容器中时，主要需要注意以下几点：

1. **网络连接**: 容器和主机之间的网络通信
2. **数据持久化**: Redis 数据需要映射到主机目录
3. **端口映射**: 容器端口映射到主机端口
4. **配置文件**: Redis 配置文件的挂载

---

## 📋 当前 config.yaml 配置

```yaml
redis:
  host: localhost      # ✅ 正确：Docker 端口映射到 localhost
  port: 6379          # ✅ 正确：默认 Redis 端口
  db: 0               # ✅ 正确：使用默认数据库
  password: null      # ⚠️  根据实际情况配置
```

**这个配置是正确的！** 因为 Docker 容器会将端口映射到 `localhost:6379`。

---

## 🚀 Docker Redis 启动方式

### 方式 1: 基础启动（推荐用于开发）

```powershell
# 启动 Redis 容器
docker run -d `
  --name redis-server `
  -p 6379:6379 `
  redis:6.0-alpine

# 验证运行状态
docker ps | Select-String "redis"
```

**优点**: 简单快速
**缺点**: 数据不持久化，容器删除后数据丢失

---

### 方式 2: 数据持久化启动（⭐ 推荐）

```powershell
# 创建数据目录
New-Item -ItemType Directory -Force -Path "D:\Cityu\SEMA\CS5481\project\redis_data"

# 启动 Redis 容器（Windows 路径）
docker run -d `
  --name redis-server `
  -p 6379:6379 `
  -v D:\Cityu\SEMA\CS5481\project\redis_data:/data `
  redis:6.0-alpine redis-server --appendonly yes

# 验证数据目录
Get-ChildItem D:\Cityu\SEMA\CS5481\project\redis_data
```

**Linux/macOS 版本**:

```bash
# 创建数据目录
mkdir -p redis_data

# 启动 Redis 容器
docker run -d \
  --name redis-server \
  -p 6379:6379 \
  -v $(pwd)/redis_data:/data \
  redis:6.0-alpine redis-server --appendonly yes
```

**优点**:

- ✅ 数据持久化到 `redis_data/` 目录
- ✅ 容器重启后数据不丢失
- ✅ 启用 AOF（Append Only File）持久化

---

### 方式 3: 自定义配置启动（生产环境）

#### 步骤 1: 创建 Redis 配置文件

```powershell
# 创建配置目录
New-Item -ItemType Directory -Force -Path "redis_config"
```

创建 `redis_config/redis.conf`：

```conf
# Redis 配置文件（优化版）

# 网络配置
bind 0.0.0.0
port 6379
protected-mode no

# 持久化配置
save 900 1          # 900秒内至少1个key变化则保存
save 300 10         # 300秒内至少10个key变化则保存
save 60 10000       # 60秒内至少10000个key变化则保存
appendonly yes      # 启用AOF持久化
appendfsync everysec # 每秒同步一次

# 内存配置
maxmemory 1gb       # 最大内存1GB（根据实际需求调整）
maxmemory-policy allkeys-lru  # 内存满时使用LRU淘汰

# 性能优化
tcp-backlog 511
timeout 0
tcp-keepalive 300
```

#### 步骤 2: 启动容器

```powershell
# Windows
docker run -d `
  --name redis-server `
  -p 6379:6379 `
  -v D:\Cityu\SEMA\CS5481\project\redis_data:/data `
  -v D:\Cityu\SEMA\CS5481\project\redis_config\redis.conf:/usr/local/etc/redis/redis.conf `
  redis:6.0-alpine redis-server /usr/local/etc/redis/redis.conf

# Linux/macOS
docker run -d \
  --name redis-server \
  -p 6379:6379 \
  -v $(pwd)/redis_data:/data \
  -v $(pwd)/redis_config/redis.conf:/usr/local/etc/redis/redis.conf \
  redis:6.0-alpine redis-server /usr/local/etc/redis/redis.conf
```

---

## 🔧 常用 Docker Redis 命令

### 管理命令

```powershell
# 启动 Redis 容器
docker start redis-server

# 停止 Redis 容器
docker stop redis-server

# 重启 Redis 容器
docker restart redis-server

# 删除 Redis 容器
docker rm -f redis-server

# 查看容器日志
docker logs redis-server

# 查看实时日志
docker logs -f redis-server

# 查看容器状态
docker ps -a | Select-String "redis"

# 进入容器内部
docker exec -it redis-server sh
```

### Redis 命令行操作

```powershell
# 从容器内运行 redis-cli
docker exec -it redis-server redis-cli

# 直接执行 Redis 命令
docker exec -it redis-server redis-cli ping
docker exec -it redis-server redis-cli INFO
docker exec -it redis-server redis-cli DBSIZE
docker exec -it redis-server redis-cli LLEN data_queue
```

### 数据备份和恢复

```powershell
# 备份 Redis 数据
docker exec redis-server redis-cli BGSAVE

# 复制备份文件到主机
docker cp redis-server:/data/dump.rdb ./backup_dump.rdb

# 从主机恢复数据（需要先停止容器）
docker stop redis-server
Copy-Item backup_dump.rdb redis_data/dump.rdb
docker start redis-server
```

---

## 🔍 连接验证

### 从 Python 连接测试

```python
import redis

# 测试连接
try:
    r = redis.Redis(host='localhost', port=6379, db=0)
    r.ping()
    print("✅ Redis 连接成功！")
    print(f"Redis 版本: {r.info()['redis_version']}")
    print(f"已使用内存: {r.info()['used_memory_human']}")
except Exception as e:
    print(f"❌ Redis 连接失败: {e}")
```

### 使用项目的验证脚本

```powershell
# 运行配置验证
python validate_config.py
```

---

## ⚙️ config.yaml 配置说明

### 标准配置（推荐）

```yaml
redis:
  host: localhost      # Docker 端口映射到 localhost
  port: 6379          # 映射的端口号
  db: 0               # 数据库编号（0-15）
  password: null      # 如果 Redis 设置了密码，填写在这里
  queue_name: data_queue
```

### 如果 Redis 有密码

```yaml
redis:
  host: localhost
  port: 6379
  db: 0
  password: "your_redis_password_here"  # 设置密码
  queue_name: data_queue
```

### 如果使用非标准端口

```powershell
# 启动时映射到其他端口
docker run -d `
  --name redis-server `
  -p 6380:6379 `
  redis:6.0-alpine
```

```yaml
redis:
  host: localhost
  port: 6380          # 修改为映射的端口
  db: 0
  password: null
  queue_name: data_queue
```

---

## 📊 Docker Compose 方式（推荐团队开发）

创建 `docker-compose.yml`：

```yaml
version: '3.8'

services:
  redis:
    image: redis:6.0-alpine
    container_name: redis-server
    ports:
      - "6379:6379"
    volumes:
      - ./redis_data:/data
      - ./redis_config/redis.conf:/usr/local/etc/redis/redis.conf
    command: redis-server /usr/local/etc/redis/redis.conf
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3
```

**使用方式**:

```powershell
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f redis

# 停止服务
docker-compose down

# 停止并删除数据卷
docker-compose down -v
```

---

## 🗂️ 目录结构（使用 Docker Redis）

```
project/
├── data_exports/          # 数据导出目录（已创建✅）
│   ├── .gitkeep
│   ├── README.md
│   └── archive/
│       └── .gitkeep
│
├── logs/                  # 日志目录（已创建✅）
│   └── .gitkeep
│
├── redis_data/            # Redis 数据目录（需创建）
│   ├── dump.rdb          # RDB 快照文件
│   └── appendonly.aof    # AOF 持久化文件
│
├── redis_config/          # Redis 配置目录（可选）
│   └── redis.conf        # Redis 配置文件
│
└── docker-compose.yml     # Docker Compose 配置（可选）
```

---

## ✅ 推荐的启动流程

### 第一次启动

```powershell
# 1. 创建数据目录
New-Item -ItemType Directory -Force -Path "redis_data"

# 2. 启动 Redis 容器
docker run -d `
  --name redis-server `
  -p 6379:6379 `
  -v D:\Cityu\SEMA\CS5481\project\redis_data:/data `
  redis:6.0-alpine redis-server --appendonly yes

# 3. 验证运行
docker ps
docker exec -it redis-server redis-cli ping

# 4. 测试 Python 连接
python -c "import redis; r = redis.Redis(host='localhost', port=6379); print('✅ 连接成功' if r.ping() else '❌ 连接失败')"

# 5. 运行项目
python validate_config.py
python control_center.py
```

### 后续启动

```powershell
# 如果容器存在但未运行
docker start redis-server

# 如果容器不存在，重新创建（数据仍在 redis_data/ 目录）
docker run -d `
  --name redis-server `
  -p 6379:6379 `
  -v D:\Cityu\SEMA\CS5481\project\redis_data:/data `
  redis:6.0-alpine redis-server --appendonly yes
```

---

## 🔒 .gitignore 配置

将 Redis 数据目录添加到 .gitignore：

```gitignore
# Redis 数据（Docker 挂载卷）
redis_data/
dump.rdb
appendonly.aof

# Redis 配置（如果包含敏感信息）
redis_config/redis.conf
```

---

## ⚠️ 常见问题

### Q1: 端口 6379 被占用？

```powershell
# 查看端口占用
netstat -ano | findstr :6379

# 使用其他端口
docker run -d `
  --name redis-server `
  -p 6380:6379 `
  redis:6.0-alpine

# 修改 config.yaml
redis:
  port: 6380
```

### Q2: 无法连接到 Docker Redis？

**检查清单**:

```powershell
# 1. 容器是否运行
docker ps | Select-String "redis"

# 2. 端口是否映射
docker port redis-server

# 3. 测试容器内连接
docker exec -it redis-server redis-cli ping

# 4. 测试主机连接
redis-cli -h localhost -p 6379 ping

# 5. 检查防火墙
# Windows: 控制面板 → 防火墙 → 允许应用通过防火墙
```

### Q3: 容器重启后数据丢失？

**原因**: 没有挂载数据卷
**解决**: 使用 `-v` 参数挂载数据目录（见"方式 2"）

### Q4: 内存使用过高？

```powershell
# 查看内存使用
docker exec -it redis-server redis-cli INFO memory

# 设置内存限制
docker run -d `
  --name redis-server `
  -p 6379:6379 `
  -v D:\Cityu\SEMA\CS5481\project\redis_data:/data `
  --memory="1g" `
  redis:6.0-alpine redis-server --maxmemory 1gb --maxmemory-policy allkeys-lru
```

---

## 📈 监控和优化

### 实时监控

```powershell
# 监控 Redis 命令
docker exec -it redis-server redis-cli MONITOR

# 查看慢查询
docker exec -it redis-server redis-cli SLOWLOG GET 10

# 查看客户端连接
docker exec -it redis-server redis-cli CLIENT LIST
```

### 性能统计

```powershell
# 查看统计信息
docker exec -it redis-server redis-cli INFO stats

# 查看内存碎片率
docker exec -it redis-server redis-cli INFO memory | Select-String "mem_fragmentation_ratio"
```

---

## 🎉 总结

### ✅ 你当前的配置是正确的

```yaml
redis:
  host: localhost   # ✅ Docker 端口映射到 localhost
  port: 6379       # ✅ 标准端口
```

### 📝 建议的完整启动命令

```powershell
# 创建数据目录
New-Item -ItemType Directory -Force -Path "redis_data"

# 启动 Redis（带数据持久化）
docker run -d `
  --name redis-server `
  -p 6379:6379 `
  -v D:\Cityu\SEMA\CS5481\project\redis_data:/data `
  --restart unless-stopped `
  redis:6.0-alpine redis-server --appendonly yes --maxmemory 1gb

# 验证
docker ps
python validate_config.py
```

### 🚀 现在可以直接使用

你的 `config.yaml` 不需要修改！直接运行：

```powershell
python control_center.py
```

---

**最后更新**: 2025-01-20
**Docker Redis 版本**: 6.0-alpine
**测试状态**: ✅ 已验证
