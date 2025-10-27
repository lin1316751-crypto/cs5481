# 导出数据使用说明

本目录包含从 Redis 手动导出的数据，供数据分析、清洗团队使用。

---

## 📁 文件说明

### 1. JSON 文件

```
redis_export_20251020_143052.json
```

**格式**: 标准 JSON 数组

```json
[
  {
    "title": "Bitcoin hits new high",
    "content": "Bitcoin surged to...",
    "source": "reddit",
    "created_at": "2025-10-20T14:30:00",
    ...
  },
  ...
]
```

**适合**:

- ✅ 查看和编辑（可读性好）
- ✅ 前端/可视化工具
- ✅ Postman/API 测试

**使用示例**:

```python
import json

with open('redis_export_xxx.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"Total records: {len(data)}")
print(data[0])  # 查看第一条
```

---

### 2. JSONL 文件（推荐）

```
redis_export_20251020_143052.jsonl
```

**格式**: 每行一条 JSON 记录

```json
{"title": "Bitcoin hits new high", "source": "reddit", ...}
{"title": "Ethereum update", "source": "twitter", ...}
```

**适合**:

- ✅ 流式处理（逐行读取）
- ✅ pandas 快速读取
- ✅ 大数据分析

**使用示例**:

```python
import pandas as pd

# 方法 1: pandas 直接读取（推荐）
df = pd.read_json('redis_export_xxx.jsonl', lines=True)
print(df.head())

# 方法 2: 逐行读取（内存友好）
import json

with open('redis_export_xxx.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        record = json.loads(line)
        # 处理每条记录
        print(record['title'])
```

---

### 3. 元数据文件

```
export_metadata_20251020_143052.json
```

**内容**:

```json
{
  "export_time": "2025-10-20T14:30:52",
  "total_records": 5432,
  "source_distribution": {
    "reddit": 3200,
    "twitter": 1500,
    "stocktwits": 500,
    "newsapi": 200,
    "rss": 32
  },
  "files": {
    "json": "redis_export_20251020_143052.json",
    "jsonl": "redis_export_20251020_143052.jsonl"
  }
}
```

**用途**:

- 了解数据概况
- 验证数据完整性
- 记录导出时间

---

## 📊 数据字段说明

## 🎯 通用字段

所有数据源都包含以下基础字段：

| 字段名        | 类型   | 说明     | 用途                                  |
| ------------- | ------ | -------- | ------------------------------------- |
| `source`    | string | 数据来源 | reddit/newsapi/rss/stocktwits/twitter |
| `timestamp` | string | 抓取时间 | ISO 8601 格式，用于时间序列分析       |
| `text`      | string | 主要内容 | 核心文本数据                          |
| `url`       | string | 原始链接 | 数据溯源                              |

---

## 📱 Reddit 数据字段

### 帖子 (Post) 字段

| 字段名              | 类型   | 说明           | 分析用途       |
| ------------------- | ------ | -------------- | -------------- |
| **基础信息**  |        |                |                |
| `post_id`         | string | 帖子唯一ID     | 去重、追踪     |
| `title`           | string | 帖子标题       | 关键词提取     |
| `selftext`        | string | 帖子正文       | 内容分析       |
| `text`            | string | 标题+正文      | 完整文本       |
| `url`             | string | 帖子链接       | 溯源           |
| **作者信息**  |        |                |                |
| `author`          | string | 发帖用户       | 用户画像       |
| **互动数据**  |        |                |                |
| `score`           | int    | 帖子分数       | 热度评估 ⭐    |
| `upvote_ratio`    | float  | 点赞比例 (0-1) | 争议度评估 ⭐  |
| `num_comments`    | int    | 评论数量       | 讨论热度 ⭐    |
| `gilded`          | int    | 获得金币数     | 质量评估       |
| **内容分类**  |        |                |                |
| `subreddit`       | string | 所属板块       | 主题分类       |
| `link_flair_text` | string | 帖子标签       | 细分主题       |
| **内容特性**  |        |                |                |
| `is_self`         | bool   | 是否文本帖     | 内容类型       |
| `is_video`        | bool   | 是否视频帖     | 多媒体标识     |
| `over_18`         | bool   | 是否成人内容   | 过滤标识       |
| `spoiler`         | bool   | 是否剧透       | 过滤标识       |
| **管理标记**  |        |                |                |
| `distinguished`   | string | 官方标记       | mod/admin/null |
| `stickied`        | bool   | 是否置顶       | 重要性标识     |
| **时间信息**  |        |                |                |
| `created_utc`     | float  | 发布时间戳     | 时序分析       |
| `timestamp`       | string | 抓取时间       | 数据新鲜度     |

### 评论 (Comment) 字段

| 字段名             | 类型   | 说明       | 分析用途                  |
| ------------------ | ------ | ---------- | ------------------------- |
| **基础信息** |        |            |                           |
| `comment_id`     | string | 评论唯一ID | 去重、追踪                |
| `text`           | string | 评论内容   | **情感分析** ⭐⭐⭐ |
| `url`            | string | 评论链接   | 溯源                      |
| **作者信息** |        |            |                           |
| `author`         | string | 评论用户   | 用户画像                  |
| `is_submitter`   | bool   | 是否OP本人 | 身份识别                  |
| **互动数据** |        |            |                           |
| `score`          | int    | 评论分数   | **情感强度** ⭐⭐   |
| `gilded`         | int    | 获得金币数 | 质量评估                  |
| **关系链**   |        |            |                           |
| `parent_id`      | string | 父评论ID   | 讨论树构建                |
| `link_id`        | string | 所属帖子ID | 关联分析                  |
| `subreddit`      | string | 所属板块   | 主题分类                  |
| **管理标记** |        |            |                           |
| `distinguished`  | string | 官方标记   | mod/admin/null            |
| `stickied`       | bool   | 是否置顶   | 重要性标识                |
| **时间信息** |        |            |                           |
| `created_utc`    | float  | 发布时间戳 | 时序分析                  |
| `timestamp`      | string | 抓取时间   | 数据新鲜度                |

**Reddit 数据适用场景:**

- ✅ 社区情感分析 (score, upvote_ratio)
- ✅ 讨论热度追踪 (num_comments)
- ✅ 用户影响力分析 (gilded, score)
- ✅ 争议话题识别 (低upvote_ratio + 高num_comments)

---

## 🐦 Twitter 数据字段

| 字段名               | 类型   | 说明       | 分析用途                    |
| -------------------- | ------ | ---------- | --------------------------- |
| **基础信息**   |        |            |                             |
| `text`             | string | 推文内容   | **关键词提取** ⭐⭐⭐ |
| `url`              | string | 推文链接   | 溯源                        |
| `tweet_id`         | string | 推文ID     | 去重                        |
| **用户信息**   |        |            |                             |
| `user`             | string | 用户昵称   | 用户画像                    |
| `user_id`          | string | 用户ID     | 用户追踪                    |
| **互动数据**   |        |            |                             |
| `likes`            | int    | 点赞数     | **热度评估** ⭐⭐     |
| `retweets`         | int    | 转发数     | **传播力** ⭐⭐⭐     |
| `replies`          | int    | 回复数     | 讨论热度                    |
| `quotes`           | int    | 引用转发数 | 深度互动                    |
| `view_count`       | int    | 浏览量     | 曝光度                      |
| **内容元数据** |        |            |                             |
| `hashtags`         | list   | 话题标签   | **趋势追踪** ⭐⭐⭐   |
| `mentions`         | list   | @提及      | 关系网络                    |
| `language`         | string | 语言代码   | 国际化分析                  |
| **内容特性**   |        |            |                             |
| `is_retweet`       | bool   | 是否转发   | 原创性判断                  |
| **时间信息**   |        |            |                             |
| `created_at`       | string | 发布时间   | 时序分析                    |
| `timestamp`        | string | 抓取时间   | 数据新鲜度                  |

**Twitter 数据适用场景:**

- ✅ 实时热点追踪 (hashtags, retweets)
- ✅ 病毒传播分析 (retweets, view_count)
- ✅ 舆论领袖识别 (high likes/retweets)
- ✅ 突发事件检测 (retweets突增)

---

## 💬 StockTwits 数据字段

| 字段名                   | 类型   | 说明               | 分析用途                         |
| ------------------------ | ------ | ------------------ | -------------------------------- |
| **基础信息**       |        |                    |                                  |
| `text`                 | string | 消息内容           | 文本分析                         |
| `message_id`           | int    | 消息ID             | 去重                             |
| `url`                  | string | 消息链接           | 溯源                             |
| **股票关联**       |        |                    |                                  |
| `symbol`               | string | 主要股票代码       | 股票关联                         |
| `symbols`              | list   | 所有提及股票       | 多股关联                         |
| **情感数据**       |        |                    |                                  |
| `sentiment`            | string | **情感标签** | **Bullish/Bearish** ⭐⭐⭐ |
| **用户信息**       |        |                    |                                  |
| `user`                 | string | 用户名             | 用户画像                         |
| `user_id`              | int    | 用户ID             | 用户追踪                         |
| `user_followers`       | int    | **粉丝数**   | **影响力权重** ⭐⭐        |
| `user_ideas`           | int    | 历史发帖数         | 活跃度                           |
| `user_watchlist_count` | int    | 关注股票数         | 专业度                           |
| **互动数据**       |        |                    |                                  |
| `likes`                | int    | 点赞数             | 认同度                           |
| `reshares`             | int    | 转发数             | 传播力                           |
| `replies`              | int    | 回复数             | 讨论热度                         |
| **内容元数据**     |        |                    |                                  |
| `hashtags`             | list   | 话题标签           | 趋势追踪                         |
| `links`                | list   | 包含链接           | 信息来源                         |
| **时间信息**       |        |                    |                                  |
| `created_at`           | string | 发布时间           | 时序分析                         |
| `timestamp`            | string | 抓取时间           | 数据新鲜度                       |

**StockTwits 独特优势:**

- ✅ **内置情感标签** - 无需NLP，直接分析 ⭐⭐⭐
- ✅ **股票符号关联** - 自动关联多只股票
- ✅ **用户声誉数据** - 粉丝数、发帖数权重
- ✅ **金融专注** - 纯粹的金融讨论社区

**分析场景:**

- ✅ 股票情绪分析 (sentiment + user_followers 权重)
- ✅ 热门股票追踪 (symbol 频率统计)
- ✅ KOL 观点提取 (高 followers 用户)
- ✅ 情绪转变检测 (sentiment 时序变化)

---

## 📰 NewsAPI 数据字段

| 字段名             | 类型   | 说明      | 分析用途   |
| ------------------ | ------ | --------- | ---------- |
| **基础信息** |        |           |            |
| `title`          | string | 新闻标题  | 主题提取   |
| `description`    | string | 摘要描述  | 快速浏览   |
| `content`        | string | 正文内容  | 深度分析   |
| `text`           | string | 标题+描述 | 完整文本   |
| `url`            | string | 新闻链接  | 溯源       |
| **来源信息** |        |           |            |
| `source_name`    | string | 媒体名称  | 来源可信度 |
| `source_id`      | string | 媒体ID    | 来源分类   |
| `author`         | string | 作者      | 作者画像   |
| **多媒体**   |        |           |            |
| `urlToImage`     | string | 配图URL   | 多媒体分析 |
| `has_image`      | bool   | 是否有图  | 内容丰富度 |
| **时间信息** |        |           |            |
| `published_at`   | string | 发布时间  | 时序分析   |
| `timestamp`      | string | 抓取时间  | 数据新鲜度 |

**NewsAPI 优势:**

- ✅ 权威媒体 (80,000+ 新闻源)
- ✅ 标题/摘要/正文 分离（便于不同粒度分析）
- ✅ 多语言支持
- ✅ 实时更新

**分析场景:**

- ✅ 权威观点提取 (title, description)
- ✅ 新闻时间线构建 (published_at)
- ✅ 媒体立场分析 (source_name)
- ✅ 关键事件追踪 (keywords in title)

---

## 📡 RSS 数据字段

| 字段名             | 类型   | 说明                 | 分析用途                |
| ------------------ | ------ | -------------------- | ----------------------- |
| **基础信息** |        |                      |                         |
| `title`          | string | 文章标题             | 主题提取                |
| `summary`        | string | 文章摘要             | 快速浏览                |
| `content`        | string | **完整正文**   | 深度分析 ⭐             |
| `text`           | string | 标题+摘要            | 快速文本                |
| `url`            | string | 文章链接             | 溯源                    |
| `guid`           | string | **全局唯一ID** | **精准去重** ⭐⭐ |
| **作者信息** |        |                      |                         |
| `author`         | string | 作者                 | 作者画像                |
| **内容分类** |        |                      |                         |
| `tags`           | list   | 标签数组             | 主题分类                |
| `categories`     | list   | 分类数组             | 内容归类                |
| **多媒体**   |        |                      |                         |
| `media_content`  | dict   | 媒体内容             | 图片/视频               |
| `has_media`      | bool   | 是否有媒体           | 内容丰富度              |
| **时间信息** |        |                      |                         |
| `published`      | string | 发布时间             | 时序分析                |
| `timestamp`      | string | 抓取时间             | 数据新鲜度              |

**RSS 优势:**

- ✅ 完整正文内容 (content 字段)
- ✅ GUID 精准去重
- ✅ 丰富的分类标签
- ✅ 无 API 限制

**分析场景:**

- ✅ 长文本分析 (content)
- ✅ 主题分类 (tags, categories)
- ✅ 精准去重 (guid)
- ✅ 持续监控 (无限制抓取)

---

## 🛠️ 数据处理示例

### 1. 基础统计

```python
import pandas as pd

df = pd.read_json('redis_export_xxx.jsonl', lines=True)

# 数据概览
print(f"总记录数: {len(df)}")
print(f"数据源分布:\n{df['source'].value_counts()}")
print(f"时间范围: {df['created_at'].min()} ~ {df['created_at'].max()}")

# 缺失值统计
print(f"缺失值:\n{df.isnull().sum()}")
```

### 2. 数据清洗

```python
# 删除重复 URL
df_clean = df.drop_duplicates(subset=['url'], keep='first')

# 删除缺失标题或内容
df_clean = df_clean.dropna(subset=['title', 'content'])

# 过滤短内容
df_clean = df_clean[df_clean['content'].str.len() > 50]

# 时间格式转换
df_clean['created_at'] = pd.to_datetime(df_clean['created_at'])
df_clean['date'] = df_clean['created_at'].dt.date

print(f"清洗前: {len(df)} 条")
print(f"清洗后: {len(df_clean)} 条")
```

### 3. 按数据源分析

```python
# Reddit 数据
df_reddit = df[df['source'] == 'reddit']
print(f"Reddit 平均评分: {df_reddit['score'].mean():.2f}")
print(f"Reddit 平均评论数: {df_reddit['num_comments'].mean():.2f}")

# Twitter 数据
df_twitter = df[df['source'] == 'twitter']
print(f"Twitter 平均转发: {df_twitter['retweet_count'].mean():.2f}")

# StockTwits 情感分布
df_stocktwits = df[df['source'] == 'stocktwits']
print(f"情感分布:\n{df_stocktwits['sentiment'].value_counts()}")
```

### 4. 时间序列分析

```python
# 按日期统计
daily_counts = df.groupby(df['created_at'].dt.date).size()
print(daily_counts)

# 按小时统计
hourly_counts = df.groupby(df['created_at'].dt.hour).size()
print(hourly_counts)

# 热门时段
peak_hour = hourly_counts.idxmax()
print(f"最活跃时段: {peak_hour}:00")
```

### 5. 导出清洗后的数据

```python
# CSV 格式（Excel 可打开）
df_clean.to_csv('cleaned_data.csv', index=False, encoding='utf-8-sig')

# Parquet 格式（压缩，推荐）
df_clean.to_parquet('cleaned_data.parquet', compression='gzip')

# Excel 格式
df_clean.to_excel('cleaned_data.xlsx', index=False)
```

---

## 📈 可视化示例

### 1. 数据源分布

```python
import matplotlib.pyplot as plt

df['source'].value_counts().plot(kind='bar', figsize=(10, 6))
plt.title('Data Distribution by Source')
plt.xlabel('Source')
plt.ylabel('Count')
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig('source_distribution.png', dpi=300)
plt.show()
```

### 2. 时间趋势

```python
df['created_at'] = pd.to_datetime(df['created_at'])
daily = df.groupby(df['created_at'].dt.date).size()

daily.plot(figsize=(12, 6))
plt.title('Daily Data Collection Trend')
plt.xlabel('Date')
plt.ylabel('Records Count')
plt.grid(True)
plt.tight_layout()
plt.savefig('daily_trend.png', dpi=300)
plt.show()
```

### 3. 情感分析（StockTwits）

```python
df_st = df[df['source'] == 'stocktwits']

sentiment_counts = df_st['sentiment'].value_counts()
sentiment_counts.plot(kind='pie', autopct='%1.1f%%', figsize=(8, 8))
plt.title('Sentiment Distribution (StockTwits)')
plt.ylabel('')
plt.tight_layout()
plt.savefig('sentiment_pie.png', dpi=300)
plt.show()
```

---

## 🔄 数据更新流程

### 1. 定期导出（数据采集组）

```powershell
# 每天/每周运行
conda activate cs5481
.\export_data.bat
```

### 2. 数据清洗（数据清洗组）

```python
# 读取最新导出
df = pd.read_json('redis_export_latest.jsonl', lines=True)

# 清洗处理
df_clean = clean_data(df)

# 保存到 cleaned/
df_clean.to_csv('../cleaned/cleaned_data_20251020.csv', index=False)
```

### 3. 数据分析（数据分析组）

```python
# 读取清洗后数据
df = pd.read_csv('../cleaned/cleaned_data_20251020.csv')

# 分析处理
results = analyze_data(df)

# 保存结果
results.to_csv('../analysis/analysis_results_20251020.csv', index=False)
```

---

## ❓ 常见问题

### Q: 数据太大，pandas 读取失败？

```python
# 分块读取
chunks = []
for chunk in pd.read_json('large_file.jsonl', lines=True, chunksize=10000):
    # 处理每个块
    chunk_clean = process_chunk(chunk)
    chunks.append(chunk_clean)

df = pd.concat(chunks, ignore_index=True)
```

### Q: 如何过滤特定时间范围的数据？

```python
df['created_at'] = pd.to_datetime(df['created_at'])
df_filtered = df[(df['created_at'] >= '2025-10-01') & 
                  (df['created_at'] < '2025-11-01')]
```

### Q: 如何合并多个导出文件？

```python
import glob

all_files = glob.glob('redis_export_*.jsonl')
df_list = [pd.read_json(f, lines=True) for f in all_files]
df_merged = pd.concat(df_list, ignore_index=True)
df_merged = df_merged.drop_duplicates(subset=['url'])
```

---

## 📚 相关文档

- [数据字段详细说明](../../02_使用指南/数据字段说明.md)
- [组员协作指南](组员协作完整指南.md)
- [常见问题解答](常见问题解答.md)

---

**导出工具**: [`export_data.bat`](../../export_data.bat)
**源代码**: [`export_redis_data.py`](../../export_redis_data.py)
**更新时间**: 2025-10-20
