"""
数据导出工具
将 Redis 数据导出为 JSON 或 Parquet 文件，防止内存占用过大，同时保留 Redis 用于实时计算
"""
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from utils.logger import setup_logger
from utils.redis_client import RedisClient

try:
    import pandas as pd  # type: ignore
except Exception:
    pd = None

logger = setup_logger('data_exporter')


class DataExporter:
    """数据导出器"""
    
    def __init__(self, redis_client: RedisClient, export_dir: str = 'data_exports', format: Optional[str] = None):
        """
        初始化数据导出器
        
        Args:
            redis_client: Redis 客户端实例
            export_dir: 导出目录
            format: 导出格式（'json' 或 'parquet'），默认自动从 config.yaml 读取 data_management.archive.format
        """
        self.redis_client = redis_client
        self.export_dir = export_dir
        self.format = (format or self._load_export_format()).lower()
        if self.format not in ('json', 'parquet'):
            self.format = 'json'
        
        # 确保导出目录存在
        if not os.path.exists(export_dir):
            os.makedirs(export_dir)
            logger.info(f"创建导出目录: {export_dir}")
    
    def export_and_trim(self, max_keep: int = 10000, batch_size: int = 1000) -> Dict[str, Any]:
        """
        导出数据并修剪 Redis 队列
        
        Args:
            max_keep: Redis 中保留的最大数据条数（实时计算用）
            batch_size: 批量处理大小
        
        Returns:
            dict: 导出统计信息
        """
        stats = {
            'queue_length_before': 0,
            'exported': 0,
            'queue_length_after': 0,
            'export_file': None
        }
        
        try:
            # 获取当前队列长度
            queue_length = self.redis_client.get_queue_length()
            stats['queue_length_before'] = queue_length
            
            logger.info(f"当前队列长度: {queue_length}")
            
            if queue_length <= max_keep:
                logger.info(f"队列长度未超过阈值 ({max_keep})，无需导出")
                stats['queue_length_after'] = queue_length
                return stats
            
            # 计算需要导出的数据量
            to_export = queue_length - max_keep
            logger.info(f"需要导出 {to_export} 条数据")
            
            # 导出数据
            export_file = self._export_data(to_export, batch_size=batch_size)
            stats['export_file'] = export_file
            stats['exported'] = to_export
            
            # 修剪队列（从右侧移除旧数据）
            self._trim_queue(max_keep)

            # 修剪后重建来源计数（与配额配合）
            try:
                scanned, counts = self.redis_client.rebuild_source_counts(max_scan=max_keep)
                logger.info(f"来源计数已重建：扫描{scanned}条，示例={list(counts.items())[:3]}")
            except Exception:
                pass
            
            # 获取修剪后的队列长度
            stats['queue_length_after'] = self.redis_client.get_queue_length()
            
            logger.info(f"导出完成: {export_file}")
            logger.info(f"队列长度: {stats['queue_length_before']} -> {stats['queue_length_after']}")
            
        except Exception as e:
            logger.error(f"导出数据时出错: {e}")
        
        return stats
    
    def _export_data(self, count: int, batch_size: int = 1000) -> str:
        """
        导出指定数量的数据到 JSON/Parquet 文件（最旧的 count 条）
        
        Args:
            count: 导出数量
        
        Returns:
            str: 导出文件路径
        """
        # 生成文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        ext = 'parquet' if self.format == 'parquet' and pd is not None else 'json'
        filename = f"data_export_{timestamp}.{ext}"
        filepath = os.path.join(self.export_dir, filename)

        # 从 Redis 读取最旧的 count 条：索引从尾部开始的是旧数据，但更稳妥的方式是从头取最新，导出旧数据需计算切片
        # 当前队列头（index=0）是最新，尾部（index=-1）是最旧。我们想导出最旧 count 条，即区间 [max_keep, end]
        client = self.redis_client.client
        queue_name = self.redis_client.queue_name
        length = self.redis_client.get_queue_length()
        start = max(0, length - count)
        end = length - 1

        data_list = []
        for i in range(start, end + 1, batch_size):
            r = min(end, i + batch_size - 1)
            batch = client.lrange(queue_name, i, r)
            data_list.extend([json.loads(item) for item in batch])

        # 写入文件（JSON 或 Parquet）
        if ext == 'json' or pd is None:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump({
                    'export_time': datetime.now().isoformat(),
                    'count': len(data_list),
                    'data': data_list
                }, f, ensure_ascii=False, indent=2)
        else:
            # Parquet 依赖 pandas + pyarrow
            try:
                df = pd.DataFrame(data_list)
                df.to_parquet(filepath, index=False)
            except Exception as e:
                logger.error(f"Parquet 导出失败，回退 JSON: {e}")
                # 回退到 JSON
                json_path = filepath.replace('.parquet', '.json')
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump({
                        'export_time': datetime.now().isoformat(),
                        'count': len(data_list),
                        'data': data_list
                    }, f, ensure_ascii=False, indent=2)
                filepath = json_path

        logger.info(f"已导出 {len(data_list)} 条数据到 {filepath}")
        return filepath
    
    def _trim_queue(self, max_keep: int):
        """
        修剪队列，只保留最新的数据
        
        Args:
            max_keep: 保留的最大数据条数
        """
        client = self.redis_client.client
        queue_name = self.redis_client.queue_name
        # LTRIM 保留最新的 max_keep 条数据（头部是最新）
        client.ltrim(queue_name, 0, max_keep - 1)
        logger.info(f"队列已修剪，保留最新 {max_keep} 条数据")
    
    def export_by_source(self, max_per_source: int = 5000) -> Dict[str, Any]:
        """
        按数据源分别导出
        
        Args:
            max_per_source: 每个数据源保留的最大数据量
        
        Returns:
            dict: 导出统计信息
        """
        stats = {}
        
        try:
            # 获取所有数据
            all_data = self.redis_client.peek_data(100000)  # 读取大量数据
            
            # 按来源分组
            by_source = {}
            for item in all_data:
                source = item.get('source', 'unknown')
                if source not in by_source:
                    by_source[source] = []
                by_source[source].append(item)
            
            # 分别导出
            for source, data_list in by_source.items():
                if len(data_list) > max_per_source:
                    # 导出旧数据
                    to_export = data_list[max_per_source:]
                    self._export_source_data(source, to_export)
                    stats[source] = len(to_export)
            
        except Exception as e:
            logger.error(f"按来源导出数据时出错: {e}")
        
        return stats
    
    def _export_source_data(self, source: str, data_list: List[Dict]):
        """导出特定来源的数据"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"data_{source}_{timestamp}.json"
        filepath = os.path.join(self.export_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                'export_time': datetime.now().isoformat(),
                'source': source,
                'count': len(data_list),
                'data': data_list
            }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"已导出 {source} 的 {len(data_list)} 条数据到 {filepath}")

    # ============== 内部工具 ==============
    def _load_export_format(self) -> str:
        """从 config.yaml 读取 data_management.archive.format，默认 json。"""
        try:
            import yaml
            with open('config.yaml', 'r', encoding='utf-8') as f:
                cfg = yaml.safe_load(f) or {}
            fmt = (((cfg.get('data_management') or {}).get('archive') or {}).get('format') or 'json')
            return str(fmt)
        except Exception:
            return 'json'


def main():
    """测试函数"""
    import yaml
    
    # 加载配置
    with open('config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 初始化 Redis 客户端
    redis_client = RedisClient(**config['redis'])
    
    # 初始化导出器
    exporter = DataExporter(redis_client)
    
    # 执行导出和修剪
    stats = exporter.export_and_trim(max_keep=10000)
    
    print(f"导出完成: {stats}")
    
    # 关闭连接
    redis_client.close()


if __name__ == '__main__':
    main()
