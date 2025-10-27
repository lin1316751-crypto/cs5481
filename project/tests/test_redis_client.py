"""
Redis 客户端单元测试
测试 RedisClient 的核心功能：连接、推送、配额管理
"""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from utils.redis_client import RedisClient


class TestRedisClient:
    """RedisClient 单元测试"""
    
    @patch('utils.redis_client.redis.Redis')
    def test_init_success(self, mock_redis):
        """测试 Redis 客户端初始化成功"""
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_redis.return_value = mock_client
        
        client = RedisClient(
            host='localhost',
            port=6379,
            queue_name='test_queue',
            storage_config={'max_keep': 1000},
            source_quotas={'reddit': 0.5, 'twitter': 0.3}
        )
        
        assert client.queue_name == 'test_queue'
        assert client.max_keep == 1000
        assert client.source_quotas == {'reddit': 0.5, 'twitter': 0.3}
        mock_client.ping.assert_called_once()
    
    @patch('utils.redis_client.redis.Redis')
    def test_push_data_success(self, mock_redis):
        """测试成功推送数据"""
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_client.llen.return_value = 100
        mock_client.get.return_value = '10'  # 来源计数
        mock_redis.return_value = mock_client
        
        client = RedisClient(queue_name='test_queue')
        data = {'source': 'reddit', 'title': 'Test Post', 'text': 'Content'}
        
        result = client.push_data(data)
        
        assert result is True
        mock_client.lpush.assert_called_once()
        mock_client.incr.assert_called_once()
    
    @patch('utils.redis_client.redis.Redis')
    def test_push_data_quota_exceeded(self, mock_redis):
        """测试配额超限时拒绝推送"""
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_client.get.return_value = '600'  # 已有600条reddit数据
        mock_redis.return_value = mock_client
        
        # 配额：reddit占50%，max_keep=1000，即500条上限
        client = RedisClient(
            queue_name='test_queue',
            storage_config={'max_keep': 1000},
            source_quotas={'reddit': 0.5}
        )
        
        data = {'source': 'reddit', 'title': 'Test'}
        result = client.push_data(data)
        
        # 应该拒绝推送
        assert result is False
        mock_client.lpush.assert_not_called()
    
    @patch('utils.redis_client.redis.Redis')
    def test_get_queue_length(self, mock_redis):
        """测试获取队列长度"""
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_client.llen.return_value = 12345
        mock_redis.return_value = mock_client
        
        client = RedisClient(queue_name='test_queue')
        length = client.get_queue_length()
        
        assert length == 12345
        mock_client.llen.assert_called_once_with('test_queue')
    
    @patch('utils.redis_client.redis.Redis')
    def test_rebuild_source_counts(self, mock_redis):
        """测试重建来源计数"""
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_client.llen.return_value = 5
        mock_client.lrange.return_value = [
            json.dumps({'source': 'reddit', 'text': 'post1'}),
            json.dumps({'source': 'reddit', 'text': 'post2'}),
            json.dumps({'source': 'twitter', 'text': 'tweet1'}),
            json.dumps({'source': 'rss', 'text': 'article1'}),
            json.dumps({'source': 'reddit', 'text': 'post3'}),
        ]
        
        # Mock pipeline
        mock_pipeline = MagicMock()
        mock_client.pipeline.return_value = mock_pipeline
        
        mock_redis.return_value = mock_client
        
        client = RedisClient(queue_name='test_queue')
        scanned, counts = client.rebuild_source_counts()
        
        assert scanned == 5
        assert counts['reddit'] == 3
        assert counts['twitter'] == 1
        assert counts['rss'] == 1
        
        # 验证 pipeline 被使用
        mock_client.pipeline.assert_called_once()
        # 验证 pipeline.set 被调用 3 次（3 个不同的来源）
        assert mock_pipeline.set.call_count == 3
        # 验证 pipeline.execute 被调用
        mock_pipeline.execute.assert_called_once()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
