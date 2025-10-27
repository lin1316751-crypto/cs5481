"""
Twitter/X API v2 爬虫模块
支持 X API Free Tier 的限制管理
"""
import time
import requests
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from utils.logger import setup_logger
from utils.redis_client import RedisClient
import yaml

logger = setup_logger('twitter_v2_crawler')


class TwitterV2Crawler:
    """Twitter API v2 爬虫类 (支持免费套餐限制管理)"""
    
    def __init__(self, config: dict, redis_client: RedisClient):
        """
        初始化 Twitter V2 爬虫
        
        Args:
            config: Twitter 配置字典
            redis_client: Redis 客户端实例
        """
        self.config = config
        self.redis_client = redis_client
        self.enabled = config.get('enabled', False)
        
        if not self.enabled:
            logger.info("Twitter 爬虫已禁用")
            return
        
        # 读取凭证
        self.bearer_token = config.get('bearer_token')
        self.api_key = config.get('api_key')
        self.api_secret = config.get('api_secret')
        
        # 读取限制配置
        self.rate_limits = config.get('rate_limits', {})
        self.max_posts_per_run = self.rate_limits.get('max_posts_per_run', 3)
        self.max_posts_per_month = self.rate_limits.get('max_posts_per_month', 100)
        
        # 读取抓取配置
        self.keywords = config.get('keywords', [])
        self.tweets_per_keyword = config.get('tweets_per_keyword', 1)
        
        # API 端点
        self.search_url = "https://api.twitter.com/2/tweets/search/recent"
        
        # 验证配置
        if not self.bearer_token and not (self.api_key and self.api_secret):
            logger.error("❌ 缺少 Twitter API 凭证!")
            logger.info("请在 config.yaml 中配置 bearer_token 或 api_key/api_secret")
            self.enabled = False
            return
        
        # 测试 Bearer Token 是否有效
        if self.bearer_token and not self._test_bearer_token():
            logger.error("❌ Bearer Token 无效或已过期!")
            logger.error("请访问 https://developer.x.com/en/portal/dashboard 检查你的 App")
            self.enabled = False
            return
        
        logger.info("✓ Twitter API v2 初始化成功")
        logger.info(f"限制: {self.max_posts_per_run} 条/次, {self.max_posts_per_month} 条/月")
        logger.warning("⚠️ Twitter Free 套餐速率限制极严格 (15分钟窗口),建议降低抓取频率")
    
    def crawl(self) -> Dict[str, int]:
        """
        执行抓取任务
        
        Returns:
            dict: 抓取统计信息 {'tweets': 数量, 'errors': 数量}
        """
        stats = {'tweets': 0, 'errors': 0}
        
        if not self.enabled:
            logger.warning("Twitter 爬虫未启用,跳过")
            return stats
        
        # 检查月度限制
        if not self._check_monthly_quota():
            logger.warning("⚠️ 本月配额已用完,跳过抓取")
            return stats
        
        logger.info("开始抓取 Twitter 数据...")
        logger.info(f"关键词: {', '.join(self.keywords)}")
        
        total_tweets_this_run = 0
        
        for keyword in self.keywords:
            # 检查是否超过单次限制
            if total_tweets_this_run >= self.max_posts_per_run:
                logger.warning(f"⚠️ 已达到单次限制 ({self.max_posts_per_run} 条),停止抓取")
                break
            
            try:
                logger.info(f"正在搜索: {keyword}")
                
                # 计算本次可抓取数量
                remaining_quota = self.max_posts_per_run - total_tweets_this_run
                max_results = min(self.tweets_per_keyword, remaining_quota, 10)  # API 单次最多 10
                
                # 搜索推文
                tweets = self._search_tweets(keyword, max_results=max_results)
                
                if not tweets:
                    logger.warning(f"关键词 {keyword} 未找到推文")
                    continue
                
                # 保存推文
                keyword_count = 0
                for tweet in tweets:
                    tweet_data = self._extract_tweet_data(tweet, keyword)
                    if tweet_data and self.redis_client.push_data(tweet_data):
                        stats['tweets'] += 1
                        total_tweets_this_run += 1
                        keyword_count += 1
                
                logger.info(f"✓ 关键词 {keyword} 抓取完成 - 推文: {keyword_count}")
                
                # 避免请求过快 - Twitter Free 限制很严格,需要更长延迟
                logger.info("⏳ 等待 5 秒避免速率限制...")
                time.sleep(5)  # 从 2 秒增加到 5 秒
                
            except Exception as e:
                logger.error(f"抓取关键词 {keyword} 时出错: {e}")
                stats['errors'] += 1
        
        # 更新配额计数
        self._update_quota(total_tweets_this_run)
        
        logger.info(f"Twitter 抓取完成 - 推文: {stats['tweets']}, 错误: {stats['errors']}")
        logger.info(f"本次使用: {total_tweets_this_run} 条, 本月累计: {self._get_current_month_usage()} 条")
        
        return stats
    
    def _test_bearer_token(self) -> bool:
        """
        测试 Bearer Token 是否有效
        
        Returns:
            bool: Token 是否有效
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.bearer_token}",
                "User-Agent": "v2TweetSearchPython"
            }
            
            # 使用一个简单的查询测试
            params = {
                "query": "test",
                "max_results": 10
            }
            
            response = requests.get(self.search_url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                logger.info("✓ Bearer Token 验证成功")
                return True
            elif response.status_code == 401:
                logger.error("❌ Bearer Token 无效 (401 Unauthorized)")
                return False
            elif response.status_code == 403:
                logger.error("❌ Bearer Token 权限不足 (403 Forbidden)")
                logger.error("   请确保你的 App 有 'Read' 权限")
                return False
            elif response.status_code == 429:
                logger.warning("⚠️ 速率限制,但 Token 可能有效")
                return True  # Token 本身可能是有效的,只是被限速了
            else:
                logger.warning(f"⚠️ 未知响应码: {response.status_code}")
                return True  # 保守起见,认为可能有效
                
        except Exception as e:
            logger.error(f"测试 Bearer Token 失败: {e}")
            return False
    
    def _search_tweets(self, query: str, max_results: int = 10) -> List[Dict]:
        """
        使用 Twitter API v2 搜索推文
        
        Args:
            query: 搜索关键词
            max_results: 最多返回结果数 (1-10 for Free Tier)
        
        Returns:
            list: 推文列表
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.bearer_token}",
                "User-Agent": "v2TweetSearchPython"
            }
            
            # API 参数
            params = {
                "query": query,
                "max_results": max_results,
                "tweet.fields": "created_at,public_metrics,author_id,lang,entities",
                "expansions": "author_id",
                "user.fields": "username,name,verified,public_metrics"
            }
            
            response = requests.get(self.search_url, headers=headers, params=params, timeout=30)
            
            # 检查速率限制
            if response.status_code == 429:
                reset_time = response.headers.get('x-rate-limit-reset', 'unknown')
                remaining = response.headers.get('x-rate-limit-remaining', '0')
                logger.error(
                    f"❌ API 速率限制! "
                    f"剩余请求: {remaining}, "
                    f"重置时间: {reset_time}"
                )
                # 如果有重置时间,等待
                if reset_time != 'unknown':
                    try:
                        reset_timestamp = int(reset_time)
                        now = datetime.now().timestamp()
                        wait_seconds = max(0, reset_timestamp - now + 5)  # +5秒缓冲
                        if wait_seconds < 900:  # 如果等待时间小于15分钟
                            logger.warning(f"⏳ 等待 {int(wait_seconds)} 秒后重试...")
                            time.sleep(wait_seconds)
                            # 重试一次
                            response = requests.get(self.search_url, headers=headers, params=params, timeout=30)
                            if response.status_code != 200:
                                return []
                        else:
                            logger.error(f"⏳ 需要等待 {int(wait_seconds/60)} 分钟,跳过")
                            return []
                    except:
                        return []
                else:
                    return []
            
            response.raise_for_status()
            data = response.json()
            
            tweets = data.get('data', [])
            users = {user['id']: user for user in data.get('includes', {}).get('users', [])}
            
            # 合并用户信息
            for tweet in tweets:
                author_id = tweet.get('author_id')
                if author_id in users:
                    tweet['author'] = users[author_id]
            
            return tweets
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                logger.error("❌ API 访问被拒绝 (403) - 请检查 Bearer Token")
            else:
                logger.error(f"HTTP 错误: {e}")
            return []
        except Exception as e:
            logger.error(f"搜索推文失败: {e}")
            return []
    
    def _extract_tweet_data(self, tweet: dict, keyword: str) -> Dict[str, Any]:
        """
        提取推文数据
        
        Args:
            tweet: Twitter API 返回的推文对象
            keyword: 搜索关键词
        
        Returns:
            dict: 推文数据
        """
        try:
            author = tweet.get('author', {})
            metrics = tweet.get('public_metrics', {})
            
            # 时间戳转换
            created_at = tweet.get('created_at')
            if created_at:
                timestamp = int(datetime.fromisoformat(created_at.replace('Z', '+00:00')).timestamp())
            else:
                timestamp = int(time.time())
            
            data = {
                # 基础字段
                'text': tweet.get('text', ''),
                'source': 'twitter',
                'timestamp': timestamp,
                'url': f"https://twitter.com/i/web/status/{tweet.get('id')}",
                
                # Twitter 特有字段
                'tweet_id': tweet.get('id'),
                'author': author.get('username', 'unknown'),
                'author_name': author.get('name', 'Unknown'),
                'verified': author.get('verified', False),
                'keyword': keyword,
                'language': tweet.get('lang', 'en'),
                
                # 互动数据
                'retweet_count': metrics.get('retweet_count', 0),
                'reply_count': metrics.get('reply_count', 0),
                'like_count': metrics.get('like_count', 0),
                'quote_count': metrics.get('quote_count', 0),
                
                # 实体信息
                'entities': tweet.get('entities', {}),
            }
            
            return data
            
        except Exception as e:
            logger.error(f"提取推文数据失败: {e}")
            return None
    
    def _check_monthly_quota(self) -> bool:
        """
        检查月度配额是否可用
        
        Returns:
            bool: 是否可以继续抓取
        """
        current_usage = self._get_current_month_usage()
        
        # 检查是否需要重置计数器
        self._reset_counter_if_needed()
        
        if current_usage >= self.max_posts_per_month:
            logger.warning(f"⚠️ 月度配额已用完: {current_usage}/{self.max_posts_per_month}")
            return False
        
        remaining = self.max_posts_per_month - current_usage
        logger.info(f"✓ 月度配额检查通过: 剩余 {remaining}/{self.max_posts_per_month}")
        return True
    
    def _get_current_month_usage(self) -> int:
        """获取本月已使用的 Posts 数量"""
        return self.rate_limits.get('current_month_posts', 0)
    
    def _update_quota(self, posts_used: int):
        """
        更新配额计数
        
        Args:
            posts_used: 本次使用的 Posts 数量
        """
        current = self.rate_limits.get('current_month_posts', 0)
        new_total = current + posts_used
        
        # 更新配置文件中的计数器
        self._save_quota_to_config(new_total)
        
        logger.info(f"✓ 配额已更新: {current} → {new_total}")
    
    def _reset_counter_if_needed(self):
        """检查并重置月度计数器"""
        last_reset = self.rate_limits.get('last_reset_date')
        today = str(date.today())
        
        if last_reset is None or last_reset[:7] != today[:7]:  # 不同月份
            logger.info(f"✓ 月度计数器重置 (上次: {last_reset})")
            self.rate_limits['current_month_posts'] = 0
            self.rate_limits['last_reset_date'] = today
            self._save_quota_to_config(0)
    
    def _save_quota_to_config(self, new_total: int):
        """
        将配额计数保存到 config.yaml
        
        Args:
            new_total: 新的累计数量
        """
        try:
            # 读取配置文件
            with open('config.yaml', 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # 更新计数器
            if 'twitter' in config and 'rate_limits' in config['twitter']:
                config['twitter']['rate_limits']['current_month_posts'] = new_total
                config['twitter']['rate_limits']['last_reset_date'] = str(date.today())
            
            # 写回配置文件
            with open('config.yaml', 'w', encoding='utf-8') as f:
                yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
            
            # 更新内存中的配置
            self.rate_limits['current_month_posts'] = new_total
            
        except Exception as e:
            logger.error(f"保存配额到配置文件失败: {e}")
