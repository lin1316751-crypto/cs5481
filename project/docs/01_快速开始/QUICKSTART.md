# 项目快速启动指南

## 第一步：安装 Redis

### Windows 安装 Redis
1. 下载 Redis for Windows: https://github.com/tporadowski/redis/releases
2. 解压并运行 `redis-server.exe`
3. 或使用 WSL2 安装 Redis

### 验证 Redis 运行
```powershell
redis-cli ping
# 应该返回: PONG
```

## 第二步：设置 Python 环境

```powershell
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
.\venv\Scripts\Activate.ps1

# 如果遇到执行策略错误，运行：
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 安装依赖
pip install -r requirements.txt
```

## 第三步：配置 Reddit API

1. 访问 https://www.reddit.com/prefs/apps
2. 点击 "create another app..." 或 "创建应用"
3. 填写信息：
   - **name**: 随便填（如 FinanceDataCrawler）
   - **App type**: 选择 "script"
   - **description**: 可选
   - **about url**: 可选
   - **redirect uri**: 填写 `http://localhost:8080`
4. 点击 "create app"
5. 记录下：
   - **client_id**: 在应用名称下方的一串字符
   - **client_secret**: 标注为 "secret" 的字符串

## 第三步之二：配置 NewsAPI（强烈推荐！）

1. 访问 https://newsapi.org/register
2. 注册免费账号（支持 Google/GitHub 登录）
3. 获取 API Key（在账户页面）
4. 免费版限制：
   - ✅ 每天 100 次请求
   - ✅ 访问 80,000+ 新闻源
   - ✅ 延迟最多 1 小时的新闻

## 第四步：创建配置文件

```powershell
# 复制配置文件模板
Copy-Item config.example.yaml config.yaml

# 用记事本或 VS Code 编辑 config.yaml
notepad config.yaml
```

填入你的 Reddit API 凭据：
```yaml
reddit:
  client_id: YOUR_CLIENT_ID_HERE      # 替换为你的 client_id
  client_secret: YOUR_CLIENT_SECRET_HERE  # 替换为你的 client_secret
  user_agent: FinanceDataCrawler/1.0

newsapi:
  enabled: true
  api_key: YOUR_API_KEY_HERE  # 替换为你的 NewsAPI Key
```

## 第五步：检查配置

```powershell
python check_config.py
```

如果所有检查都通过，会显示 ✓ 标记。

## 第六步：运行爬虫

### 方式1：单次运行
```powershell
python main.py
```

### 方式2：定时调度（推荐）
```powershell
python scheduler.py
```
按 `Ctrl+C` 停止调度器

### 方式3：单独运行某个爬虫
```powershell
# Reddit 爬虫
python crawlers/reddit_crawler.py

# RSS 爬虫
python crawlers/rss_crawler.py
```

## 第七步：查看数据

```powershell
# 运行数据查看工具
python view_redis_data.py
```

或使用 Redis CLI：
```powershell
redis-cli
> LLEN data_queue          # 查看队列长度
> LRANGE data_queue 0 9    # 查看前10条数据
```

## 常见问题

### 1. Redis 连接失败
- 确保 Redis 服务正在运行
- 检查 `config.yaml` 中的 Redis 配置

### 2. Reddit API 错误
- 检查 client_id 和 client_secret 是否正确
- 确保没有多余的空格

### 3. NewsAPI 错误
- 检查 API Key 是否正确
- 确认没有超过每天 100 次请求限制
- 访问 https://newsapi.org/account 查看使用情况

### 4. praw 导入错误
```powershell
pip install praw prawcore newsapi-python
```

### 5. Twitter 相关
```powershell
# 推荐安装 twint-fork
pip install twint-fork

# 备选方案
pip install snscrape
```

### 6. 其他依赖问题
```powershell
pip install -r requirements.txt --upgrade
```

## 下一步

- 修改 `config.yaml` 中的抓取参数（子版块、RSS源、抓取间隔等）
- 查看 `logs/` 目录下的日志文件
- 使用 `view_redis_data.py` 导出数据进行分析

## 项目结构说明

```
project/
├── crawlers/              # 爬虫模块
│   ├── reddit_crawler.py  # Reddit 爬虫 ✅
│   ├── newsapi_crawler.py # NewsAPI 爬虫 ✅ (推荐)
│   ├── rss_crawler.py     # RSS 爬虫 ✅
│   └── twitter_crawler.py # Twitter 爬虫 ✅ (可选)
├── utils/                 # 工具模块
│   ├── redis_client.py    # Redis 客户端 ✅
│   └── logger.py          # 日志工具 ✅
├── logs/                  # 日志目录
├── config.yaml            # 配置文件（需自己创建）
├── main.py               # 主程序 ✅
├── scheduler.py          # 调度程序 ✅
├── check_config.py       # 配置检查工具 ✅
└── view_redis_data.py    # 数据查看工具 ✅
```
