"""
NewsAPI 爬虫模块
使用 NewsAPI.org 获取财经新闻
支持免费套餐限制管理 (100 次/天)
需要申请免费 API Key: https://newsapi.org/
"""
import time
import yaml
from datetime import datetime, timedelta, date
from typing import List, Dict, Any
from utils.logger import setup_logger
from utils.redis_client import RedisClient

logger = setup_logger('newsapi_crawler')


class NewsAPICrawler:
    """NewsAPI 爬虫类"""
    
    def __init__(self, config: dict, redis_client: RedisClient):
        """
        初始化 NewsAPI 爬虫
        
        Args:
            config: NewsAPI 配置字典
            redis_client: Redis 客户端实例
        """
        self.config = config
        self.redis_client = redis_client
        self.enabled = config.get('enabled', False)
        self.api_key = config.get('api_key', '')
        
        # 读取限制配置
        self.rate_limits = config.get('rate_limits', {})
        self.max_requests_per_day = self.rate_limits.get('max_requests_per_day', 100)
        self.requests_per_run = self.rate_limits.get('requests_per_run', 3)
        
        if not self.enabled:
            logger.info("NewsAPI 爬虫已禁用")
            return
        
        if not self.api_key or self.api_key == 'YOUR_API_KEY_HERE':
            logger.warning("NewsAPI 未配置 API Key")
            self.enabled = False
            return
        
        try:
            from newsapi import NewsApiClient
            self.newsapi = NewsApiClient(api_key=self.api_key)
            logger.info("NewsAPI 爬虫初始化成功")
        except ImportError as e:
            logger.error(f"newsapi-python 未安装: {e}")
            logger.error("请运行: pip install newsapi-python")
            self.enabled = False
        except Exception as e:
            logger.error(f"NewsAPI 初始化失败: {e}")
            self.enabled = False
    
    def crawl(self) -> Dict[str, int]:
        """
        执行抓取任务
        
        Returns:
            dict: 抓取统计信息 {'articles': 数量, 'errors': 数量}
        """
        stats = {'articles': 0, 'errors': 0}
        
        if not self.enabled:
            logger.warning("NewsAPI 爬虫未启用，跳过")
            return stats
        
        # 检查每日配额
        if not self._check_daily_quota():
            logger.warning("⚠️ 今日配额已用完,跳过抓取")
            return stats
        
        logger.info("开始抓取 NewsAPI 数据...")
        
        # 获取配置 - 只抓取配置的关键词数量
        queries = self.config.get('query_keywords', ['finance', 'stocks', 'market'])
        # 限制为 requests_per_run
        queries = queries[:self.requests_per_run]
        
        language = self.config.get('language', 'en')
        articles_per_keyword = self.config.get('articles_per_keyword', 20)
        
        # ✅ 修复：NewsAPI 免费版有 12-24 小时延迟，改为抓取最近 7 天
        now = datetime.now()
        from_7days = (now - timedelta(days=1)).strftime('%Y-%m-%d')  # 改为 7 天
        
        requests_used = 0
        
        for query in queries:
            try:
                logger.info(f"正在搜索关键词: {query}")
                
                articles = []
                
                # ✅ 修复：使用 everything 端点 + 7天时间范围
                try:
                    response = self.newsapi.get_everything(
                        q=query,
                        language=language,
                        from_param=from_7days,  # ✅ 改为 7 天
                        sort_by='publishedAt',  # 按发布时间排序
                        page_size=articles_per_keyword
                    )
                    requests_used += 1
                    
                    if response['status'] == 'ok':
                        articles = response.get('articles', [])
                        total_results = response.get('totalResults', 0)
                        logger.info(f"  ✓ 找到 {len(articles)} 篇文章（总共 {total_results} 篇可用）")
                    else:
                        logger.warning(f"  ✗ API 返回错误: {response.get('message', 'Unknown')}")
                        
                except Exception as e:
                    logger.error(f"  ✗ 抓取失败: {e}")
                    # ✅ 打印详细错误信息
                    import traceback
                    logger.error(traceback.format_exc())
                    stats['errors'] += 1
                    continue
                
                # 保存文章
                keyword_count = 0
                for article in articles:
                    article_data = self._extract_article_data(article, query)
                    if article_data and self.redis_client.push_data(article_data):
                        stats['articles'] += 1
                        keyword_count += 1
                
                logger.info(
                    f"✓ 关键词 '{query}' 抓取完成 - "
                    f"获取: {len(articles)} 篇, 保存: {keyword_count} 篇"
                )
                
                # 避免请求过快
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"搜索关键词 {query} 时出错: {e}")
                stats['errors'] += 1
        
        # 更新配额
        self._update_quota(requests_used)
        
        logger.info(f"NewsAPI 抓取完成 - 文章: {stats['articles']}, 错误: {stats['errors']}")
        logger.info(f"本次使用: {requests_used} 次, 今日累计: {self._get_current_day_usage()} 次")
        return stats
    
    def _extract_article_data(self, article: dict, query: str) -> Dict[str, Any]:
        """
        提取文章数据 - 完整信息
        
        Args:
            article: NewsAPI 文章对象
            query: 搜索关键词
        
        Returns:
            dict: 文章数据
        """
        try:
            # 组合标题和描述
            title = article.get('title', '')
            description = article.get('description', '')
            content = article.get('content', '')
            
            text = title
            if description:
                text += "\n\n" + description
            if content:
                text += "\n\n" + content
            
            # 解析时间戳
            published_at = article.get('publishedAt', '')
            try:
                from dateutil import parser as date_parser
                dt = date_parser.parse(published_at)
                timestamp = int(dt.timestamp())
            except:
                timestamp = int(datetime.now().timestamp())
            
            data = {
                # 基础字段
                'text': text,
                'source': 'newsapi',
                'timestamp': timestamp,
                'url': article.get('url', ''),
                
                # NewsAPI 特有字段
                'query': query,
                'source_name': article.get('source', {}).get('name', 'Unknown'),
                'source_id': article.get('source', {}).get('id', ''),
                'author': article.get('author', 'Unknown'),
                
                # 内容分离（用于不同分析）
                'title': title,
                'description': description,
                'content': content,
                
                # 媒体
                'url_to_image': article.get('urlToImage', ''),
                'has_image': bool(article.get('urlToImage')),
                
                # 时间信息
                'published_at': published_at
            }
            
            return data
            
        except Exception as e:
            logger.error(f"提取文章数据失败: {e}")
            return None
    
    def _check_daily_quota(self) -> bool:
        """
        检查每日配额是否可用
        
        Returns:
            bool: 是否可以继续抓取
        """
        current_usage = self._get_current_day_usage()
        
        # 检查是否需要重置计数器
        self._reset_counter_if_needed()
        
        if current_usage >= self.max_requests_per_day:
            logger.warning(f"⚠️ 今日配额已用完: {current_usage}/{self.max_requests_per_day}")
            return False
        
        remaining = self.max_requests_per_day - current_usage
        logger.info(f"✓ 今日配额检查通过: 剩余 {remaining}/{self.max_requests_per_day}")
        return True
    
    def _get_current_day_usage(self) -> int:
        """获取今日已使用的请求数量"""
        return self.rate_limits.get('current_day_requests', 0)
    
    def _update_quota(self, requests_used: int):
        """
        更新配额计数
        
        Args:
            requests_used: 本次使用的请求数量
        """
        current = self.rate_limits.get('current_day_requests', 0)
        new_total = current + requests_used
        
        # 更新配置文件中的计数器
        self._save_quota_to_config(new_total)
        
        logger.info(f"✓ 配额已更新: {current} → {new_total}")
    
    def _reset_counter_if_needed(self):
        """检查并重置每日计数器"""
        last_reset = self.rate_limits.get('last_reset_date')
        today = str(date.today())
        
        if last_reset != today:
            logger.info(f"✓ 每日计数器重置 (上次: {last_reset})")
            self.rate_limits['current_day_requests'] = 0
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
            if 'newsapi' in config and 'rate_limits' in config['newsapi']:
                config['newsapi']['rate_limits']['current_day_requests'] = new_total
                config['newsapi']['rate_limits']['last_reset_date'] = str(date.today())
            
            # 写回配置文件
            with open('config.yaml', 'w', encoding='utf-8') as f:
                yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
            
            # 更新内存中的配置
            self.rate_limits['current_day_requests'] = new_total
            
        except Exception as e:
            logger.error(f"保存配额到配置文件失败: {e}")


def main():
    """测试函数"""
    import yaml
    
    # 加载配置
    with open('config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 初始化 Redis 客户端
    redis_client = RedisClient(**config['redis'])
    
    # 初始化并运行爬虫
    crawler = NewsAPICrawler(config.get('newsapi', {}), redis_client)
    stats = crawler.crawl()
    
    print(f"抓取完成: {stats}")
    
    # 关闭连接
    redis_client.close()


if __name__ == '__main__':
    main()
