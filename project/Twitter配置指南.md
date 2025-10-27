# 🔑 Twitter X API 配置指南

**App ID**: 31700005  
**App Name**: yhh1090798  
**限制**: 100 Posts/月, 500 Writes/月

---

## 📋 配置步骤

### 1. 获取 Bearer Token

访问 Twitter 开发者控制台:
```
https://developer.twitter.com/en/portal/dashboard
```

找到你的应用 **yhh1090798** (App ID: 31700005)

在 **Keys and tokens** 标签页中:
1. 找到 **Bearer Token**
2. 点击 "Regenerate" (如果需要)
3. 复制 Bearer Token (长字符串,约 100+ 字符)

### 2. 配置到 config.yaml

打开 `config.yaml`,找到 `twitter` 配置段 (约第 285 行):

```yaml
twitter:
  enabled: true
  
  # ===== X API v2 凭证 (必需) =====
  api_version: "v2"
  
  # 你的凭证
  bearer_token: "粘贴你的 Bearer Token"  # ← 在这里填写
  
  # 或使用 OAuth 2.0 (可选)
  api_key: "YOUR_API_KEY"  
  api_secret: "YOUR_API_SECRET"
  access_token: "YOUR_ACCESS_TOKEN"
  access_token_secret: "YOUR_ACCESS_TOKEN_SECRET"
```

**示例**:
```yaml
bearer_token: "AAAAAAAAAAAAAAAAAAAAABc4xwEAAAAAX8FTZ..."
```

### 3. 检查限制配置

确认配置中的限制设置正确:

```yaml
  # ===== 免费套餐限制配置 =====
  rate_limits:
    max_posts_per_run: 3        # 每次运行最多 3 条推文
    max_posts_per_month: 100    # 月度限制
    max_writes_per_month: 500   # 写操作限制
    
    # 自动计数器 (系统自动管理,无需修改)
    current_month_posts: 0
    current_month_writes: 0
    last_reset_date: null
```

### 4. 配置抓取关键词

默认配置 (已优化):
```yaml
  keywords:
    - "$SPY"           # S&P 500
    - "$QQQ"           # Nasdaq
    - "Federal Reserve"  # 美联储
  
  tweets_per_keyword: 1  # 每个关键词 1 条
```

**计算**: 3 个关键词 × 1 条/关键词 = **3 条/次**

### 5. 测试配置

```bash
# 激活环境
conda activate cs5481

# 运行一次爬虫
.\run.bat
选择: 2. Run crawler once
```

**期望日志**:
```
✓ Twitter API v2 初始化成功
限制: 3 条/次, 100 条/月
✓ 月度配额检查通过: 剩余 100/100
正在搜索: $SPY
关键词 $SPY 抓取完成: 1 条
Twitter 抓取完成 - 推文: 3, 错误: 0
本次使用: 3 条, 本月累计: 3 条
```

---

## ⚠️ 配额管理

### 月度限制
- **100 Posts/月**
- 每次 3 条 → 最多运行 **33 次/月**
- 建议: 每天 1 次 (30 天 = 90 条,留 10 条余量)

### 调度配置
在 `config.yaml` 的 `scheduler` 部分:

```yaml
scheduler:
  twitter_interval: 1440  # 24小时 = 1天1次
```

### 自动计数
系统会自动:
1. ✅ 记录每次使用的 Posts 数量
2. ✅ 累加到月度总计
3. ✅ 每月 1 号自动重置
4. ✅ 超过限制时自动跳过

---

## 🔍 故障排除

### Q1: 提示 "❌ 缺少 Twitter API 凭证"
**A**: 检查 `bearer_token` 是否正确填写,不要有多余空格或引号错误

### Q2: 提示 "❌ API 访问被拒绝 (403)"
**A**: 
1. 确认 Bearer Token 是否正确
2. 检查应用是否激活 (Active 状态)
3. 尝试重新生成 Token

### Q3: 提示 "❌ API 速率限制! (429)"
**A**: 
1. Twitter 检测到请求过频繁
2. 等待 15 分钟后重试
3. 增加 `twitter_interval` 到更大值

### Q4: 本月配额已用完
**A**: 
1. 查看 `config.yaml` 中的 `current_month_posts`
2. 等到下个月 1 号自动重置
3. 或手动改小 `max_posts_per_run` (如改为 2)

---

## 📊 配额监控

### 查看当前使用量

查看 `config.yaml` 中的计数器:
```yaml
rate_limits:
  current_month_posts: 15  # ← 当前累计
  last_reset_date: "2025-10-20"  # ← 上次重置日期
```

### 计算剩余配额
```
剩余 = 100 - current_month_posts
可运行次数 = 剩余 ÷ 3
```

**示例**: 
- 已用 15 条
- 剩余 85 条
- 可运行 28 次 (85 ÷ 3 = 28)

---

## 🎯 优化建议

### 方案 A: 保守模式 (推荐)
```yaml
twitter_interval: 1440  # 每天 1 次
max_posts_per_run: 3    # 每次 3 条
```
**月度用量**: 30 天 × 3 条 = 90 条 (留 10 条余量)

### 方案 B: 节约模式
```yaml
twitter_interval: 2880  # 每两天 1 次
max_posts_per_run: 3
```
**月度用量**: 15 次 × 3 条 = 45 条 (节省一半配额)

### 方案 C: 精简模式
```yaml
tweets_per_keyword: 1
keywords:
  - "$SPY"  # 只抓 S&P 500
```
**每次用量**: 1 条 → 可运行 100 次

---

## 📝 配置完成检查清单

- [ ] Bearer Token 已填写到 `config.yaml`
- [ ] `enabled: true` 已设置
- [ ] 限制配置检查通过 (3 条/次, 100 条/月)
- [ ] 测试运行成功 (有推文数据)
- [ ] 调度间隔设置合理 (1440 分钟 = 24 小时)
- [ ] 了解配额监控方法

---

**配置完成后,你的 Twitter 爬虫将会**:
- ✅ 每天自动抓取 3 条最新推文
- ✅ 自动管理月度配额
- ✅ 超限时自动跳过
- ✅ 每月 1 号自动重置

**Happy Crawling!** 🎉
