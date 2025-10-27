"""
爬虫模块初始化文件
"""
from crawlers.reddit_crawler import RedditCrawler
from crawlers.rss_crawler import RSSCrawler
from crawlers.newsapi_crawler import NewsAPICrawler
from crawlers.stocktwits_crawler import StockTwitsCrawler
from crawlers.alphavantage_crawler import AlphaVantageCrawler  # ✅ 新增

__all__ = ['RedditCrawler', 'RSSCrawler', 'NewsAPICrawler', 'StockTwitsCrawler', 'AlphaVantageCrawler']
