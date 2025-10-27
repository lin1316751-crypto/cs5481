"""
Twitter 爬虫模块
使用 twint（维护版本）抓取财经相关推文
推荐使用: twint-fork (pip install twint-fork)
"""
import time
from datetime import datetime
from typing import List, Dict, Any
from utils.logger import setup_logger
from utils.redis_client import RedisClient

logger = setup_logger('twitter_crawler')


class TwitterCrawler:
    """Twitter 爬虫类"""
    
    def __init__(self, config: dict, redis_client: RedisClient):
        """
        初始化 Twitter 爬虫
        
        Args:
            config: Twitter 配置字典
            redis_client: Redis 客户端实例
        """
        self.config = config
        self.redis_client = redis_client
        self.enabled = config.get('enabled', False)
        self.keywords = config.get('keywords', [])
        self.max_tweets = config.get('max_tweets', 100)
        self.use_twint = config.get('use_twint', True)  # 优先使用 twint-fork
        
        if not self.enabled:
            logger.info("Twitter 爬虫已禁用")
            return
        
        # 智能加载：优先 snscrape（更快），失败则尝试 twint-fork
        self.has_snscrape = False
        self.has_twint = False
        
        # 尝试导入 snscrape（优先，因为更稳定快速）
        try:
            import snscrape.modules.twitter as sntwitter
            self.sntwitter = sntwitter
            self.has_snscrape = True
            logger.info("✓ snscrape 可用")
        except ImportError:
            logger.warning("✗ snscrape 未安装")
        
        # 尝试导入 twint-fork（备用方案）
        if self.use_twint or not self.has_snscrape:
            try:
                import twint
                self.twint = twint
                self.has_twint = True
                logger.info("✓ twint-fork 可用")
            except ImportError:
                logger.warning("✗ twint-fork 未安装")
        
        # 检查是否至少有一个可用
        if not self.has_snscrape and not self.has_twint:
            logger.error("错误: snscrape 和 twint-fork 都未安装")
            logger.error("请至少安装一个: pip install snscrape 或 pip install twint-fork")
            self.enabled = False
        else:
            logger.info(f"Twitter 爬虫初始化成功 (snscrape: {self.has_snscrape}, twint: {self.has_twint})")
    
    def crawl(self) -> Dict[str, int]:
        """
        执行抓取任务
        
        Returns:
            dict: 抓取统计信息 {'tweets': 数量, 'errors': 数量}
        """
        stats = {'tweets': 0, 'errors': 0}
        
        if not self.enabled:
            logger.warning("Twitter 爬虫未启用，跳过")
            return stats
        
        logger.info("开始抓取 Twitter 数据...")
        
        # 智能选择：优先 snscrape，失败则回退到 twint-fork
        for keyword in self.keywords:
            success = False
            
            # 尝试 1: snscrape（更快更稳定）
            if self.has_snscrape and not success:
                try:
                    count = self._crawl_keyword_with_snscrape(keyword)
                    stats['tweets'] += count
                    success = True
                    logger.info(f"✓ snscrape 成功抓取关键词 {keyword}: {count} 条")
                except Exception as e:
                    logger.warning(f"✗ snscrape 抓取失败: {e}")
            
            # 尝试 2: twint-fork（备用方案）
            if self.has_twint and not success:
                try:
                    count = self._crawl_keyword_with_twint(keyword)
                    stats['tweets'] += count
                    success = True
                    logger.info(f"✓ twint-fork 成功抓取关键词 {keyword}: {count} 条")
                except Exception as e:
                    logger.warning(f"✗ twint-fork 抓取失败: {e}")
            
            if not success:
                logger.error(f"✗ 关键词 {keyword} 抓取失败（所有方法都失败）")
                stats['errors'] += 1
        
        logger.info(f"Twitter 抓取完成 - 推文: {stats['tweets']}, 错误: {stats['errors']}")
        return stats
    
    def _crawl_keyword_with_snscrape(self, keyword: str) -> int:
        """使用 snscrape 抓取单个关键词"""
        count = 0
        query = f"{keyword} lang:en"
        scraper = self.sntwitter.TwitterSearchScraper(query)
        
        for i, tweet in enumerate(scraper.get_items()):
            if i >= self.max_tweets:
                break
            
            tweet_data = self._extract_tweet_data_snscrape(tweet, keyword)
            if tweet_data and self.redis_client.push_data(tweet_data):
                count += 1
            
            time.sleep(0.3)  # 避免过快
        
        return count
    
    def _crawl_keyword_with_twint(self, keyword: str) -> int:
        """使用 twint-fork 抓取单个关键词"""
        c = self.twint.Config()
        c.Search = keyword
        c.Lang = "en"
        c.Limit = self.max_tweets
        c.Store_object = True
        c.Hide_output = True
        
        tweets_list = []
        c.Store_object_tweets_list = tweets_list
        
        self.twint.run.Search(c)
        
        count = 0
        for tweet in tweets_list:
            tweet_data = self._extract_tweet_data_twint(tweet, keyword)
            if tweet_data and self.redis_client.push_data(tweet_data):
                count += 1
        
        time.sleep(2)
        return count
    
    def _extract_tweet_data_twint(self, tweet, keyword: str) -> Dict[str, Any]:
        """提取推文数据（twint 格式）- 尽可能多的信息"""
        try:
            data = {
                'text': tweet.tweet,
                'source': 'twitter',
                'timestamp': int(datetime.strptime(
                    f"{tweet.datestamp} {tweet.timestamp}", 
                    "%Y-%m-%d %H:%M:%S"
                ).timestamp()) if hasattr(tweet, 'datestamp') else int(datetime.now().timestamp()),
                'url': f"https://twitter.com/{tweet.username}/status/{tweet.id}",
                'keyword': keyword,
                'user': tweet.username,
                'user_id': getattr(tweet, 'user_id', ''),
                'likes': getattr(tweet, 'likes_count', 0),
                'retweets': getattr(tweet, 'retweets_count', 0),
                'replies': getattr(tweet, 'replies_count', 0),
                'hashtags': getattr(tweet, 'hashtags', []),
                'mentions': getattr(tweet, 'mentions', []),
                'language': getattr(tweet, 'lang', 'en'),
                'is_retweet': getattr(tweet, 'retweet', False)
            }
            return data
        except Exception as e:
            logger.error(f"提取推文数据失败（twint）: {e}")
            return None
    
    def _extract_tweet_data_snscrape(self, tweet, keyword: str) -> Dict[str, Any]:
        """提取推文数据（snscrape 格式）- 尽可能多的信息"""
        try:
            data = {
                'text': tweet.content if hasattr(tweet, 'content') else tweet.rawContent,
                'source': 'twitter',
                'timestamp': int(tweet.date.timestamp()),
                'url': tweet.url,
                'keyword': keyword,
                'user': tweet.user.username if hasattr(tweet, 'user') else 'unknown',
                'user_id': tweet.user.id if hasattr(tweet, 'user') else '',
                'likes': getattr(tweet, 'likeCount', 0),
                'retweets': getattr(tweet, 'retweetCount', 0),
                'replies': getattr(tweet, 'replyCount', 0),
                'quotes': getattr(tweet, 'quoteCount', 0),
                'hashtags': [tag for tag in (getattr(tweet, 'hashtags', []) or [])],
                'mentions': [m.username for m in (getattr(tweet, 'mentionedUsers', []) or [])],
                'language': getattr(tweet, 'lang', 'en'),
                'is_retweet': getattr(tweet, 'retweetedTweet', None) is not None,
                'view_count': getattr(tweet, 'viewCount', 0)
            }
            return data
        except Exception as e:
            logger.error(f"提取推文数据失败（snscrape）: {e}")
            return None


def main():
    """测试函数"""
    import yaml
    
    # 加载配置
    with open('config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 初始化 Redis 客户端
    redis_client = RedisClient(**config['redis'])
    
    # 初始化并运行爬虫
    crawler = TwitterCrawler(config['twitter'], redis_client)
    stats = crawler.crawl()
    
    print(f"抓取完成: {stats}")
    
    # 关闭连接
    redis_client.close()


if __name__ == '__main__':
    main()
