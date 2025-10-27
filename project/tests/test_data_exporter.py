"""
数据导出器单元测试
测试 DataExporter 的导出和修剪功能
"""
import pytest
import json
import os
from unittest.mock import Mock, patch, MagicMock, mock_open
from utils.data_exporter import DataExporter
from utils.redis_client import RedisClient


class TestDataExporter:
    """DataExporter 单元测试"""
    
    @patch('utils.data_exporter.os.makedirs')
    @patch('utils.data_exporter.os.path.exists')
    def test_init(self, mock_exists, mock_makedirs):
        """测试导出器初始化"""
        mock_exists.return_value = False
        mock_redis = MagicMock(spec=RedisClient)
        
        exporter = DataExporter(
            redis_client=mock_redis,
            export_dir='test_exports',
            format='json'
        )
        
        assert exporter.export_dir == 'test_exports'
        assert exporter.format == 'json'
        mock_makedirs.assert_called_once_with('test_exports')
    
    @patch('utils.data_exporter.os.path.exists', return_value=True)
    def test_export_and_trim_no_need(self, mock_exists):
        """测试队列未超阈值时不导出"""
        mock_redis = MagicMock(spec=RedisClient)
        mock_redis.get_queue_length.return_value = 500  # 小于max_keep
        
        exporter = DataExporter(mock_redis, 'test_exports')
        stats = exporter.export_and_trim(max_keep=1000)
        
        assert stats['exported'] == 0
        assert stats['export_file'] is None
        assert stats['queue_length_before'] == 500
    
    @patch('utils.data_exporter.os.path.exists', return_value=True)
    @patch('builtins.open', new_callable=mock_open)
    @patch('utils.data_exporter.json.dump')
    def test_export_and_trim_json(self, mock_json_dump, mock_file, mock_exists):
        """测试 JSON 导出功能"""
        mock_redis = MagicMock(spec=RedisClient)
        # 调用顺序: 1. 导出前检查 (1500), 2. _export_data内部 (1500), 3. 导出后检查 (1000)
        mock_redis.get_queue_length.side_effect = [1500, 1500, 1000]
        
        # 创建 mock client 属性
        mock_client = MagicMock()
        mock_client.lrange.return_value = [
            json.dumps({'source': 'reddit', 'text': f'old_post_{i}'})
            for i in range(500)
        ]
        mock_redis.client = mock_client
        mock_redis.queue_name = 'test_queue'
        
        # mock ltrim 操作
        mock_client.ltrim.return_value = None
        
        mock_redis.rebuild_source_counts.return_value = (1000, {'reddit': 800, 'twitter': 200})
        
        exporter = DataExporter(mock_redis, 'test_exports', format='json')
        stats = exporter.export_and_trim(max_keep=1000, batch_size=100)
        
        assert stats['queue_length_before'] == 1500
        assert stats['exported'] == 500
        assert stats['queue_length_after'] == 1000
        assert stats['export_file'] is not None
        # 验证导出文件被写入
        mock_json_dump.assert_called_once()
        # 验证队列被修剪
        mock_client.ltrim.assert_called_once_with('test_queue', 0, 999)
        # 验证来源计数被重建
        mock_redis.rebuild_source_counts.assert_called_once()


class TestDataExporterIntegration:
    """数据导出器集成测试（需要真实Redis环境）"""
    
    @pytest.mark.skip(reason="需要真实 Redis 服务器")
    def test_export_real_data(self):
        """集成测试：真实导出数据"""
        # 此测试需要真实 Redis 连接
        pass


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
