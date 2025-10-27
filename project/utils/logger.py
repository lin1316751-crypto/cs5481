"""
日志工具模块
提供统一的日志记录功能（支持文件轮转与配置文件设置）
"""
import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler


def _load_logging_config():
    """从 config.yaml 读取日志配置（若存在）。"""
    try:
        import yaml
        with open('config.yaml', 'r', encoding='utf-8') as f:
            cfg = yaml.safe_load(f) or {}
        logging_cfg = (cfg.get('logging') or {})
        return {
            'level': getattr(logging, str(logging_cfg.get('level', 'INFO')).upper(), logging.INFO),
            'log_dir': logging_cfg.get('log_dir', 'logs'),
            'max_log_size_mb': int(logging_cfg.get('max_log_size_mb', 10)),
            'backup_count': int(logging_cfg.get('backup_count', 5)),
        }
    except Exception:
        # 回退默认
        return {
            'level': logging.INFO,
            'log_dir': 'logs',
            'max_log_size_mb': 10,
            'backup_count': 5,
        }


def setup_logger(name, log_dir=None, level=None):
    """
    设置日志记录器
    
    Args:
        name: 日志记录器名称
        log_dir: 日志目录（可选，默认从 config.yaml 读取或使用 logs）
        level: 日志级别（可选，默认从 config.yaml 读取或 INFO）
    
    Returns:
        logger: 配置好的日志记录器
    """
    cfg = _load_logging_config()
    log_dir = log_dir or cfg['log_dir']
    level = level if isinstance(level, int) else cfg['level']

    # 确保日志目录存在
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 创建日志记录器
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 避免重复添加处理器
    if logger.handlers:
        return logger
    
    # 创建文件轮转处理器（单文件大小与备份数量从配置读取）
    log_filename = f"{name}_{datetime.now().strftime('%Y%m%d')}.log"
    log_filepath = os.path.join(log_dir, log_filename)
    file_handler = RotatingFileHandler(
        log_filepath,
        maxBytes=cfg['max_log_size_mb'] * 1024 * 1024,
        backupCount=cfg['backup_count'],
        encoding='utf-8'
    )
    file_handler.setLevel(level)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    
    # 创建格式器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # 添加处理器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger
