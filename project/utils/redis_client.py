"""
Redis 客户端模块
提供 Redis 连接和数据存储功能，支持：
- 精简模式（节省内存）
- 队列长度预警
- 按数据来源配额（软限制）与来源计数
"""
import json
import redis
from typing import Dict, Any, Optional, Tuple
from utils.logger import setup_logger

logger = setup_logger('redis_client')


class RedisClient:
    """Redis 客户端类"""

    def __init__(
        self,
        host: str = 'localhost',
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        queue_name: str = 'data_queue',
        storage_config: Optional[Dict[str, Any]] = None,
        source_quotas: Optional[Dict[str, float]] = None,
        **kwargs,
    ):
        """
        初始化 Redis 客户端

        Args:
            host: Redis 主机地址
            port: Redis 端口
            db: Redis 数据库编号
            password: Redis 密码
            queue_name: 队列名称
            storage_config: 存储优化配置字典（来自 redis.storage_optimization）
            source_quotas: 来源配额（来自 redis.source_quotas），0-1 之间
        """
        self.queue_name = queue_name

        # 存储优化配置
        # 兼容传入的完整 redis 配置（storage_optimization 可能通过 **kwargs 传入）
        storage_config = storage_config or kwargs.get('storage_optimization') or {}
        self.storage_config = storage_config
        self.slim_mode = self.storage_config.get('slim_mode', False)
        self.data_ttl = self.storage_config.get('data_ttl', None)
        self.max_keep = int(self.storage_config.get('max_keep', 10000))

        # 来源配额（软限制）
        self.source_quotas = source_quotas or kwargs.get('source_quotas') or {}
        # 以 Redis Key 记录每个来源的计数，避免全量扫描
        self.source_count_prefix = f"{self.queue_name}:source_count:"

        try:
            self.client = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            # 测试连接
            self.client.ping()
            logger.info(f"Redis 连接成功: {host}:{port}/{db}")
            if self.slim_mode:
                logger.info("✓ 精简模式已启用 (节省60%空间)")
            if self.data_ttl:
                logger.info(f"✓ 数据TTL: {self.data_ttl}秒")
            logger.info(f"✓ 最大保留: {self.max_keep}条")
            if self.source_quotas:
                logger.info(f"✓ 来源配额启用: {self.source_quotas}")
        except redis.ConnectionError as e:
            logger.error(f"Redis 连接失败: {e}")
            raise
    
    def push_data(self, data: Dict[str, Any]) -> bool:
        """
        将数据推送到 Redis 队列（支持精简模式）
        
        Args:
            data: 要推送的数据字典
        
        Returns:
            bool: 是否推送成功
        """
        try:
            # 🔥 精简模式：只保留核心字段
            if self.slim_mode:
                data = self._slim_data(data)
            
            # 序列化为 JSON
            json_data = json.dumps(data, ensure_ascii=False)
            
            # 推送到列表
            # 先检查来源配额（软限制：超额则跳过本条）
            source = data.get('source') or 'unknown'
            if self._exceeds_quota(source):
                logger.warning(f"⚠️  来源 {source} 已超过配额，丢弃新数据以保护总量（soft limit）")
                return False

            self.client.lpush(self.queue_name, json_data)
            # 更新来源计数
            try:
                self.client.incr(self._source_count_key(source))
            except Exception:
                # 计数失败不影响主流程
                pass
            
            # 🔥 检查队列长度，超过阈值警告
            queue_length = self.client.llen(self.queue_name)
            if queue_length > self.max_keep:
                logger.warning(f"⚠️  队列长度 {queue_length} 超过阈值 {self.max_keep}，建议导出")
            
            logger.debug(f"数据已推送到 Redis: source={data.get('source')}")
            return True
        except Exception as e:
            logger.error(f"推送数据到 Redis 失败: {e}")
            return False
    
    def _slim_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        精简数据字段（只保留核心字段，节省60%空间）
        
        核心字段:
        - title: 标题
        - url: 链接
        - published: 发布时间
        - source: 数据源
        - feed_category: 分类（RSS专用）
        - language: 语言
        - summary: 摘要
        
        Args:
            data: 原始数据
        
        Returns:
            精简后的数据
        """
        slim_fields = [
            'title',
            'url',
            'published',
            'source',
            'feed_category',
            'language',
            'summary',
            'timestamp'  # 爬取时间戳
        ]
        
        slimmed = {k: v for k, v in data.items() if k in slim_fields}
        
        # 确保必要字段存在
        if 'timestamp' not in slimmed and 'crawl_timestamp' in data:
            slimmed['timestamp'] = data['crawl_timestamp']
        
        if 'summary' not in slimmed and 'text' in data:
            slimmed['summary'] = data['text'][:500]  # 只保留前500字符
        
        return slimmed
    
    def push_batch(self, data_list: list) -> int:
        """
        批量推送数据到 Redis
        
        Args:
            data_list: 数据字典列表
        
        Returns:
            int: 成功推送的数据条数
        """
        success_count = 0
        try:
            # 逐条校验来源配额，必要时可优化为分组批处理
            pipe = self.client.pipeline()
            to_incr = {}
            for data in data_list:
                if self.slim_mode:
                    data = self._slim_data(data)
                source = (data or {}).get('source') or 'unknown'
                if self._exceeds_quota(source):
                    continue
                json_data = json.dumps(data, ensure_ascii=False)
                pipe.lpush(self.queue_name, json_data)
                to_incr[source] = to_incr.get(source, 0) + 1
                success_count += 1
            if success_count:
                pipe.execute()
                # 批量增加来源计数
                for s, c in to_incr.items():
                    try:
                        self.client.incrby(self._source_count_key(s), c)
                    except Exception:
                        pass
                logger.info(f"批量推送 {success_count} 条数据到 Redis")
        except Exception as e:
            logger.error(f"批量推送数据失败: {e}")

        return success_count
    
    def get_queue_length(self) -> int:
        """
        获取队列长度
        
        Returns:
            int: 队列中的数据条数
        """
        try:
            length = self.client.llen(self.queue_name)
            return length
        except Exception as e:
            logger.error(f"获取队列长度失败: {e}")
            return -1
    
    def peek_data(self, count=10) -> list:
        """
        查看队列中的数据（不移除）
        
        Args:
            count: 查看的数据条数
        
        Returns:
            list: 数据列表
        """
        try:
            data_list = self.client.lrange(self.queue_name, 0, count - 1)
            return [json.loads(item) for item in data_list]
        except Exception as e:
            logger.error(f"查看队列数据失败: {e}")
            return []

    # ============== 配额与计数 ==============
    def _source_count_key(self, source: str) -> str:
        return f"{self.source_count_prefix}{source}"

    def _quota_limit(self, source: str) -> Optional[int]:
        """返回某来源的配额上限条数（基于 max_keep 与百分比），无则返回 None。"""
        if not self.source_quotas:
            return None
        q = self.source_quotas.get(source)
        if q is None:
            return None
        try:
            return int(self.max_keep * float(q))
        except Exception:
            return None

    def _exceeds_quota(self, source: str) -> bool:
        limit = self._quota_limit(source)
        if not limit:
            return False
        try:
            # 读取当前来源计数
            cnt = int(self.client.get(self._source_count_key(source)) or 0)
            return cnt >= limit
        except Exception:
            return False

    def rebuild_source_counts(self, max_scan: Optional[int] = None) -> Tuple[int, Dict[str, int]]:
        """
        全量（或部分）扫描队列，重建来源计数键。
        注意：O(n) 操作，请在导出修剪后调用。

        Args:
            max_scan: 最多扫描的条数（从队列头部开始），默认全量

        Returns:
            (scanned, counts) 元组
        """
        try:
            # 清理现有计数
            # 简化处理：不删除旧 key，直接覆盖 set 值
            length = self.client.llen(self.queue_name)
            scan_n = length if max_scan is None else min(length, max_scan)
            if scan_n <= 0:
                return 0, {}
            # 从头部读取最新的 scan_n 条
            data_list = self.client.lrange(self.queue_name, 0, scan_n - 1)
            counts: Dict[str, int] = {}
            for item in data_list:
                try:
                    d = json.loads(item)
                    s = (d or {}).get('source') or 'unknown'
                    counts[s] = counts.get(s, 0) + 1
                except Exception:
                    continue
            # 回写计数
            pipe = self.client.pipeline()
            for s, c in counts.items():
                pipe.set(self._source_count_key(s), c)
            pipe.execute()
            logger.info(f"来源计数重建完成：扫描 {scan_n} 条，来源数 {len(counts)}")
            return scan_n, counts
        except Exception as e:
            logger.error(f"重建来源计数失败: {e}")
            return 0, {}
    
    def close(self):
        """关闭 Redis 连接"""
        try:
            self.client.close()
            logger.info("Redis 连接已关闭")
        except Exception as e:
            logger.error(f"关闭 Redis 连接失败: {e}")
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """
        获取 Redis 内存使用情况
        
        Returns:
            dict: 内存使用信息
            {
                'used_memory_mb': 123.45,        # 已使用内存(MB)
                'used_memory_human': '123.45M',  # 人类可读格式
                'used_memory_peak_mb': 200.00,   # 峰值内存(MB)
                'used_memory_peak_human': '200M' # 峰值人类可读格式
            }
        """
        try:
            info = self.client.info('memory')
            return {
                'used_memory_mb': info['used_memory'] / 1024 / 1024,
                'used_memory_human': info['used_memory_human'],
                'used_memory_peak_mb': info['used_memory_peak'] / 1024 / 1024,
                'used_memory_peak_human': info['used_memory_peak_human']
            }
        except Exception as e:
            logger.error(f"获取 Redis 内存信息失败: {e}")
            return {
                'used_memory_mb': 0,
                'used_memory_human': 'N/A',
                'used_memory_peak_mb': 0,
                'used_memory_peak_human': 'N/A'
            }

