"""
Tests for Sync Service.

Author: wdblink
"""

import unittest
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch
from src.sync_service import SyncService
from src.config import Config

class TestSyncService(unittest.TestCase):
    def setUp(self):
        # 创建临时目录作为 Obsidian Vault
        self.test_dir = tempfile.mkdtemp()
        self.vault_path = Path(self.test_dir)
        
        # Mock Config
        self.mock_config_patcher = patch('src.sync_service.get_config')
        self.mock_get_config = self.mock_config_patcher.start()
        self.mock_config = MagicMock()
        self.mock_config.OBSIDIAN_VAULT_PATH = self.vault_path
        self.mock_config.NOTION_TOKEN = "fake_token"
        self.mock_config.NOTION_DATABASE_ID = "fake_db_id"
        self.mock_get_config.return_value = self.mock_config

        # Mock NotionAdapter
        self.mock_notion_patcher = patch('src.sync_service.NotionAdapter')
        self.MockNotionAdapter = self.mock_notion_patcher.start()
        self.mock_notion = self.MockNotionAdapter.return_value

    def tearDown(self):
        shutil.rmtree(self.test_dir)
        self.mock_config_patcher.stop()
        self.mock_notion_patcher.stop()
        # 清理生成的 state 文件
        if Path("sync_state.json").exists():
            Path("sync_state.json").unlink()

    def test_sync_new_file(self):
        # 创建测试文件
        file_path = self.vault_path / "test.md"
        with open(file_path, "w") as f:
            f.write("# Hello\nWorld")

        # Mock create_page return value
        self.mock_notion.create_page.return_value = {"id": "new_page_id"}
        self.mock_notion.find_page_by_title.return_value = None

        service = SyncService()
        # 强制使用临时的 state 文件路径，避免影响当前目录（虽然 tearDown 会删，但最好隔离）
        service.state_file = Path(self.test_dir) / "sync_state.json"
        
        service.sync()

        # 验证 create_page 被调用
        self.mock_notion.create_page.assert_called_once()
        args, _ = self.mock_notion.create_page.call_args
        self.assertEqual(args[0], "fake_db_id") # database_id
        self.assertEqual(args[1]["Name"]["title"][0]["text"]["content"], "test") # title from filename

        # 验证状态已更新
        with open(service.state_file, "r") as f:
            state = json.load(f)
        self.assertIn("test.md", state)
        self.assertEqual(state["test.md"]["page_id"], "new_page_id")

    def test_sync_updated_file(self):
        # 1. 先模拟已同步状态
        service = SyncService()
        service.state_file = Path(self.test_dir) / "sync_state.json"
        service.state = {
            "test.md": {
                "mtime": 0,
                "hash": "old_hash",
                "page_id": "existing_page_id"
            }
        }
        service._save_state()

        # 2. 创建文件（内容变化）
        file_path = self.vault_path / "test.md"
        with open(file_path, "w") as f:
            f.write("# Updated\nContent")

        # 3. 执行同步
        service.sync()

        # 验证 update_page 被调用
        self.mock_notion.update_page.assert_called_once()
        args, _ = self.mock_notion.update_page.call_args
        self.assertEqual(args[0], "existing_page_id")
        
        # 验证 create_page 未被调用
        self.mock_notion.create_page.assert_not_called()

    def test_skip_unchanged_file(self):
        file_path = self.vault_path / "test.md"
        with open(file_path, "w") as f:
            f.write("Content")
            
        service = SyncService()
        service.state_file = Path(self.test_dir) / "sync_state.json"
        
        # 手动计算 hash 并写入 state
        current_hash = service._calculate_file_hash(file_path)
        service.state = {
            "test.md": {
                "mtime": file_path.stat().st_mtime,
                "hash": current_hash,
                "page_id": "page_id"
            }
        }
        service._save_state()

        service.sync()

        # 验证没有任何 API 调用
        self.mock_notion.create_page.assert_not_called()
        self.mock_notion.update_page.assert_not_called()

if __name__ == '__main__':
    unittest.main()
