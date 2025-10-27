# 📊 API 限制管理总结

**更新日期**: 2025-10-20  
**状态**: 已配置限制管理系统

---

## 🎯 配置概览

| API | 限制类型 | 限制值 | 每次使用 | 最大频率 | 自动管理 |
|-----|---------|--------|---------|---------|---------|
| **Twitter X API** | 100 Posts/月 | 100 | 3 条 | 33 次/月 | ✅ 是 |
| **NewsAPI** | 100 次/天 | 100 | 3 次 | 33 次/天 | ✅ 是 |
| **StockTwits** | 200 次/小时 | 200 | ~9 次 | 22 次/小时 | ❌ 否 |
| **Reddit** | 无限制 | ∞ | 不限 | 不限 | N/A |
| **RSS** | 无限制 | ∞ | 不限 | 不限 | N/A |

---

## 🔧 Twitter X API 配置

### 限制详情
- **每月限制**: 100 Posts
- **每次抓取**: 3 条推文
- **关键词**: 3 个 ($SPY, $QQQ, Federal Reserve)
- **每关键词**: 1 条推文
- **计算**: 3 关键词 × 1 条 = 3 条/次

### 配置位置
`config.yaml` 第 285-330 行

```yaml
twitter:
  enabled: true
  bearer_token: "YOUR_BEARER_TOKEN"  # ← 必需
  
  rate_limits:
    max_posts_per_run: 3        # 每次 3 条
    max_posts_per_month: 100    # 月限制
    current_month_posts: 0      # 自动计数
    last_reset_date: null       # 自动重置
  
  keywords:
    - "$SPY"
    - "$QQQ"
    - "Federal Reserve"
  
  tweets_per_keyword: 1
```

### 调度配置
`config.yaml` 第 378 行

```yaml
scheduler:
  twitter_interval: 1440  # 24小时 (每天1次)
```

### 月度规划
- **保守方案**: 每天 1 次 × 30 天 = 90 条 (留 10 条余量)
- **可运行次数**: 100 ÷ 3 = 33 次/月
- **自动重置**: 每月 1 号

---

## 📰 NewsAPI 配置

### 限制详情
- **每日限制**: 100 次请求
- **每次抓取**: 3 个关键词
- **关键词**: finance, stocks, market
- **每关键词**: 20 篇文章
- **计算**: 3 关键词 = 3 次请求 = 60 篇/次

### 配置位置
`config.yaml` 第 258-282 行

```yaml
newsapi:
  api_key: "7d65184d1c104775995f49a4f0c3eb74"  # ← 已填写
  enabled: true
  
  rate_limits:
    max_requests_per_day: 100   # 每日限制
    requests_per_run: 3         # 每次 3 个关键词
    current_day_requests: 0     # 自动计数
    last_reset_date: null       # 自动重置
  
  query_keywords:
    - "finance"
    - "stocks"
    - "market"
  
  articles_per_keyword: 20
```

### 调度配置
`config.yaml` 第 379 行

```yaml
scheduler:
  newsapi_interval: 720  # 12小时 (每天2次)
```

### 每日规划
- **保守方案**: 每天 2 次 × 3 次 = 6 次 (留余量)
- **可运行次数**: 100 ÷ 3 = 33 次/天
- **自动重置**: 每天 0 点

---

## 📈 StockTwits API (需配置 Token)

### 限制详情
- **速率限制**: 200 次/小时
- **监控股票**: 9 个 (SPY, QQQ, DIA, IWM, XLF, XLE, XLK, BTC.X, ETH.X)
- **每股票**: 30 条消息
- **计算**: 9 股票 = 9 次请求

### 配置位置
`config.yaml` 第 337-358 行

```yaml
stocktwits:
  enabled: true
  access_token: null  # ← 需要配置 (见 API密钥配置指南.md)
  
  watch_symbols:
    - SPY
    - QQQ
    - DIA
    # ... 共 9 个
  
  messages_per_symbol: 30
```

### 调度配置
`config.yaml` 第 380 行

```yaml
scheduler:
  stocktwits_interval: 60  # 60分钟 (每小时1次)
```

### 每小时规划
- **每次请求**: 9 次
- **可运行次数**: 200 ÷ 9 = 22 次/小时
- **实际设置**: 1 次/小时 (保守)

---

## 🔄 自动管理机制

### 1. Twitter (月度重置)

**计数器**:
```yaml
current_month_posts: 15  # 本月已用
last_reset_date: "2025-10-20"
```

**逻辑**:
1. 每次抓取前检查配额
2. 自动累加使用量
3. 每月 1 号重置为 0
4. 超限时跳过抓取

**代码**: `crawlers/twitter_v2_crawler.py`

### 2. NewsAPI (每日重置)

**计数器**:
```yaml
current_day_requests: 6  # 今日已用
last_reset_date: "2025-10-20"
```

**逻辑**:
1. 每次抓取前检查配额
2. 自动累加使用量
3. 每天 0 点重置为 0
4. 超限时跳过抓取

**代码**: `crawlers/newsapi_crawler.py`

### 3. 配额保存

**自动保存到 config.yaml**:
- 每次运行后更新计数器
- 写入 `current_month_posts` / `current_day_requests`
- 更新 `last_reset_date`

---

## 📅 运行频率规划

### 循环模式 (推荐)

启用循环模式:
```bash
.\run.bat
选择: 3. Run crawler in loop mode
```

**实际运行频率**:
- Reddit: 每 60 分钟
- RSS: 每 30 分钟
- NewsAPI: 每 12 小时 (2 次/天)
- Twitter: 每 24 小时 (1 次/天)
- StockTwits: 每 60 分钟

### 单次模式

```bash
.\run.bat
选择: 2. Run crawler once
```

**每次使用**:
- Twitter: 3 条
- NewsAPI: 3 次请求
- StockTwits: 9 次请求
- Reddit: 不限
- RSS: 不限

---

## 📊 配额监控

### 查看当前使用量

**方法 1**: 查看 config.yaml

```yaml
twitter:
  rate_limits:
    current_month_posts: 15  # ← 看这里

newsapi:
  rate_limits:
    current_day_requests: 6  # ← 看这里
```

**方法 2**: 查看运行日志

```
Twitter 抓取完成 - 推文: 3, 错误: 0
本次使用: 3 条, 本月累计: 15 条
✓ 月度配额检查通过: 剩余 85/100

NewsAPI 抓取完成 - 文章: 60, 错误: 0
本次使用: 3 次, 今日累计: 6 次
✓ 今日配额检查通过: 剩余 94/100
```

### 计算剩余配额

**Twitter**:
```
剩余 Posts = 100 - current_month_posts
可运行次数 = 剩余 ÷ 3
```

**NewsAPI**:
```
剩余请求 = 100 - current_day_requests
可运行次数 = 剩余 ÷ 3
```

---

## ⚠️ 注意事项

### 1. Twitter 配额珍贵
- ✅ 每天只运行 1 次
- ✅ 使用最重要的关键词
- ✅ 避免手动多次测试
- ❌ 不要设置过短的 interval

### 2. NewsAPI 免费版限制
- ✅ 每天最多 2-3 次运行
- ✅ 选择最重要的关键词
- ✅ 12 小时间隔合理
- ❌ 不要频繁测试

### 3. StockTwits 需要 Token
- ⚠️ 目前未配置 `access_token`
- ⚠️ 需要注册开发者账号
- ⚠️ 见 `API密钥配置指南.md`

### 4. 配额超限处理
- 系统自动跳过抓取
- 不会报错或中断
- 日志显示 "配额已用完"
- 等待自动重置

---

## 🎯 最佳实践

### 推荐配置

**正式运行** (循环模式):
```yaml
scheduler:
  reddit_interval: 60       # 每小时
  rss_interval: 30          # 每30分钟
  newsapi_interval: 720     # 每12小时 (2次/天)
  twitter_interval: 1440    # 每24小时 (1次/天)
  stocktwits_interval: 60   # 每小时
```

**测试模式** (谨慎使用):
```yaml
scheduler:
  newsapi_interval: 1440    # 每24小时 (1次/天)
  twitter_interval: 2880    # 每48小时 (15次/月)
```

### 节约配额技巧

1. **减少关键词数量**:
   ```yaml
   twitter:
     keywords:
       - "$SPY"  # 只抓最重要的
   ```

2. **增加运行间隔**:
   ```yaml
   twitter_interval: 2880  # 两天一次
   ```

3. **降低每次数量**:
   ```yaml
   tweets_per_keyword: 1  # 已是最小值
   max_posts_per_run: 2   # 从 3 改为 2
   ```

---

## 📝 配置完成检查清单

- [ ] Twitter Bearer Token 已配置
- [ ] NewsAPI Key 已配置
- [ ] 运行间隔已优化 (twitter: 1440, newsapi: 720)
- [ ] 测试运行成功
- [ ] 配额自动管理正常工作
- [ ] 了解如何监控配额使用

---

## 📚 相关文档

- **Twitter 配置**: Twitter配置指南.md
- **所有 API 配置**: API密钥配置指南.md
- **数据源状态**: 数据源状态报告.md
- **常见问题**: 常见问题.md

---

**配置完成后,系统将**:
- ✅ 自动管理 API 配额
- ✅ 避免超限
- ✅ 每日/每月自动重置
- ✅ 日志显示详细使用情况

**Happy Crawling with Smart Quota Management!** 🎉
