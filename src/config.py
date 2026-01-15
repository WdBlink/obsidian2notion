"""
Configuration module for the Obsidian to Notion sync service.

此模块负责加载和验证应用程序配置。
Author: wdblink
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

class Config:
    """
    应用程序配置类。
    
    Attributes:
        NOTION_TOKEN (str): Notion Integration Token.
        NOTION_DATABASE_ID (str): Notion Database ID.
        OBSIDIAN_VAULT_PATH (Path): 本地 Obsidian 仓库路径.
        SYNC_INTERVAL_MINUTES (int): 同步间隔时间（分钟）.
        LOG_LEVEL (str): 日志级别.
    """

    def __init__(self):
        """初始化配置并验证必要环境变量。"""
        self.NOTION_TOKEN: str = self._get_env("NOTION_TOKEN")
        self.NOTION_DATABASE_ID: str = self._get_env("NOTION_DATABASE_ID")
        
        vault_path = self._get_env("OBSIDIAN_VAULT_PATH")
        self.OBSIDIAN_VAULT_PATH: Path = Path(vault_path)
        
        self.SYNC_INTERVAL_MINUTES: int = int(os.getenv("SYNC_INTERVAL_MINUTES", "60"))
        self.LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
        
        self._validate()

    def _get_env(self, key: str) -> str:
        """
        获取环境变量，如果不存在则抛出异常。
        
        Args:
            key: 环境变量名称.
            
        Returns:
            环境变量的值.
            
        Raises:
            ValueError: 如果环境变量未设置.
        """
        value = os.getenv(key)
        if not value:
            raise ValueError(f"Missing required environment variable: {key}")
        return value

    def _validate(self):
        """
        验证配置的有效性。
        
        Raises:
            ValueError: 如果路径不存在或无效.
        """
        if not self.OBSIDIAN_VAULT_PATH.exists():
             # 在测试或首次运行时，路径可能暂时不存在，可以只打印警告或者抛出异常
             # 为了健壮性，这里先抛出异常，确保用户配置正确
             raise ValueError(f"Obsidian vault path does not exist: {self.OBSIDIAN_VAULT_PATH}")

# 全局配置实例
try:
    # 只有在环境变量存在时才能安全初始化，否则可能在导入时报错
    # 这里我们允许延迟初始化，或者假设用户已经配好了环境
    # 为了方便测试，如果环境变量缺失，可能需要在 main 中处理异常
    config = Config()
except ValueError:
    config = None  # type: ignore

def get_config() -> Config:
    """
    获取配置单例。如果初始化失败（例如缺少环境变量），则再次尝试初始化以抛出详细错误。
    
    Returns:
        Config: 配置对象.
    """
    global config
    if config is None:
        config = Config()
    return config
