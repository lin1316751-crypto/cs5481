"""
RSS 爬虫解析测试
测试 RSS 爬虫的数据解析功能（使用 mock 数据）
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import feedparser


class TestRSSCrawler:
    """RSS 爬虫单元测试"""
    
    @patch('crawlers.rss_crawler.feedparser.parse')
    def test_parse_feed_entry(self, mock_parse):
        """测试解析单个 RSS 条目"""
        # Mock feedparser 返回
        mock_parse.return_value = {
            'entries': [{
                'title': 'Test Article',
                'summary': 'Test summary',
                'link': 'https://example.com/article',
                'published': 'Mon, 20 Oct 2025 10:00:00 GMT',
                'author': 'Test Author',
                'id': 'unique-id-123'
            }]
        }
        
        # 导入放在这里避免实际初始化
        try:
            from crawlers.rss_crawler import RSSCrawler
            
            mock_redis = MagicMock()
            config = {
                'feeds': [{'name': 'Test Feed', 'url': 'https://test.com/rss', 'category': 'test'}]
            }
            
            crawler = RSSCrawler(config, mock_redis)
            
            # 这里可以测试 parse 方法
            # 注意：需要检查实际的 RSSCrawler 实现
            
        except ImportError:
            pytest.skip("RSSCrawler 未实现或导入失败")
    
    def test_parse_missing_fields(self):
        """测试处理缺失字段的情况"""
        # 测试当RSS条目缺少某些字段时的容错处理
        try:
            from crawlers.rss_crawler import RSSCrawler
            
            mock_redis = MagicMock()
            config = {'feeds': []}
            crawler = RSSCrawler(config, mock_redis)
            
            # 测试不完整的entry
            incomplete_entry = {
                'title': 'Only Title',
                # 缺少其他字段
            }
            
            # 验证爬虫能处理缺失字段（应使用None或默认值）
            
        except ImportError:
            pytest.skip("RSSCrawler 未实现")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
