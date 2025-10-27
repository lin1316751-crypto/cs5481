# 🗄️ Redis 存储优化方案

**问题:** Redis 是内存数据库，存储太多数据会占用大量内存  
**目标:** 优化存储策略，自动备份到本地文件

---

## 📊 存储问题分析

### 当前情况

假设每天抓取 **2,000 篇** RSS 文章，每篇平均 **2KB**：

```
每天数据量 = 2,000 × 2KB = 4MB
每周数据量 = 4MB × 7 = 28MB
每月数据量 = 4MB × 30 = 120MB
```

加上其他数据源（Reddit, Twitter, StockTwits, NewsAPI）：

```
Reddit: 48,000条 × 1KB = 48MB/天
NewsAPI: 100条 × 2KB = 0.2MB/天
StockTwits: 8,640条 × 0.5KB = 4.3MB/天
Twitter: 5,760条 × 0.3KB = 1.7MB/天
RSS: 2,000条 × 2KB = 4MB/天
─────────────────────────────
总计: 约 58MB/天 = 1.74GB/月
```

**问题:**
- ❌ Redis 全部存储会占用 **1.74GB 内存/月**
- ❌ 历史数据价值递减（7天前的数据很少用）
- ❌ 没有自动清理机制

---

## 🎯 优化策略

### 策略 1: 分层存储 ⭐⭐⭐⭐⭐（推荐）

```
┌─────────────────────────────────────┐
│  Redis (热数据 - 最近24小时)         │  <- 快速访问
│  大小: ~60MB                         │
└─────────────────────────────────────┘
           ↓ 自动导出
┌─────────────────────────────────────┐
│  本地文件 (温数据 - 最近7天)         │  <- 按需加载
│  格式: JSON/Parquet                  │
│  大小: ~400MB                        │
└─────────────────────────────────────┘
           ↓ 定期压缩
┌─────────────────────────────────────┐
│  压缩归档 (冷数据 - 7天以上)         │  <- 长期存储
│  格式: .tar.gz                       │
│  大小: ~50MB (压缩后)                │
└─────────────────────────────────────┘
```

**优点:**
- ✅ Redis 只保留 24 小时数据（约 60MB）
- ✅ 节省内存 **96.6%**
- ✅ 历史数据不丢失
- ✅ 查询性能高（热数据在内存）

---

### 策略 2: 字段精简 ⭐⭐⭐⭐

**问题:** 17个字段占用空间大

**优化:** Redis 只存必要字段，完整数据存本地

```python
# Redis 存储 (精简版 - 7个字段)
redis_data = {
    'title': '...',        # 必须
    'url': '...',          # 必须
    'published': 123456,   # 必须
    'source': 'rss',       # 必须
    'feed_category': '...', # 筛选用
    'language': 'en',      # 筛选用
    'summary': '...'       # 预览用
}

# 本地文件存储 (完整版 - 17个字段)
local_data = {
    # ... 所有17个字段
}
```

**节省:** 每条数据从 2KB → 0.8KB，**节省 60%**

---

### 策略 3: TTL 自动过期 ⭐⭐⭐

**原理:** 使用 Redis 的 TTL (Time To Live) 功能

```python
# 设置24小时后自动删除
redis_client.setex(
    key='data:12345',
    time=86400,  # 24小时 = 86400秒
    value=json_data
)
```

**优点:**
- ✅ 自动清理
- ✅ 无需手动管理
- ✅ 保证 Redis 不会无限增长

**缺点:**
- ⚠️ 数据会丢失（需配合导出使用）

---

## 🔧 实现方案

### 方案 A: 定时导出 + TTL（最优）

#### 配置文件
```yaml
# config.yaml
redis:
  host: localhost
  port: 6379
  db: 0
  queue_name: data_queue
  
  # 🔥 新增: 存储优化配置
  storage_optimization:
    enabled: true
    
    # Redis 只保留最近的数据
    max_keep: 5000  # 减少到5000条（约1小时数据）
    
    # 数据生命周期（秒）
    data_ttl: 86400  # 24小时后自动删除
    
    # 字段精简模式
    slim_mode: true  # 只存7个核心字段

# 数据管理
data_management:
  # 导出配置
  export_dir: data_exports
  
  # 🔥 新增: 自动导出触发条件
  auto_export:
    enabled: true
    
    # 触发条件1: Redis队列长度
    queue_threshold: 5000  # 超过5000条自动导出
    
    # 触发条件2: 内存使用
    memory_threshold_mb: 100  # 超过100MB自动导出
    
    # 触发条件3: 时间间隔
    time_interval_minutes: 60  # 每60分钟导出一次
  
  # 🔥 新增: 归档配置
  archive:
    enabled: true
    compress: true  # 压缩归档
    retention_days: 30  # 保留30天
    format: "parquet"  # parquet 压缩比高
```

#### 优化后的 RedisClient

```python
# utils/redis_client.py (优化版)

class RedisClient:
    def __init__(self, host='localhost', port=6379, db=0, password=None, 
                 queue_name='data_queue', storage_config=None):
        # ... 现有代码 ...
        
        # 存储优化配置
        self.storage_config = storage_config or {}
        self.slim_mode = self.storage_config.get('slim_mode', False)
        self.data_ttl = self.storage_config.get('data_ttl', 86400)
        self.max_keep = self.storage_config.get('max_keep', 10000)
    
    def push_data(self, data: Dict[str, Any]) -> bool:
        """推送数据（优化版）"""
        try:
            # 🔥 字段精简模式
            if self.slim_mode:
                data = self._slim_data(data)
            
            json_data = json.dumps(data, ensure_ascii=False)
            
            # 🔥 推送到队列
            self.client.lpush(self.queue_name, json_data)
            
            # 🔥 检查是否需要导出（防止内存占用）
            queue_length = self.client.llen(self.queue_name)
            if queue_length > self.max_keep:
                logger.warning(f"队列长度 {queue_length} 超过阈值 {self.max_keep}，建议导出")
                # 可以在这里触发导出
                
            return True
        except Exception as e:
            logger.error(f"推送数据失败: {e}")
            return False
    
    def _slim_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """精简数据字段（只保留核心字段）"""
        slim_fields = [
            'title',
            'url', 
            'published',
            'source',
            'feed_category',
            'language',
            'summary'
        ]
        
        return {k: v for k, v in data.items() if k in slim_fields}
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """获取 Redis 内存使用情况"""
        info = self.client.info('memory')
        return {
            'used_memory_mb': info['used_memory'] / 1024 / 1024,
            'used_memory_human': info['used_memory_human'],
            'peak_memory_mb': info['used_memory_peak'] / 1024 / 1024
        }
```

#### 智能导出器

```python
# utils/smart_exporter.py (新文件)

import os
import json
import gzip
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

class SmartExporter:
    """智能数据导出器"""
    
    def __init__(self, redis_client, config):
        self.redis_client = redis_client
        self.config = config
        self.export_dir = Path(config.get('export_dir', 'data_exports'))
        self.archive_dir = self.export_dir / 'archive'
        
        # 创建目录
        self.export_dir.mkdir(exist_ok=True)
        self.archive_dir.mkdir(exist_ok=True)
        
        # 导出配置
        self.auto_export = config.get('auto_export', {})
        self.archive_config = config.get('archive', {})
    
    def should_export(self) -> bool:
        """判断是否需要导出"""
        if not self.auto_export.get('enabled', True):
            return False
        
        # 检查1: 队列长度
        queue_threshold = self.auto_export.get('queue_threshold', 5000)
        queue_length = self.redis_client.get_queue_length()
        if queue_length > queue_threshold:
            logger.info(f"触发导出: 队列长度 {queue_length} > {queue_threshold}")
            return True
        
        # 检查2: 内存使用
        memory_threshold = self.auto_export.get('memory_threshold_mb', 100)
        memory_info = self.redis_client.get_memory_usage()
        if memory_info['used_memory_mb'] > memory_threshold:
            logger.info(f"触发导出: 内存使用 {memory_info['used_memory_mb']:.1f}MB > {memory_threshold}MB")
            return True
        
        return False
    
    def export(self, batch_size=1000) -> Dict[str, Any]:
        """导出数据到本地文件"""
        stats = {
            'exported': 0,
            'export_file': None,
            'format': self.archive_config.get('format', 'json')
        }
        
        try:
            # 获取队列长度
            total = self.redis_client.get_queue_length()
            if total == 0:
                logger.info("队列为空，跳过导出")
                return stats
            
            # 计算需要导出的数量
            max_keep = self.redis_client.max_keep
            to_export = max(0, total - max_keep)
            
            if to_export == 0:
                logger.info(f"队列长度 {total} 未超过 {max_keep}，跳过导出")
                return stats
            
            logger.info(f"开始导出 {to_export} 条数据（保留 {max_keep} 条在Redis）")
            
            # 分批获取数据
            all_data = []
            for i in range(0, to_export, batch_size):
                batch = self.redis_client.get_data(min(batch_size, to_export - i))
                all_data.extend(batch)
            
            # 生成文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            export_format = stats['format']
            
            if export_format == 'parquet':
                filename = f'data_{timestamp}.parquet'
                filepath = self.export_dir / filename
                self._export_parquet(all_data, filepath)
            elif export_format == 'json':
                filename = f'data_{timestamp}.json.gz'
                filepath = self.export_dir / filename
                self._export_json_gz(all_data, filepath)
            else:
                filename = f'data_{timestamp}.json'
                filepath = self.export_dir / filename
                self._export_json(all_data, filepath)
            
            stats['exported'] = len(all_data)
            stats['export_file'] = str(filepath)
            
            logger.info(f"✓ 导出完成: {stats['exported']} 条 → {filepath}")
            
            # 清理旧归档
            self._cleanup_old_archives()
            
            return stats
            
        except Exception as e:
            logger.error(f"导出失败: {e}")
            return stats
    
    def _export_json(self, data, filepath):
        """导出为 JSON"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _export_json_gz(self, data, filepath):
        """导出为压缩 JSON"""
        with gzip.open(filepath, 'wt', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
    
    def _export_parquet(self, data, filepath):
        """导出为 Parquet（高压缩比）"""
        df = pd.DataFrame(data)
        df.to_parquet(filepath, compression='gzip', index=False)
    
    def _cleanup_old_archives(self):
        """清理过期归档"""
        if not self.archive_config.get('enabled', True):
            return
        
        retention_days = self.archive_config.get('retention_days', 30)
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        deleted_count = 0
        for file in self.export_dir.glob('data_*.{json,json.gz,parquet}'):
            # 从文件名提取日期
            try:
                date_str = file.stem.split('_')[1]  # data_20241020_120000
                file_date = datetime.strptime(date_str, '%Y%m%d')
                
                if file_date < cutoff_date:
                    file.unlink()
                    deleted_count += 1
                    logger.info(f"删除过期归档: {file.name}")
            except:
                continue
        
        if deleted_count > 0:
            logger.info(f"清理完成: 删除 {deleted_count} 个过期归档")
```

---

## 📊 存储对比

### 优化前 vs 优化后

| 项目 | 优化前 | 优化后 | 节省 |
|------|--------|--------|------|
| **Redis 内存** | 1.74GB/月 | 60MB | ⬇️ **96.6%** |
| **数据保留** | 全部在Redis | 24小时热数据 | - |
| **历史数据** | ❌ 无 | ✅ 本地文件 | - |
| **压缩** | ❌ 无 | ✅ Parquet/Gzip | ⬇️ 70% |
| **自动清理** | ❌ 无 | ✅ 30天 | - |
| **查询速度** | 快 | 热数据快，历史慢 | - |

---

## 🎯 推荐配置

### 配置 1: 轻量级（推荐个人用户）

```yaml
redis:
  storage_optimization:
    enabled: true
    max_keep: 5000      # 约1小时数据
    data_ttl: 86400     # 24小时过期
    slim_mode: true     # 精简模式

data_management:
  auto_export:
    enabled: true
    queue_threshold: 5000
    memory_threshold_mb: 50
    time_interval_minutes: 60
  
  archive:
    enabled: true
    compress: true
    retention_days: 7   # 只保留7天
    format: "parquet"   # 高压缩比
```

**效果:**
- Redis: ~50MB
- 本地: ~280MB/周（压缩后）

---

### 配置 2: 标准版（推荐团队使用）

```yaml
redis:
  storage_optimization:
    enabled: true
    max_keep: 10000     # 约2小时数据
    data_ttl: 172800    # 48小时过期
    slim_mode: false    # 保留完整字段

data_management:
  auto_export:
    enabled: true
    queue_threshold: 10000
    memory_threshold_mb: 100
    time_interval_minutes: 120
  
  archive:
    enabled: true
    compress: true
    retention_days: 30   # 保留30天
    format: "parquet"
```

**效果:**
- Redis: ~100MB
- 本地: ~1.2GB/月（压缩后）

---

### 配置 3: 专业版（推荐研究机构）

```yaml
redis:
  storage_optimization:
    enabled: false      # 不限制
    max_keep: 50000     # 约半天数据
    slim_mode: false

data_management:
  auto_export:
    enabled: true
    queue_threshold: 50000
    memory_threshold_mb: 500
    time_interval_minutes: 360  # 每6小时
  
  archive:
    enabled: true
    compress: true
    retention_days: 90   # 保留3个月
    format: "parquet"
```

**效果:**
- Redis: ~500MB
- 本地: ~3.6GB/月（压缩后）

---

## 💡 使用建议

### 1. 定期监控

```python
# 检查 Redis 内存
from utils.redis_client import RedisClient

client = RedisClient()
memory_info = client.get_memory_usage()
print(f"Redis 内存使用: {memory_info['used_memory_human']}")
print(f"队列长度: {client.get_queue_length()}")
```

### 2. 手动导出

```python
from utils.smart_exporter import SmartExporter

exporter = SmartExporter(redis_client, config)
stats = exporter.export()
print(f"导出 {stats['exported']} 条数据到 {stats['export_file']}")
```

### 3. 查询历史数据

```python
import pandas as pd

# 读取 Parquet 文件
df = pd.read_parquet('data_exports/data_20241020_120000.parquet')

# 筛选
df_rss = df[df['source'] == 'rss']
df_china = df[df['feed_category'] == 'china']
```

---

## ✅ 实施步骤

1. ✅ 更新 `config.example.yaml` - 添加存储优化配置
2. ✅ 更新 `utils/redis_client.py` - 添加精简模式
3. ✅ 创建 `utils/smart_exporter.py` - 智能导出器
4. ✅ 更新 `control_center.py` - 集成自动导出
5. ⏭️ 测试运行
6. ⏭️ 监控内存使用

---

**下一步:** 实施代码修改
