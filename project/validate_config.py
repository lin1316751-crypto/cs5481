"""
配置验证工具
检查配置文件是否正确，并验证 API 连接
"""
import yaml
import sys
import redis
from typing import Dict, List, Tuple

# 颜色输出
class Color:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_success(msg):
    print(f"{Color.GREEN}✓{Color.END} {msg}")

def print_warning(msg):
    print(f"{Color.YELLOW}⚠{Color.END} {msg}")

def print_error(msg):
    print(f"{Color.RED}✗{Color.END} {msg}")

def print_info(msg):
    print(f"{Color.BLUE}ℹ{Color.END} {msg}")


class ConfigValidator:
    """配置验证器"""
    
    def __init__(self, config_file='config.yaml'):
        """
        初始化验证器
        
        Args:
            config_file: 配置文件路径
        """
        self.config_file = config_file
        self.config = None
        self.errors = []
        self.warnings = []
        self.passed_checks = []
    
    def validate(self) -> bool:
        """
        执行所有验证
        
        Returns:
            bool: 验证是否通过
        """
        print("=" * 60)
        print("配置文件验证工具")
        print("=" * 60)
        print()
        
        # 1. 加载配置文件
        if not self._load_config():
            return False
        
        # 2. 验证 Redis 配置
        self._validate_redis()
        
        # 3. 验证爬虫配置
        self._validate_reddit()
        self._validate_newsapi()
        self._validate_rss()
        self._validate_stocktwits()
        
        # 4. 验证调度配置
        self._validate_scheduler()
        
        # 5. 打印总结
        self._print_summary()
        
        return len(self.errors) == 0
    
    def _load_config(self) -> bool:
        """加载配置文件"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
            print_success(f"配置文件加载成功: {self.config_file}")
            return True
        except FileNotFoundError:
            print_error(f"配置文件不存在: {self.config_file}")
            print_info("请创建 config.yaml（可参考 README 配置说明）")
            return False
        except Exception as e:
            print_error(f"配置文件加载失败: {e}")
            return False
    
    def _validate_redis(self):
        """验证 Redis 配置"""
        print("\n" + "-" * 60)
        print("Redis 配置检查")
        print("-" * 60)
        
        if 'redis' not in self.config:
            self.errors.append("缺少 redis 配置段")
            print_error("缺少 redis 配置")
            return
        
        redis_config = self.config['redis']
        host = redis_config.get('host', 'localhost')
        port = redis_config.get('port', 6379)
        db = redis_config.get('db', 0)
        password = redis_config.get('password')
        
        print_info(f"Redis 地址: {host}:{port}")
        print_info(f"数据库: {db}")
        
        # 测试连接
        try:
            client = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                socket_timeout=5,
                decode_responses=True
            )
            client.ping()
            print_success("Redis 连接成功")
            self.passed_checks.append("Redis 连接")
            
            # 检查内存
            info = client.info('memory')
            used_memory_mb = info['used_memory'] / 1024 / 1024
            print_info(f"Redis 内存使用: {used_memory_mb:.2f} MB")
            
            client.close()
        except redis.ConnectionError:
            self.errors.append("Redis 连接失败")
            print_error("Redis 连接失败 - 请确保 Redis 服务已启动")
            print_info("Windows: 运行 redis-server")
        except Exception as e:
            self.warnings.append(f"Redis 检查异常: {e}")
            print_warning(f"Redis 检查异常: {e}")
    
    def _validate_reddit(self):
        """验证 Reddit 配置"""
        print("\n" + "-" * 60)
        print("Reddit 爬虫配置检查")
        print("-" * 60)
        
        if 'reddit' not in self.config:
            self.warnings.append("缺少 reddit 配置")
            print_warning("缺少 reddit 配置")
            return
        
        reddit_config = self.config['reddit']
        
        if not reddit_config.get('enabled', False):
            print_info("Reddit 爬虫已禁用")
            return
        
        # 检查必需字段
        required_fields = ['client_id', 'client_secret', 'user_agent']
        missing_fields = []
        
        for field in required_fields:
            if not reddit_config.get(field):
                missing_fields.append(field)
        
        if missing_fields:
            self.errors.append(f"Reddit 配置缺少: {', '.join(missing_fields)}")
            print_error(f"缺少必需字段: {', '.join(missing_fields)}")
            print_info("获取方法: https://www.reddit.com/prefs/apps")
        else:
            print_success("Reddit 配置完整")
            self.passed_checks.append("Reddit 配置")
            
            # 检查 subreddits
            subreddits = reddit_config.get('subreddits', [])
            if subreddits:
                print_info(f"监控板块: {', '.join(subreddits)}")
            else:
                self.warnings.append("未配置 subreddits")
                print_warning("未配置监控板块")
    
    def _validate_newsapi(self):
        """验证 NewsAPI 配置"""
        print("\n" + "-" * 60)
        print("NewsAPI 爬虫配置检查")
        print("-" * 60)
        
        if 'newsapi' not in self.config:
            self.warnings.append("缺少 newsapi 配置")
            print_warning("缺少 newsapi 配置")
            return
        
        newsapi_config = self.config['newsapi']
        
        if not newsapi_config.get('enabled', False):
            print_info("NewsAPI 爬虫已禁用")
            return
        
        # 检查 API Key
        api_key = newsapi_config.get('api_key')
        if not api_key:
            self.errors.append("NewsAPI 缺少 api_key")
            print_error("缺少 api_key")
            print_info("获取方法: https://newsapi.org/")
        else:
            print_success("NewsAPI 配置完整")
            self.passed_checks.append("NewsAPI 配置")
            
            # 检查 query_keywords（与 config.yaml 字段对齐）
            queries = newsapi_config.get('query_keywords', [])
            if queries:
                print_info(f"搜索关键词: {', '.join(queries[:3])}{'...' if len(queries) > 3 else ''}")
            else:
                self.warnings.append("未配置 query_keywords")
                print_warning("未配置搜索关键词")
    
    def _validate_rss(self):
        """验证 RSS 配置"""
        print("\n" + "-" * 60)
        print("RSS 爬虫配置检查")
        print("-" * 60)
        
        if 'rss' not in self.config:
            self.warnings.append("缺少 rss 配置")
            print_warning("缺少 rss 配置")
            return
        
        rss_config = self.config['rss']
        
        if not rss_config.get('enabled', False):
            print_info("RSS 爬虫已禁用")
            return
        
        # 检查 feeds
        feeds = rss_config.get('feeds', [])
        if not feeds:
            self.warnings.append("未配置 RSS feeds")
            print_warning("未配置 RSS 订阅源")
        else:
            print_success(f"RSS 配置完整 - {len(feeds)} 个订阅源")
            self.passed_checks.append("RSS 配置")
            for feed in feeds[:3]:
                print_info(f"  - {feed.get('name', '未命名')}: {feed.get('url', '')}")
    
    def _validate_stocktwits(self):
        """验证 StockTwits 配置"""
        print("\n" + "-" * 60)
        print("StockTwits 爬虫配置检查")
        print("-" * 60)
        
        if 'stocktwits' not in self.config:
            self.warnings.append("缺少 stocktwits 配置")
            print_warning("缺少 stocktwits 配置")
            return
        
        stocktwits_config = self.config['stocktwits']
        
        if not stocktwits_config.get('enabled', False):
            print_info("StockTwits 爬虫已禁用")
            return
        
        # 检查监控标的
        symbols = stocktwits_config.get('watch_symbols', [])
        if not symbols:
            self.warnings.append("未配置 StockTwits watch_symbols")
            print_warning("未配置监控标的")
        else:
            print_success(f"StockTwits 配置完整 - 监控 {len(symbols)} 个标的")
            print_info(f"标的: {', '.join(symbols)}")
            self.passed_checks.append("StockTwits 配置")
            
            # 提示 API 限制
            requests_per_hour = len(symbols) * 12  # 假设每5分钟抓取一次
            if requests_per_hour > 200:
                self.warnings.append("StockTwits 请求可能超过限制")
                print_warning(f"预计请求: {requests_per_hour}/小时 > 200 (限制)")
            else:
                print_info(f"预计请求: {requests_per_hour}/小时 < 200 (限制) ✓")
        
        # 重要提示
        print_info("💡 StockTwits 无需 API Key，可直接使用")
    
    def _validate_twitter(self):
        """验证 Twitter 配置"""
        print("\n" + "-" * 60)
        print("Twitter 爬虫配置检查")
        print("-" * 60)
        
        if 'twitter' not in self.config:
            self.warnings.append("缺少 twitter 配置")
            print_warning("缺少 twitter 配置")
            return
        
        twitter_config = self.config['twitter']
        
        if not twitter_config.get('enabled', False):
            print_info("Twitter 爬虫已禁用")
            return
        
        # 检查 keywords
        keywords = twitter_config.get('keywords', [])
        if not keywords:
            self.warnings.append("未配置 Twitter keywords")
            print_warning("未配置搜索关键词")
        else:
            print_success(f"Twitter 配置完整 - {len(keywords)} 个关键词")
            print_info(f"关键词: {', '.join(keywords[:3])}{'...' if len(keywords) > 3 else ''}")
            self.passed_checks.append("Twitter 配置")
        
        # 检查工具可用性
        try:
            import snscrape
            print_info("✓ snscrape 已安装（优先使用）")
        except ImportError:
            print_warning("snscrape 未安装")
        
        try:
            import twint
            print_info("✓ twint-fork 已安装（备用）")
        except ImportError:
            print_warning("twint-fork 未安装")
            print_info("建议: pip install twint-fork")
    
    def _validate_scheduler(self):
        """验证调度配置"""
        print("\n" + "-" * 60)
        print("调度器配置检查")
        print("-" * 60)
        
        if 'scheduler' not in self.config:
            self.warnings.append("缺少 scheduler 配置")
            print_warning("缺少 scheduler 配置")
            return
        
        scheduler_config = self.config['scheduler']
        
        # 检查间隔配置
        intervals = {
            'reddit_interval': scheduler_config.get('reddit_interval', 3),
            'newsapi_interval': scheduler_config.get('newsapi_interval', 15),
            'rss_interval': scheduler_config.get('rss_interval', 10),
            'stocktwits_interval': scheduler_config.get('stocktwits_interval', 5),
            'twitter_interval': scheduler_config.get('twitter_interval', 5),
            'export_interval': scheduler_config.get('export_interval', 60)
        }
        
        print_success("调度配置:")
        for name, interval in intervals.items():
            source_name = name.replace('_interval', '').upper()
            print_info(f"  {source_name:15s}: 每 {interval:3d} 分钟")
        
        # 验证 NewsAPI 限制
        newsapi_interval = intervals['newsapi_interval']
        requests_per_day = (24 * 60) // newsapi_interval
        if requests_per_day > 100:
            self.errors.append("NewsAPI 请求超过限制")
            print_error(f"NewsAPI: {requests_per_day} 次/天 > 100 (限制)")
        else:
            print_info(f"NewsAPI: {requests_per_day} 次/天 < 100 (限制) ✓")
        
        self.passed_checks.append("调度配置")
    
    def _print_summary(self):
        """打印验证总结"""
        print("\n" + "=" * 60)
        print("验证总结")
        print("=" * 60)
        
        print(f"\n✓ 通过检查: {len(self.passed_checks)}")
        for check in self.passed_checks:
            print(f"  - {check}")
        
        if self.warnings:
            print(f"\n⚠ 警告: {len(self.warnings)}")
            for warning in self.warnings:
                print(f"  - {warning}")
        
        if self.errors:
            print(f"\n✗ 错误: {len(self.errors)}")
            for error in self.errors:
                print(f"  - {error}")
            print("\n" + "=" * 60)
            print_error("配置验证失败，请修复上述错误")
            print("=" * 60)
        else:
            print("\n" + "=" * 60)
            print_success("配置验证通过！可以开始运行爬虫")
            print("=" * 60)
            print("\n运行命令:")
            print("  单次运行:  python control_center.py")
            print("  定时调度:  python advanced_scheduler.py")


def main():
    """主函数"""
    validator = ConfigValidator()
    
    if validator.validate():
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
