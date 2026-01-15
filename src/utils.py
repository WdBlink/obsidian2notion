"""
Utility functions for the project.

包含日志设置和其他通用工具函数。
Author: wdblink
"""

import logging
import sys
from .config import get_config

def setup_logger(name: str) -> logging.Logger:
    """
    设置并获取 logger 实例。
    
    Args:
        name: Logger 名称，通常使用 __name__.
        
    Returns:
        配置好的 logging.Logger 实例.
    """
    try:
        config = get_config()
        log_level = config.LOG_LEVEL
    except ValueError:
        log_level = "INFO"

    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(log_level)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
