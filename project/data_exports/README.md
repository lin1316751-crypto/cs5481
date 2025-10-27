# 📂 数据导出目录说明

此目录用于存储从 Redis 导出的财经数据文件。

## 📁 目录结构

```
data_exports/
├── .gitkeep                           # Git 目录占位符
├── README.md                          # 本说明文件
├── export_YYYYMMDD_HHMMSS.json       # JSON 格式导出文件
├── export_YYYYMMDD_HHMMSS.parquet    # Parquet 格式导出文件
└── archive/                           # 归档子目录
    ├── .gitkeep                       # Git 目录占位符
    └── export_YYYYMMDD.parquet.gz    # 压缩归档文件
```

## 📊 文件说明

### JSON 导出文件
- **命名格式**: `export_YYYYMMDD_HHMMSS.json`
- **用途**: 人类可读的数据格式，便于检查和调试
- **大小**: 约 5-10MB/万条数据
- **保留期**: 根据 `config.yaml` 中的 `retention_days` 配置（默认 90 天）

### Parquet 导出文件
- **命名格式**: `export_YYYYMMDD_HHMMSS.parquet`
- **用途**: 高效的列式存储格式，适合大数据分析
- **大小**: 约 1-2MB/万条数据（压缩率 50-80%）
- **保留期**: 根据 `config.yaml` 中的 `retention_days` 配置（默认 90 天）
- **优势**: 
  - 压缩率高，节省存储空间
  - 读取速度快，适合 pandas/spark 分析
  - 支持列裁剪，只读取需要的字段

### 归档文件（archive/）
- **命名格式**: `export_YYYYMMDD.parquet.gz`
- **用途**: 长期归档的历史数据
- **大小**: 约 0.5-1MB/万条数据（gzip 再压缩）
- **保留期**: 90 天（3 个月）

## 🔄 自动导出触发条件

根据 `config.yaml` 配置，系统会在以下情况自动导出：

1. **队列长度触发**: Redis 队列长度超过 `queue_threshold`（默认 50 万条）
2. **内存触发**: Redis 内存使用超过 `memory_threshold_mb`（默认 900MB）
3. **定时触发**: 每隔 `time_interval_minutes`（默认 1440 分钟 = 24 小时）

## 📈 预期数据量

基于配置的数据源和抓取频率：

| 时间周期 | 数据量 | JSON 大小 | Parquet 大小 |
|---------|--------|-----------|--------------|
| 1 小时 | ~2,700 条 | ~1.5 MB | ~0.5 MB |
| 1 天 | ~64,000 条 | ~35 MB | ~10 MB |
| 1 周 | ~448,000 条 | ~245 MB | ~70 MB |
| 1 月 | ~1,920,000 条 | ~1 GB | ~300 MB |

## 🛠️ 使用方式

### 手动导出
```python
from utils.data_exporter import DataExporter
from utils.redis_client import RedisClient
import yaml

# 加载配置
with open('config.yaml') as f:
    config = yaml.safe_load(f)

# 创建 Redis 客户端
redis_client = RedisClient(**config['redis'])

# 创建导出器
exporter = DataExporter(redis_client, export_dir='data_exports')

# 执行导出（保留最新 10 万条在 Redis）
result = exporter.export_and_trim(max_keep=100000)

print(f"导出了 {result['exported']} 条数据")
print(f"文件路径: {result['file']}")
```

### 读取导出数据

#### 读取 JSON 文件
```python
import json

with open('data_exports/export_20250120_120000.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"共 {len(data)} 条数据")
```

#### 读取 Parquet 文件
```python
import pandas as pd

df = pd.read_parquet('data_exports/export_20250120_120000.parquet')

print(f"共 {len(df)} 条数据")
print(df.head())

# 按数据源分组统计
print(df['source'].value_counts())

# 按时间分析
df['timestamp'] = pd.to_datetime(df['timestamp'])
print(df.groupby(df['timestamp'].dt.date).size())
```

## 🗑️ 清理策略

系统会自动清理超过保留期的文件：

1. **自动清理**: 每次导出时会检查并删除超过 `retention_days` 的文件
2. **手动清理**: 运行 `python utils/clean_exports.py` 手动清理

## 📝 注意事项

1. **磁盘空间**: 确保有足够的磁盘空间存储导出文件（建议预留 10GB+）
2. **备份建议**: 定期将归档文件备份到云存储（S3, Azure Blob, Google Cloud Storage 等）
3. **性能影响**: 导出过程可能需要 10-30 秒，期间 Redis 仍可正常写入
4. **数据完整性**: 导出的是快照数据，不影响 Redis 中的实时数据

## 🔒 .gitignore 配置

此目录下的实际数据文件不应提交到 Git：

```gitignore
# 忽略所有导出文件
data_exports/*.json
data_exports/*.parquet
data_exports/*.csv
data_exports/*.gz

# 忽略归档文件
data_exports/archive/*

# 但保留目录结构
!data_exports/.gitkeep
!data_exports/archive/.gitkeep
!data_exports/README.md
```

---

**最后更新**: 2025-01-20  
**相关配置**: `config.yaml` → `data_management` 部分
