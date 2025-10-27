"""
StockTwits 爬虫模块
抓取 StockTwits 上的金融讨论和情绪数据
"""
import time
import requests
from datetime import datetime
from typing import List, Dict, Any
from utils.logger import setup_logger
from utils.redis_client import RedisClient

logger = setup_logger('stocktwits_crawler')


class StockTwitsCrawler:
    """StockTwits 爬虫类"""
    
    def __init__(self, config: dict, redis_client: RedisClient):
        """
        初始化 StockTwits 爬虫
        
        Args:
            config: StockTwits 配置字典
            redis_client: Redis 客户端实例
        """
        self.config = config
        self.redis_client = redis_client
        self.enabled = config.get('enabled', False)
        # 修复:读取 watch_symbols 配置
        self.symbols = config.get('watch_symbols', config.get('symbols', []))
        # 修复:读取 messages_per_symbol 配置
        self.max_messages = config.get('messages_per_symbol', config.get('max_messages', 30))
        # 读取 API Token (如果有)
        self.access_token = config.get('access_token')
        self.base_url = "https://api.stocktwits.com/api/2"
        
        if not self.enabled:
            logger.info("StockTwits 爬虫已禁用")
        else:
            logger.info(f"StockTwits 爬虫初始化成功，监控股票: {', '.join(self.symbols)}")
    
    def crawl(self) -> Dict[str, int]:
        """
        执行抓取任务
        
        Returns:
            dict: 抓取统计信息 {'messages': 数量, 'errors': 数量}
        """
        stats = {'messages': 0, 'errors': 0}
        
        if not self.enabled:
            logger.warning("StockTwits 爬虫未启用，跳过")
            return stats
        
        logger.info("开始抓取 StockTwits 数据...")
        
        for symbol in self.symbols:
            try:
                logger.info(f"正在抓取股票: ${symbol}")
                
                # 抓取股票流
                messages = self._fetch_symbol_stream(symbol)
                
                symbol_count = 0
                for message in messages:
                    message_data = self._extract_message_data(message, symbol)
                    if message_data and self.redis_client.push_data(message_data):
                        stats['messages'] += 1
                        symbol_count += 1
                
                logger.info(f"✓ 股票 ${symbol} 抓取完成 - 消息: {symbol_count}")
                
                # 避免请求过快
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"抓取股票 ${symbol} 时出错: {e}")
                stats['errors'] += 1
        
        logger.info(f"StockTwits 抓取完成 - 消息: {stats['messages']}, 错误: {stats['errors']}")
        return stats
    
    def _fetch_symbol_stream(self, symbol: str) -> List[Dict]:
        """
        获取股票的消息流
        
        Args:
            symbol: 股票代码（如 AAPL）
        
        Returns:
            list: 消息列表
        """
        try:
            # StockTwits API 端点
            url = f"{self.base_url}/streams/symbol/{symbol}.json"
            params = {
                'limit': self.max_messages
            }
            
            # 如果有 access_token,添加到参数中
            if self.access_token:
                params['access_token'] = self.access_token
            
            # 添加请求头,模拟浏览器访问
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
                'Referer': f'https://stocktwits.com/symbol/{symbol}'
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            messages = data.get('messages', [])
            
            return messages
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                logger.error(f"${symbol} API 访问被拒绝 (403) - StockTwits 可能需要 API Token")
                logger.info("建议: 访问 https://stocktwits.com/developers 注册 API Token")
            else:
                logger.error(f"获取 ${symbol} 消息流失败: {e}")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"获取 ${symbol} 消息流失败: {e}")
            return []
        except Exception as e:
            logger.error(f"解析 ${symbol} 数据失败: {e}")
            return []
    
    def _extract_message_data(self, message: dict, symbol: str) -> Dict[str, Any]:
        """
        提取消息数据 - 包含完整的情感和互动信息
        
        Args:
            message: StockTwits 消息对象
            symbol: 股票代码
        
        Returns:
            dict: 消息数据
        """
        try:
            # 提取用户信息
            user = message.get('user', {})
            
            # 提取情感（StockTwits 特有的情感标签）
            entities = message.get('entities', {})
            sentiment = entities.get('sentiment', {})
            
            # 提取时间戳
            created_at = message.get('created_at', '')
            try:
                from dateutil import parser as date_parser
                dt = date_parser.parse(created_at)
                timestamp = int(dt.timestamp())
            except:
                timestamp = int(datetime.now().timestamp())
            
            data = {
                'text': message.get('body', ''),
                'source': 'stocktwits',
                'timestamp': timestamp,
                'url': f"https://stocktwits.com/{user.get('username')}/message/{message.get('id')}",
                
                # 股票信息
                'symbol': symbol,
                'symbols': [s.get('symbol') for s in entities.get('symbols', [])],
                
                # 用户信息
                'user': user.get('username', 'unknown'),
                'user_id': user.get('id', ''),
                'user_followers': user.get('followers', 0),
                'user_following': user.get('following', 0),
                'user_ideas': user.get('ideas', 0),
                
                # 情感信息（重要！用于情感分析）
                'sentiment': sentiment.get('basic') if sentiment else None,  # 'Bullish' 或 'Bearish'
                
                # 互动数据
                'likes': message.get('likes', {}).get('total', 0),
                'reshares': message.get('reshare_count', 0),
                'replies': message.get('conversation', {}).get('replies', 0),
                
                # 其他元数据
                'message_id': message.get('id', ''),
                'hashtags': [tag for tag in message.get('entities', {}).get('chart', {}).get('tags', [])],
                'links': [link.get('url') for link in entities.get('links', [])],
            }
            
            return data
            
        except Exception as e:
            logger.error(f"提取消息数据失败: {e}")
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
    crawler = StockTwitsCrawler(config.get('stocktwits', {}), redis_client)
    stats = crawler.crawl()
    
    print(f"抓取完成: {stats}")
    
    # 关闭连接
    redis_client.close()


if __name__ == '__main__':
    main()
