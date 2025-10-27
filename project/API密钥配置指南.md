# 🚀 API 密钥配置指南

**配置难度**: ⭐⭐ 中等 (约 30 分钟)
**完成后数据量**: 从 15% → 100%

---

## 📋 配置清单

- [ ] Reddit API (10 分钟) - **优先级最高** ⭐⭐⭐⭐⭐
- [ ] StockTwits API (10 分钟) - **推荐配置** ⭐⭐
- [ ] NewsAPI (5 分钟) - **可选** ⭐
- [ ] 禁用 Twitter (1 分钟) - **建议禁用**

---

## 1️⃣ Reddit API (最重要!)

### 为什么优先配置?

- ✅ **数据量**: 75% (最大的数据源)
- ✅ **质量**: 高质量讨论内容
- ✅ **免费**: 无限制使用
- ✅ **简单**: 5 分钟配置

### 配置步骤

#### Step 1: 访问 Reddit 开发者页面

```
https://www.reddit.com/prefs/apps
```

#### Step 2: 创建应用

1. 点击页面底部 **"Create App"** 或 **"Create Another App"**
2. 填写表单:
   ```
   Name: Financial Data Crawler
   App type: 选择 "script" (第三个选项)
   Description: Collecting financial discussion data for research
   About url: (留空)
   Redirect uri: http://localhost:8080
   ```
3. 点击 **"Create app"**

#### Step 3: 复制凭证

创建成功后,你会看到:

```
Financial Data Crawler
personal use script
[一串乱码]  ← 这是你的 client_id

secret: [另一串乱码]  ← 这是你的 client_secret
```

**示例**:

```
client_id: "abc123XYZ456"
client_secret: "xyz789ABC012def345"
```

#### Step 4: 填写到 config.yaml

打开 `config.yaml`,找到第 76-79 行:

```yaml
reddit:
  enabled: true
  client_id: "粘贴你的 client_id"
  client_secret: "粘贴你的 client_secret"
  user_agent: "financial_crawler/1.0"
```

**完整示例**:

```yaml
reddit:
  enabled: true
  client_id: "abc123XYZ456"
  client_secret: "xyz789ABC012def345"
  user_agent: "financial_crawler/1.0"
```

#### Step 5: 测试

```bash
.\run.bat
选择: 2. Run crawler once
```

**期望日志**:

```
✓ Reddit API 初始化成功
✓ 正在抓取子版块: r/investing
✓ 子版块 r/investing 抓取完成
Reddit 抓取完成 - 帖子: 250, 评论: 750
```

---

## 2️⃣ StockTwits API (情绪数据)

### 为什么配置?

- ✅ **独特**: 包含 Bullish/Bearish 情绪标签
- ✅ **实时**: 市场情绪变化快
- ⚠️ **限制**: 200 请求/小时

### 配置步骤

#### Step 1: 访问 StockTwits 开发者页面

```
https://stocktwits.com/developers/apps/new
```

**注意**: 如果没有 StockTwits 账号,先注册:

```
https://stocktwits.com/signup
```

#### Step 2: 创建应用

填写表单:

```
App Name: Financial Data Crawler
Description: Collecting market sentiment data for research
Website URL: http://localhost
Callback URL: http://localhost/callback
```

#### Step 3: 获取 Access Token

创建成功后,页面会显示:

```
Client ID: [一串字符]
Client Secret: [一串字符]
Access Token: [30-40个字符的长字符串]  ← 复制这个!
```

**Access Token 示例**:

```
abc123xyz456def789ghi012jkl345mno678
```

#### Step 4: 填写到 config.yaml

打开 `config.yaml`,找到第 337 行:

```yaml
stocktwits:
  enabled: true
  access_token: "粘贴你的 Access Token"
  watch_symbols:
    - SPY
    - QQQ
    # ... (已配置好)
```

**完整示例**:

```yaml
stocktwits:
  enabled: true
  access_token: "abc123xyz456def789ghi012jkl345mno678"
  watch_symbols:
    - SPY
    - QQQ
    - DIA
    - IWM
    - XLF
    - XLE
    - XLK
    - BTC.X
    - ETH.X
  messages_per_symbol: 30
```

#### Step 5: 测试

```bash
.\run.bat
选择: 2. Run crawler once
```

**期望日志**:

```
✓ StockTwits 爬虫初始化成功,监控股票: SPY, QQQ, ...
✓ 正在抓取股票: $SPY
✓ 股票 $SPY 抓取完成,消息数: 30
StockTwits 抓取完成 - 消息: 270, 错误: 0
```

---

## 3️⃣ NewsAPI (可选)

### 配置步骤

#### Step 1: 注册账号

```
https://newsapi.org/register
```

填写:

```
Email: 你的邮箱
Password: 设置密码
```

#### Step 2: 复制 API Key

注册成功后,页面会显示:

```
Your API Key: [32个字符]
```

#### Step 3: 填写到 config.yaml

打开 `config.yaml`,找到第 295 行:

```yaml
newsapi:
  enabled: true
  api_key: "粘贴你的 API Key"
```

---

## 4️⃣ 禁用 Twitter (建议)

### 为什么禁用?

- ❌ **已失效**: Twitter 封禁了所有第三方爬虫
- ❌ **浪费时间**: 每次运行都会尝试并失败
- ✅ **加快速度**: 节省 1-2 分钟运行时间

### 禁用步骤

打开 `config.yaml`,找到第 381 行:

```yaml
twitter:
  enabled: false  # 改为 false
```

---

## ✅ 配置完成检查

### 检查配置文件

```bash
# 查看 config.yaml 中的关键配置
cat config.yaml | Select-String "client_id|access_token|api_key" | Select-String -NotMatch "YOUR_"
```

**期望输出** (没有包含 "YOUR_" 的行):

```yaml
client_id: "abc123..."
client_secret: "xyz789..."
access_token: "def456..."
api_key: "ghi789..."
```

### 运行完整测试

```bash
.\run.bat
选择: 2. Run crawler once
```

**期望结果**:

```
Reddit:      帖子 250, 评论 750, 错误 0
NewsAPI:     文章 100, 错误 0
RSS:         文章 815, 错误 0
StockTwits:  消息 270, 错误 0
Twitter:     (已禁用)
------------------------------------------------------------
总计:        数据 2185, 错误 0
队列长度:    2185
```

---

## 🚨 常见问题

### Q1: Reddit 提示 "invalid credentials"

**A**: 检查 `client_id` 和 `client_secret` 是否正确复制,不要包含多余空格

### Q2: StockTwits 仍然 403 Forbidden

**A**:

1. 检查 `access_token` 是否正确
2. 确认应用状态为 "Active"
3. 尝试重新生成 Token

### Q3: NewsAPI 提示 "apiKeyInvalid"

**A**:

1. 确认邮箱已验证
2. 检查 API Key 是否完整复制
3. 免费版有每日 100 次请求限制

### Q4: 配置后仍然没数据

**A**:

1. 检查 `enabled: true` (不是 false)
2. 确认没有多余的空格或引号
3. 重启 Redis: `.\start_redis.bat`
4. 重新运行爬虫

---

## 📊 配置效果对比

| 配置状态               | 数据量/次 | 数据源            | 配置时间 |
| ---------------------- | --------- | ----------------- | -------- |
| **无配置**       | ~815      | 仅 RSS            | 0 分钟   |
| **+ Reddit**     | ~1815     | RSS + Reddit      | 10 分钟  |
| **+ StockTwits** | ~2085     | RSS + Reddit + ST | 20 分钟  |
| **完整配置**     | ~2185     | 全部 (除 Twitter) | 30 分钟  |

---

## 🎯 推荐配置方案

### 方案 A: 快速测试 (0 分钟)

```yaml
只启用: RSS
数据量: 815 条/次
适合: 快速验证系统
```

### 方案 B: 标准配置 (10 分钟) ⭐ 推荐

```yaml
启用: RSS + Reddit
数据量: 1815 条/次
适合: 大部分使用场景
```

### 方案 C: 完整配置 (30 分钟)

```yaml
启用: RSS + Reddit + StockTwits + NewsAPI
数据量: 2185 条/次
适合: 专业数据采集
```

---

**配置完成后,别忘了**:

1. ✅ 运行测试确认
2. ✅ 导出数据检查格式
3. ✅ 设置循环模式 (可选)
4. ✅ 查看 `数据源状态报告.md` 了解更多

**祝配置顺利!** 🎉
