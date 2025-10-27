# Twitter X API 速率限制问题说明

## 🚨 问题现象

```
2025-10-20 17:01:09 - twitter_v2_crawler - ERROR - ❌ API 速率限制! 
2025-10-20 17:01:09 - twitter_v2_crawler - WARNING - 关键词 #Trading 未找到推文
```

连续出现速率限制错误,导致无法抓取数据。

---

## 📊 Twitter Free 套餐限制

### **官方限制 (X API Free Tier)**

| 限制类型 | 限制值 | 时间窗口 |
|---------|--------|----------|
| **Tweet Caps** | 100 Posts/月 | 月度 |
| **Rate Limit** | **450 requests / 15分钟** | 滚动窗口 |
| **Search Results** | 最多 10 条/次 | 单次请求 |
| **Historical Data** | 仅过去 **7 天** | - |

### **关键问题**

⚠️ **15分钟窗口限制**: Free 套餐每 15 分钟只能发 450 次请求,看似很多,但:
- 每次搜索 = 1 次请求
- 如果你搜索 23 个关键词 = 23 次请求
- 如果连续运行多次,很快就会触发限制

---

## 🔧 已实施的优化

### 1️⃣ **Bearer Token 验证**
- 启动时自动验证 Token 是否有效
- 如果无效,立即停止并提示用户

### 2️⃣ **智能重试机制**
- 检测 429 速率限制错误
- 读取 `x-rate-limit-reset` 头部
- 自动等待到重置时间 (如果 < 15 分钟)

### 3️⃣ **增加请求间隔**
- 每个关键词之间等待 **5 秒** (之前是 2 秒)
- 避免触发短时间内的速率限制

### 4️⃣ **月度配额管理**
- 自动计数每月使用量
- 达到 100 条/月时停止抓取

---

## 💡 推荐解决方案

### **方案 1: 降低抓取频率** ⭐⭐⭐⭐⭐

#### 修改调度配置 (推荐)

```yaml
# config.yaml
scheduler:
  enabled: true
  intervals:
    twitter: 2880  # 从 1440 (24小时) 改为 2880 (48小时)
```

**优势**:
- ✅ 48小时运行一次,完全避开 15 分钟窗口
- ✅ 每月运行 15 次,总请求 = 3关键词 × 15 = 45 次 (远低于 450/15分钟)

---

### **方案 2: 减少关键词数量**

#### 修改为只抓取最重要的关键词

```yaml
# config.yaml
twitter:
  keywords:
    # 只保留最重要的 5 个
    - $AAPL      # 苹果
    - $TSLA      # 特斯拉
    - $SPY       # S&P 500
    - #Bitcoin   # 比特币
    - #Fed       # 美联储
  
  rate_limits:
    max_posts_per_run: 5  # 每次抓 5 个关键词
```

**优势**:
- ✅ 减少请求次数
- ✅ 聚焦高价值关键词

---

### **方案 3: 禁用 Twitter 爬虫** (临时)

如果速率限制太严重,可以先禁用:

```yaml
twitter:
  enabled: false  # 临时禁用
```

**适用场景**:
- 测试阶段
- Twitter 数据非必需
- 其他数据源已足够

---

### **方案 4: 升级到 Basic 套餐** 💰

| 套餐 | 价格 | 限制 |
|------|------|------|
| Free | $0 | 100 Posts/月 |
| **Basic** | **$100/月** | **10,000 Posts/月** |
| Pro | $5,000/月 | 1,000,000 Posts/月 |

**适用场景**:
- Twitter 数据是核心数据源
- 需要大量实时推文
- 预算允许

---

## 🎯 当前配置检查

### 检查你的 Bearer Token

1. 访问: https://developer.x.com/en/portal/dashboard
2. 进入你的 App: **yhh1090798** (App ID: 31700005)
3. 检查 **Keys and tokens** 页面
4. 确认 **Bearer Token** 是否有效

### 检查权限设置

在 App Settings → User authentication settings:
- ✅ **Read** 权限 (必需)
- ✅ **App permissions** = Read

---

## 📝 建议操作步骤

### **立即执行**

1. **修改调度频率为 48 小时**
   ```yaml
   scheduler:
     intervals:
       twitter: 2880  # 48小时
   ```

2. **减少关键词到 5 个**
   ```yaml
   twitter:
     keywords:
       - $AAPL
       - $TSLA
       - $SPY
       - #Bitcoin
       - #Fed
     rate_limits:
       max_posts_per_run: 5
   ```

3. **验证 Bearer Token**
   - 运行一次爬虫,查看是否还报速率限制
   - 如果仍报 401/403,说明 Token 无效

---

## 🔍 日志监控

成功运行时应该看到:

```
2025-10-20 17:30:00 - twitter_v2_crawler - INFO - ✓ Bearer Token 验证成功
2025-10-20 17:30:00 - twitter_v2_crawler - INFO - ✓ Twitter API v2 初始化成功
2025-10-20 17:30:00 - twitter_v2_crawler - WARNING - ⚠️ Twitter Free 套餐速率限制极严格 (15分钟窗口),建议降低抓取频率
2025-10-20 17:30:01 - twitter_v2_crawler - INFO - ✓ 关键词 $AAPL 抓取完成 - 推文: 1
2025-10-20 17:30:06 - twitter_v2_crawler - INFO - ⏳ 等待 5 秒避免速率限制...
2025-10-20 17:30:11 - twitter_v2_crawler - INFO - ✓ 关键词 $TSLA 抓取完成 - 推文: 1
```

---

## ❓ FAQ

### Q1: 为什么一直报速率限制?
**A**: Twitter Free 套餐的 15 分钟窗口限制很严格。如果你连续运行多次测试,很容易超限。建议等待 15 分钟后再试。

### Q2: Bearer Token 从哪里获取?
**A**: 登录 https://developer.x.com → 进入你的 App → Keys and tokens → Bearer Token

### Q3: 如何重置速率限制?
**A**: 速率限制是滚动窗口,15 分钟后自动重置。无法手动重置。

### Q4: 可以用多个 App 吗?
**A**: 可以,但每个 Free App 都有 100 Posts/月限制,而且需要不同的项目。

---

## 📚 参考资料

- [X API Free Tier 官方文档](https://developer.x.com/en/docs/twitter-api/getting-started/about-twitter-api#v2-access-level)
- [Rate Limits 说明](https://developer.x.com/en/docs/twitter-api/rate-limits)
- [Search Recent 端点文档](https://developer.x.com/en/docs/twitter-api/tweets/search/api-reference/get-tweets-search-recent)
