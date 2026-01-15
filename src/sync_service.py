"""
Sync Service module.

此模块负责协调文件遍历、解析和 Notion 同步的核心逻辑。
Author: wdblink
"""

import os
import json
import hashlib
from pathlib import Path
from typing import Dict, Optional
from .config import get_config
from .notion_adapter import NotionAdapter
from .markdown_parser import MarkdownParser
from .utils import setup_logger

logger = setup_logger(__name__)

class SyncService:
    """
    同步服务类。
    
    Attributes:
        config: 应用配置。
        notion: Notion 适配器。
        parser: Markdown 解析器。
        state_file: 同步状态文件路径。
        state: 当前同步状态。
    """

    def __init__(self):
        self.config = get_config()
        self.notion = NotionAdapter(self.config.NOTION_TOKEN)
        self.parser = MarkdownParser()
        self.state_file = Path("sync_state.json")
        self.state = self._load_state()

    def _load_state(self) -> Dict:
        """加载同步状态文件。"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load state file: {e}")
                return {}
        return {}

    def _save_state(self):
        """保存同步状态文件。"""
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save state file: {e}")

    def _calculate_file_hash(self, file_path: Path) -> str:
        """计算文件内容的 MD5 哈希值。"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return ""

    def sync(self):
        """执行一次完整的同步流程。"""
        logger.info("Starting sync process...")
        
        vault_path = self.config.OBSIDIAN_VAULT_PATH
        if not vault_path.exists():
            logger.error(f"Vault path does not exist: {vault_path}")
            return

        # 遍历所有 Markdown 文件
        for file_path in vault_path.rglob("*.md"):
            self._sync_file(file_path, vault_path)
        
        self._save_state()
        logger.info("Sync process completed.")

    def _sync_file(self, file_path: Path, root_path: Path):
        """同步单个文件。"""
        try:
            relative_path = str(file_path.relative_to(root_path))
            current_mtime = file_path.stat().st_mtime
            current_hash = self._calculate_file_hash(file_path)

            # 检查是否需要更新
            file_state = self.state.get(relative_path, {})
            last_hash = file_state.get("hash")
            
            # 如果哈希值未变，则跳过
            if last_hash == current_hash:
                logger.debug(f"Skipping unchanged file: {relative_path}")
                return

            logger.info(f"Syncing file: {relative_path}")
            
            # 解析文件
            properties, blocks = self.parser.parse_file(file_path)
            if not properties:
                logger.warning(f"Failed to parse properties for {relative_path}")
                return

            # 获取已知的 page_id
            page_id = file_state.get("page_id")
            
            # 如果本地状态没有 page_id，尝试通过标题在 Notion 中查找，防止重复创建
            if not page_id:
                title = properties.get("Name", {}).get("title", [{}])[0].get("text", {}).get("content", "")
                if title:
                    existing_page = self.notion.find_page_by_title(self.config.NOTION_DATABASE_ID, title)
                    if existing_page:
                        page_id = existing_page["id"]
                        logger.info(f"Found existing page for {relative_path}: {page_id}")

            success = False
            if page_id:
                # 更新现有页面
                success = self.notion.update_page(page_id, properties, blocks)
            else:
                # 创建新页面
                result = self.notion.create_page(self.config.NOTION_DATABASE_ID, properties, blocks)
                if result:
                    page_id = result["id"]
                    success = True

            # 更新状态
            if success and page_id:
                self.state[relative_path] = {
                    "mtime": current_mtime,
                    "hash": current_hash,
                    "page_id": page_id
                }
                logger.info(f"Successfully synced: {relative_path}")

        except Exception as e:
            logger.error(f"Error syncing file {file_path}: {e}")
