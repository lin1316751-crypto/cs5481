"""
RSS 爬虫模块
抓取财经新闻网站的 RSS 订阅源
支持全文抓取 (使用 newspaper3k)
"""
import time
import socket
import feedparser
from datetime import datetime
from typing import List, Dict, Any
from dateutil import parser as date_parser
from newspaper import Article
from newspaper.article import ArticleException
import requests
from utils.logger import setup_logger
from utils.redis_client import RedisClient

logger = setup_logger('rss_crawler')


class RSSCrawler:
    """RSS 爬虫类 (支持全文抓取)"""
    
    def __init__(self, config: dict, redis_client: RedisClient):
        """
        初始化 RSS 爬虫
        
        Args:
            config: RSS 配置字典
            redis_client: Redis 客户端实例
        """
        self.config = config
        self.redis_client = redis_client
        self.feeds = config.get('feeds', [])
        self.fetch_full_content = config.get('fetch_full_content', True)  # 是否抓取全文
        
        logger.info(f"RSS 爬虫初始化完成，订阅源数量: {len(self.feeds)}")
        if self.fetch_full_content:
            logger.info("✓ 全文抓取已启用 (使用 newspaper3k)")
    
    def crawl(self) -> Dict[str, int]:
        """
        执行抓取任务
        
        Returns:
            dict: 抓取统计信息 {'articles': 数量, 'errors': 数量}
        """
        stats = {'articles': 0, 'errors': 0}
        
        logger.info("开始抓取 RSS 数据...")
        
        for feed_config in self.feeds:
            feed_name = feed_config.get('name', 'Unknown')
            feed_url = feed_config.get('url')
            
            if not feed_url:
                logger.warning(f"RSS 源 {feed_name} 缺少 URL，跳过")
                continue
            
            try:
                logger.info(f"正在抓取 RSS 源: {feed_name}")
                
                # 解析 RSS (带超时和重试)
                feed = self._fetch_feed_with_timeout(feed_url, feed_name)
                
                # 检查是否解析成功
                if not feed or feed.bozo:
                    if feed and feed.bozo:
                        logger.warning(f"RSS 源 {feed_name} 解析警告: {feed.bozo_exception}")
                    continue
                
                # 提取文章
                for entry in feed.entries:
                    article_data = self._extract_article_data(entry, feed_name, feed_config)
                    if article_data and self.redis_client.push_data(article_data):
                        stats['articles'] += 1
                
                logger.info(f"RSS 源 {feed_name} 抓取完成，文章数: {len(feed.entries)}")
                
                # 避免请求过快
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"抓取 RSS 源 {feed_name} 时出错: {e}")
                stats['errors'] += 1
        
        logger.info(f"RSS 抓取完成 - 文章: {stats['articles']}, 错误: {stats['errors']}")
        return stats
    
    def _fetch_feed_with_timeout(self, url: str, feed_name: str, timeout: int = 10, max_retries: int = 2):
        """
        获取 RSS 源，带超时和重试机制
        
        Args:
            url: RSS 源 URL
            feed_name: RSS 源名称
            timeout: 超时时间（秒）
            max_retries: 最大重试次数
        
        Returns:
            feedparser.FeedParserDict 或 None
        """
        for attempt in range(max_retries):
            try:
                # 设置超时
                original_timeout = socket.getdefaulttimeout()
                socket.setdefaulttimeout(timeout)
                
                # 解析 RSS
                feed = feedparser.parse(url)
                
                # 恢复原超时设置
                socket.setdefaulttimeout(original_timeout)
                
                # 检查是否成功
                if feed and not feed.bozo:
                    return feed
                elif feed and feed.bozo:
                    logger.warning(f"RSS 源 {feed_name} 解析失败 (尝试 {attempt+1}/{max_retries}): {feed.bozo_exception}")
                else:
                    logger.warning(f"RSS 源 {feed_name} 返回空结果 (尝试 {attempt+1}/{max_retries})")
                    
            except socket.timeout:
                logger.warning(f"RSS 源 {feed_name} 请求超时 (尝试 {attempt+1}/{max_retries}): {timeout}秒")
            except Exception as e:
                logger.warning(f"RSS 源 {feed_name} 请求失败 (尝试 {attempt+1}/{max_retries}): {str(e)}")
            finally:
                # 确保恢复原超时设置
                try:
                    socket.setdefaulttimeout(original_timeout)
                except:
                    pass
            
            # 等待后重试
            if attempt < max_retries - 1:
                time.sleep(2)
        
        logger.error(f"RSS 源 {feed_name} 完全失败，跳过: {url}")
        return None
    
    def _extract_article_data(self, entry, feed_name: str, feed_config: dict = None) -> Dict[str, Any]:
        """
        提取文章数据 - 完整信息（增强版）
        
        Args:
            entry: feedparser entry 对象
            feed_name: RSS 源名称
            feed_config: RSS 源配置（包含 url, category 等）
        
        Returns:
            dict: 文章数据
        """
        try:
            # ===== 核心必备字段 =====
            title = entry.get('title', '').strip()
            url = entry.get('link', '').strip()
            guid = entry.get('id', entry.get('guid', url))  # 唯一ID，用于去重
            
            # 提取摘要或内容
            summary = entry.get('summary', entry.get('description', '')).strip()
            content = ''
            if entry.get('content'):
                content = entry.content[0].get('value', '').strip()
            
            # ===== 全文抓取 (如果启用) =====
            full_text = None
            if self.fetch_full_content and url:
                full_text = self._fetch_full_article(url)
                if full_text:
                    logger.debug(f"✓ 全文抓取成功: {url[:50]}... ({len(full_text)} 字)")
                    content = full_text  # 用全文替换 content
            
            # 组合文本（用于情绪分析等）
            text = title
            if summary:
                text += "\n\n" + summary
            if content and content != summary:
                text += "\n\n" + content
            
            # 提取发布时间
            published = self._extract_timestamp(entry)
            
            # ===== 来源信息字段 =====
            feed_url = feed_config.get('url', '') if feed_config else ''
            feed_category = feed_config.get('category', 'uncategorized') if feed_config else 'uncategorized'
            
            # 提取发布机构（从 feed_name 中提取）
            publisher = feed_name.split(' - ')[0] if ' - ' in feed_name else feed_name
            
            # ===== 作者与分类 =====
            author = entry.get('author', entry.get('dc_creator', entry.get('creator', '')))
            if not author:
                author = publisher  # 如果没有作者，使用发布机构
            
            # 提取分类/标签
            category = entry.get('category', '')
            tags = []
            if hasattr(entry, 'tags') and entry.tags:
                tags = [tag.get('term', '') for tag in entry.tags if tag.get('term')]
            
            # 如果没有 tags，尝试从 category 提取
            if not tags and category:
                tags = [category]
            
            # ===== 内容增强字段 =====
            # 检测语言
            language = self._detect_language(title + summary)
            
            # 提取媒体链接
            media_url = None
            media_type = None
            if hasattr(entry, 'media_content') and entry.media_content:
                media_url = entry.media_content[0].get('url', '')
                media_type = entry.media_content[0].get('medium', 'image')
            elif hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
                media_url = entry.media_thumbnail[0].get('url', '')
                media_type = 'image'
            
            # ===== 元数据字段 =====
            crawl_timestamp = int(time.time())
            updated = self._extract_timestamp(entry, field='updated_parsed') or published
            
            # 字数统计（用于筛选低质量文章）
            word_count = len(text.split())
            
            # ===== 构建完整数据 =====
            data = {
                # 核心必备字段
                'title': title,
                'summary': summary,
                'url': url,
                'published': published,
                'guid': guid,
                'source': 'rss',
                
                # 来源信息
                'feed_source': feed_name,
                'feed_url': feed_url,
                'feed_category': feed_category,
                'publisher': publisher,
                
                # 作者与分类
                'author': author,
                'category': category,
                'tags': tags,
                
                # 内容增强
                'content': content if content else None,
                'language': language,
                'media_url': media_url,
                'media_type': media_type,
                
                # 元数据
                'crawl_timestamp': crawl_timestamp,
                'updated': updated,
                'word_count': word_count,
                
                # 向后兼容（旧字段）
                'text': text,  # 保留旧的 text 字段
                'timestamp': published  # 保留旧的 timestamp 字段
            }
            
            return data
            
        except Exception as e:
            logger.error(f"提取文章数据失败: {e}")
            return None
    
    def _fetch_full_article(self, url: str) -> str:
        """
        抓取文章全文 (使用 newspaper3k + 自定义请求头)
        
        Args:
            url: 文章链接
        
        Returns:
            str: 文章全文,失败返回 None
        """
        try:
            # 配置自定义请求头 (模拟真实浏览器)
            config = {
                'browser_user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'request_timeout': 10,
                'number_threads': 1,
                'fetch_images': False,  # 不抓取图片,提升速度
                'memoize_articles': False  # 不缓存,避免内存占用
            }
            
            # 创建 Article 对象
            article = Article(url, language='en', config=config)
            
            # 添加额外的 HTTP 头部
            article.config.headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Cache-Control': 'max-age=0'
            }
            
            # 下载并解析
            article.download()
            article.parse()
            
            # 获取正文
            full_text = article.text
            
            # 验证内容质量
            if full_text and len(full_text) > 100:  # 至少 100 字符
                return full_text
            else:
                logger.warning(f"全文太短或为空: {url}")
                return None
                
        except ArticleException as e:
            logger.warning(f"newspaper3k 抓取失败,尝试备用方案: {url}")
            # 备用方案: 使用 requests 直接抓取
            return self._fetch_full_article_fallback(url)
            
        except Exception as e:
            logger.debug(f"全文抓取失败: {url} - {e}")
            return None
    
    def _fetch_full_article_fallback(self, url: str) -> str:
        """
        备用全文抓取方案 (使用 requests + BeautifulSoup)
        
        Args:
            url: 文章链接
        
        Returns:
            str: 文章全文,失败返回 None
        """
        try:
            from bs4 import BeautifulSoup
            
            # 自定义请求头 (模拟真实浏览器)
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Referer': 'https://www.google.com/'  # 伪装来源
            }
            
            # 发送请求
            response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
            response.raise_for_status()
            
            # 解析 HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 移除脚本和样式
            for script in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                script.decompose()
            
            # 尝试多种常见的正文容器
            content_selectors = [
                'article',
                '.article-body',
                '.article-content',
                '.post-content',
                '.entry-content',
                '.content',
                'main',
                '[itemprop="articleBody"]'
            ]
            
            text = None
            for selector in content_selectors:
                elements = soup.select(selector)
                if elements:
                    text = elements[0].get_text(separator='\n', strip=True)
                    if len(text) > 100:
                        logger.debug(f"✓ 备用方案成功: {url} (选择器: {selector})")
                        return text
            
            # 如果没找到特定容器,提取所有段落
            if not text:
                paragraphs = soup.find_all('p')
                text = '\n\n'.join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 20])
                if len(text) > 100:
                    logger.debug(f"✓ 备用方案成功 (提取段落): {url}")
                    return text
            
            logger.warning(f"备用方案也失败: {url} - 内容太短")
            return None
            
        except Exception as e:
            logger.debug(f"备用方案失败: {url} - {e}")
            return None
    
    def _detect_language(self, text: str) -> str:
        """
        简单的语言检测
        
        Args:
            text: 文本内容
        
        Returns:
            str: 语言代码 ('en', 'zh', 'zh-CN')
        """
        if not text:
            return 'unknown'
        
        # 统计中文字符
        chinese_count = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
        total_count = len(text)
        
        if total_count == 0:
            return 'unknown'
        
        # 如果中文字符超过30%，判断为中文
        if chinese_count / total_count > 0.3:
            return 'zh-CN'
        elif chinese_count > 0:
            return 'zh'  # 包含部分中文
        else:
            return 'en'
    
    def _extract_timestamp(self, entry, field='published_parsed') -> int:
        """
        提取时间戳
        
        Args:
            entry: feedparser entry 对象
            field: 时间字段名 ('published_parsed', 'updated_parsed')
        
        Returns:
            int: Unix 时间戳
        """
        try:
            # 优先使用 parsed 时间
            time_struct = entry.get(field)
            if time_struct:
                return int(time.mktime(time_struct))
            
            # 备用: 尝试解析字符串时间
            time_str = entry.get(field.replace('_parsed', ''))
            if time_str:
                dt = date_parser.parse(time_str)
                return int(dt.timestamp())
            
            # 如果都没有，返回当前时间
            logger.warning(f"无法提取时间戳，使用当前时间")
            return int(time.time())
            
        except Exception as e:
            logger.warning(f"解析时间戳失败: {e}，使用当前时间")
            return int(time.time())
        """
        提取时间戳
        
        Args:
            entry: feedparser entry 对象
        
        Returns:
            int: Unix 时间戳
        """
        # 尝试多种时间字段
        time_fields = ['published', 'updated', 'created']
        
        for field in time_fields:
            if field in entry:
                try:
                    # 解析时间字符串
                    dt = date_parser.parse(entry[field])
                    return int(dt.timestamp())
                except Exception as e:
                    logger.debug(f"解析时间字段 {field} 失败: {e}")
        
        # 如果都失败，使用当前时间
        logger.warning(f"无法提取文章时间，使用当前时间")
        return int(datetime.now().timestamp())


def main():
    """测试函数"""
    import yaml
    
    # 加载配置
    with open('config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 初始化 Redis 客户端
    redis_client = RedisClient(**config['redis'])
    
    # 初始化并运行爬虫
    crawler = RSSCrawler(config['rss'], redis_client)
    stats = crawler.crawl()
    
    print(f"抓取完成: {stats}")
    
    # 关闭连接
    redis_client.close()


if __name__ == '__main__':
    main()
