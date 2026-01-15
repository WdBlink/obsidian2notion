"""
Notion API Adapter module.

此模块封装了 Notion API 的调用，提供页面创建、更新和查询功能。
Author: wdblink
"""

from typing import List, Dict, Any, Optional
from notion_client import Client
from notion_client.errors import APIResponseError
from .utils import setup_logger

logger = setup_logger(__name__)

class NotionAdapter:
    """
    Notion API 适配器类。
    
    Attributes:
        client (Client): Notion 官方客户端实例。
    """

    def __init__(self, token: str):
        """
        初始化 Notion 适配器。
        
        Args:
            token: Notion Integration Token.
        """
        self.client = Client(auth=token)

    def query_database(self, database_id: str, filter_params: Optional[Dict] = None) -> List[Dict]:
        """
        查询 Notion 数据库。
        
        Args:
            database_id: 数据库 ID。
            filter_params: 查询过滤条件。
            
        Returns:
            页面对象列表。
        """
        results = []
        has_more = True
        start_cursor = None

        try:
            while has_more:
                response = self.client.databases.query(
                    database_id=database_id,
                    filter=filter_params,
                    start_cursor=start_cursor
                )
                results.extend(response.get("results", []))
                has_more = response.get("has_more", False)
                start_cursor = response.get("next_cursor")
            return results
        except APIResponseError as e:
            logger.error(f"Failed to query database: {e}")
            raise

    def create_page(self, database_id: str, properties: Dict, children: List[Dict]) -> Optional[Dict]:
        """
        在指定数据库中创建新页面。
        
        Args:
            database_id: 目标数据库 ID。
            properties: 页面属性。
            children: 页面内容块（Blocks）。
            
        Returns:
            创建的页面对象，失败则返回 None。
        """
        try:
            response = self.client.pages.create(
                parent={"database_id": database_id},
                properties=properties,
                children=children
            )
            logger.info(f"Created page: {response.get('id')}")
            return response
        except APIResponseError as e:
            logger.error(f"Failed to create page: {e}")
            # 这里的 children 可能因为格式错误导致失败，可以考虑只创建页面不带内容，再排查
            return None

    def update_page(self, page_id: str, properties: Optional[Dict] = None, children: Optional[List[Dict]] = None) -> bool:
        """
        更新页面属性和内容。
        
        如果提供了 children，会先清空原有内容再追加新内容（全量替换策略）。
        
        Args:
            page_id: 页面 ID。
            properties: 要更新的属性。
            children: 新的内容块。
            
        Returns:
            是否更新成功。
        """
        try:
            # 1. 更新属性
            if properties:
                self.client.pages.update(page_id=page_id, properties=properties)
                logger.info(f"Updated properties for page: {page_id}")

            # 2. 更新内容（如果提供）
            if children is not None:
                self._replace_page_content(page_id, children)
            
            return True
        except APIResponseError as e:
            logger.error(f"Failed to update page {page_id}: {e}")
            return False

    def _replace_page_content(self, page_id: str, new_blocks: List[Dict]):
        """
        替换页面内容：清空现有块，添加新块。
        
        Args:
            page_id: 页面 ID。
            new_blocks: 新的内容块列表。
        """
        # 1. 获取现有块并删除
        # 注意：Notion API 不支持直接“清空”，需要遍历删除
        # 为了避免过多请求，如果页面很长可能会很慢
        try:
            has_more = True
            start_cursor = None
            
            while has_more:
                response = self.client.blocks.children.list(block_id=page_id, start_cursor=start_cursor)
                blocks = response.get("results", [])
                
                for block in blocks:
                    self.client.blocks.delete(block_id=block["id"])
                
                has_more = response.get("has_more", False)
                start_cursor = response.get("next_cursor")
            
            logger.info(f"Cleared content for page: {page_id}")

            # 2. 添加新块
            # Notion API 限制每次 append 最多 100 个 block
            batch_size = 100
            for i in range(0, len(new_blocks), batch_size):
                batch = new_blocks[i:i + batch_size]
                self.client.blocks.children.append(block_id=page_id, children=batch)
            
            logger.info(f"Appended new content to page: {page_id}")
            
        except APIResponseError as e:
            logger.error(f"Failed to replace page content for {page_id}: {e}")
            raise

    def find_page_by_title(self, database_id: str, title: str) -> Optional[Dict]:
        """
        根据标题查找页面（假设标题是唯一标识符，或者只取第一个）。
        
        Args:
            database_id: 数据库 ID。
            title: 页面标题。
            
        Returns:
            找到的页面对象，如果未找到则返回 None。
        """
        filter_params = {
            "property": "Name",  # 假设标题属性名为 "Name"
            "title": {
                "equals": title
            }
        }
        results = self.query_database(database_id, filter_params)
        if results:
            return results[0]
        return None
