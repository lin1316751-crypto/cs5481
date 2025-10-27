#!/usr/bin/env python3
"""
智能数据导出器 - 自动导出 Redis 数据到本地文件
防止 Redis 内存占用过高
"""

import os
import json
import gzip
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# 尝试导入 pandas (用于 Parquet 格式)
try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
    logger.warning("pandas 未安装，Parquet 格式不可用。安装: pip install pandas pyarrow")


class SmartExporter:
    """
    智能数据导出器
    
    功能:
    1. 监控 Redis 内存/队列使用情况
    2. 自动触发导出 (基于内存/队列/时间)
    3. 支持多种格式: JSON, JSON.GZ, Parquet
    4. 自动清理过期归档
    """
    
    def __init__(self, redis_client, config: Dict[str, Any]):
        """
        初始化智能导出器
        
        Args:
            redis_client: Redis 客户端实例
            config: 配置字典
        """
        self.redis_client = redis_client
        self.config = config
        
        # 导出目录
        self.export_dir = Path(config.get('export_dir', 'data_exports'))
        self.archive_dir = self.export_dir / 'archive'
        
        # 创建目录
        self.export_dir.mkdir(exist_ok=True)
        self.archive_dir.mkdir(exist_ok=True)
        
        # 自动导出配置
        self.auto_export_config = config.get('auto_export', {})
        self.enabled = self.auto_export_config.get('enabled', True)
        self.queue_threshold = self.auto_export_config.get('queue_threshold', 5000)
        self.memory_threshold_mb = self.auto_export_config.get('memory_threshold_mb', 100)
        self.time_interval = self.auto_export_config.get('time_interval_minutes', 60)
        
        # 归档配置
        self.archive_config = config.get('archive', {})
        self.compress = self.archive_config.get('compress', True)
        self.retention_days = self.archive_config.get('retention_days', 30)
        self.export_format = self.archive_config.get('format', 'json')
        
        # 上次导出时间
        self.last_export_time = None
        
        logger.info(f"SmartExporter 初始化完成")
        logger.info(f"导出目录: {self.export_dir}")
        logger.info(f"队列阈值: {self.queue_threshold}")
        logger.info(f"内存阈值: {self.memory_threshold_mb}MB")
        logger.info(f"时间间隔: {self.time_interval}分钟")
        logger.info(f"导出格式: {self.export_format}")
    
    def should_export(self) -> tuple[bool, str]:
        """
        判断是否需要导出
        
        Returns:
            (是否导出, 触发原因)
        """
        if not self.enabled:
            return False, "自动导出未启用"
        
        # 检查1: 队列长度
        try:
            queue_length = self.redis_client.get_queue_length()
            if queue_length > self.queue_threshold:
                return True, f"队列长度 {queue_length} > 阈值 {self.queue_threshold}"
        except Exception as e:
            logger.error(f"检查队列长度失败: {e}")
        
        # 检查2: 内存使用
        try:
            memory_info = self.redis_client.get_memory_usage()
            used_mb = memory_info.get('used_memory_mb', 0)
            if used_mb > self.memory_threshold_mb:
                return True, f"内存使用 {used_mb:.1f}MB > 阈值 {self.memory_threshold_mb}MB"
        except Exception as e:
            logger.error(f"检查内存使用失败: {e}")
        
        # 检查3: 时间间隔
        if self.last_export_time:
            elapsed = (datetime.now() - self.last_export_time).total_seconds() / 60
            if elapsed >= self.time_interval:
                return True, f"距上次导出 {elapsed:.0f}分钟 >= {self.time_interval}分钟"
        else:
            # 首次运行
            return True, "首次运行，执行初始导出"
        
        return False, "无需导出"
    
    def export(self, batch_size: int = 1000) -> Dict[str, Any]:
        """
        导出数据到本地文件
        
        Args:
            batch_size: 批量大小
            
        Returns:
            导出统计信息
        """
        stats = {
            'exported': 0,
            'export_file': None,
            'format': self.export_format,
            'file_size_mb': 0,
            'start_time': datetime.now(),
            'end_time': None,
            'error': None
        }
        
        try:
            # 获取队列长度
            total = self.redis_client.get_queue_length()
            if total == 0:
                logger.info("队列为空，跳过导出")
                stats['error'] = "队列为空"
                return stats
            
            # 计算需要导出的数量
            max_keep = getattr(self.redis_client, 'max_keep', 10000)
            to_export = max(0, total - max_keep)
            
            if to_export == 0:
                logger.info(f"队列长度 {total} 未超过 {max_keep}，跳过导出")
                stats['error'] = f"队列长度未超过阈值 ({total}/{max_keep})"
                return stats
            
            logger.info(f"开始导出 {to_export} 条数据（保留 {max_keep} 条在 Redis）")
            
            # 分批获取数据
            all_data = []
            batch_count = 0
            for i in range(0, to_export, batch_size):
                count = min(batch_size, to_export - i)
                batch = self.redis_client.get_data(count)
                all_data.extend(batch)
                batch_count += 1
                
                if batch_count % 10 == 0:
                    logger.info(f"已获取 {len(all_data)}/{to_export} 条数据...")
            
            if not all_data:
                logger.warning("未获取到任何数据")
                stats['error'] = "未获取到数据"
                return stats
            
            # 生成文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # 根据格式导出
            if self.export_format == 'parquet' and HAS_PANDAS:
                filename = f'data_{timestamp}.parquet'
                filepath = self.export_dir / filename
                self._export_parquet(all_data, filepath)
            elif self.export_format == 'json' and self.compress:
                filename = f'data_{timestamp}.json.gz'
                filepath = self.export_dir / filename
                self._export_json_gz(all_data, filepath)
            else:
                filename = f'data_{timestamp}.json'
                filepath = self.export_dir / filename
                self._export_json(all_data, filepath)
            
            # 计算文件大小
            file_size = filepath.stat().st_size / 1024 / 1024  # MB
            
            stats['exported'] = len(all_data)
            stats['export_file'] = str(filepath)
            stats['file_size_mb'] = round(file_size, 2)
            stats['end_time'] = datetime.now()
            
            duration = (stats['end_time'] - stats['start_time']).total_seconds()
            logger.info(f"✓ 导出完成: {stats['exported']} 条 → {filepath.name} ({file_size:.2f}MB)")
            logger.info(f"  耗时: {duration:.1f}秒")
            
            # 更新上次导出时间
            self.last_export_time = datetime.now()
            
            # 清理旧归档
            self._cleanup_old_archives()
            
            return stats
            
        except Exception as e:
            logger.error(f"导出失败: {e}", exc_info=True)
            stats['error'] = str(e)
            stats['end_time'] = datetime.now()
            return stats
    
    def _export_json(self, data: List[Dict], filepath: Path):
        """导出为 JSON 格式"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.debug(f"JSON 导出: {filepath}")
    
    def _export_json_gz(self, data: List[Dict], filepath: Path):
        """导出为压缩 JSON 格式 (节省 70% 空间)"""
        with gzip.open(filepath, 'wt', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
        logger.debug(f"JSON.GZ 导出: {filepath}")
    
    def _export_parquet(self, data: List[Dict], filepath: Path):
        """导出为 Parquet 格式 (高压缩比, 快速查询)"""
        if not HAS_PANDAS:
            logger.error("Parquet 格式需要 pandas。使用 JSON.GZ 替代")
            filepath = filepath.with_suffix('.json.gz')
            self._export_json_gz(data, filepath)
            return
        
        df = pd.DataFrame(data)
        df.to_parquet(filepath, compression='gzip', index=False)
        logger.debug(f"Parquet 导出: {filepath}")
    
    def _cleanup_old_archives(self):
        """清理过期归档文件"""
        if not self.archive_config.get('enabled', True):
            return
        
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        
        deleted_count = 0
        deleted_size = 0
        
        # 查找所有导出文件
        patterns = ['data_*.json', 'data_*.json.gz', 'data_*.parquet']
        for pattern in patterns:
            for file in self.export_dir.glob(pattern):
                try:
                    # 从文件名提取日期: data_20241020_120000.json
                    parts = file.stem.split('_')
                    if len(parts) < 2:
                        continue
                    
                    date_str = parts[1]  # 20241020
                    file_date = datetime.strptime(date_str, '%Y%m%d')
                    
                    if file_date < cutoff_date:
                        file_size = file.stat().st_size
                        file.unlink()
                        deleted_count += 1
                        deleted_size += file_size
                        logger.debug(f"删除过期归档: {file.name}")
                except Exception as e:
                    logger.warning(f"处理文件 {file.name} 失败: {e}")
                    continue
        
        if deleted_count > 0:
            size_mb = deleted_size / 1024 / 1024
            logger.info(f"清理完成: 删除 {deleted_count} 个过期归档，释放 {size_mb:.2f}MB 空间")
    
    def get_export_stats(self) -> Dict[str, Any]:
        """获取导出统计信息"""
        stats = {
            'total_files': 0,
            'total_size_mb': 0,
            'oldest_file': None,
            'newest_file': None,
            'files_by_format': {}
        }
        
        # 统计所有导出文件
        all_files = []
        for pattern in ['data_*.json', 'data_*.json.gz', 'data_*.parquet']:
            all_files.extend(self.export_dir.glob(pattern))
        
        if not all_files:
            return stats
        
        stats['total_files'] = len(all_files)
        
        # 计算总大小和时间范围
        for file in all_files:
            size = file.stat().st_size
            stats['total_size_mb'] += size
            
            # 按格式分类
            ext = ''.join(file.suffixes)  # .json.gz 或 .parquet
            stats['files_by_format'][ext] = stats['files_by_format'].get(ext, 0) + 1
            
            # 找最新和最旧
            mtime = datetime.fromtimestamp(file.stat().st_mtime)
            if stats['oldest_file'] is None or mtime < stats['oldest_file']:
                stats['oldest_file'] = mtime
            if stats['newest_file'] is None or mtime > stats['newest_file']:
                stats['newest_file'] = mtime
        
        stats['total_size_mb'] = round(stats['total_size_mb'] / 1024 / 1024, 2)
        
        return stats


def main():
    """测试导出器"""
    from utils.redis_client import RedisClient
    import yaml
    
    # 加载配置
    with open('config.example.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 初始化 Redis 客户端
    redis_config = config.get('redis', {})
    redis_client = RedisClient(
        host=redis_config.get('host', 'localhost'),
        port=redis_config.get('port', 6379),
        db=redis_config.get('db', 0),
        queue_name=redis_config.get('queue_name', 'data_queue')
    )
    
    # 初始化导出器
    data_config = config.get('data_management', {})
    exporter = SmartExporter(redis_client, data_config)
    
    # 检查是否需要导出
    should, reason = exporter.should_export()
    print(f"\n是否需要导出: {should}")
    print(f"原因: {reason}\n")
    
    if should:
        # 执行导出
        stats = exporter.export()
        print("\n导出结果:")
        print(f"  导出数量: {stats['exported']}")
        print(f"  导出文件: {stats['export_file']}")
        print(f"  文件大小: {stats['file_size_mb']}MB")
        if stats['error']:
            print(f"  错误: {stats['error']}")
    
    # 显示统计
    print("\n导出统计:")
    export_stats = exporter.get_export_stats()
    print(f"  总文件数: {export_stats['total_files']}")
    print(f"  总大小: {export_stats['total_size_mb']}MB")
    print(f"  最旧文件: {export_stats['oldest_file']}")
    print(f"  最新文件: {export_stats['newest_file']}")
    print(f"  格式分布: {export_stats['files_by_format']}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    main()
