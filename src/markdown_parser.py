"""
Markdown Parser module.

此模块负责解析 Obsidian Markdown 文件，提取 Frontmatter 元数据，
并将 Markdown 内容转换为 Notion API 支持的 Block 格式。
Author: wdblink
"""

import re
import yaml
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime
from .utils import setup_logger

logger = setup_logger(__name__)

class MarkdownParser:
    """
    Markdown 解析器类。
    """

    def __init__(self):
        # 匹配 Frontmatter
        self.frontmatter_pattern = re.compile(r'^---\s*\n(.*?)\n---\s*\n', re.DOTALL)
        # 匹配图片 ![[image.png]] 或 ![alt](url)
        self.obsidian_image_pattern = re.compile(r'!\[\[(.*?)\]\]')
        self.md_image_pattern = re.compile(r'!\[(.*?)\]\((.*?)\)')
        # 匹配 WikiLink [[Page Name]] 或 [[Page Name|Alias]]
        self.wikilink_pattern = re.compile(r'\[\[(.*?)(?:\|(.*?))?\]\]')
        # 匹配标签 #tag
        self.tag_pattern = re.compile(r'(?<=[\s^])#([\w\-/]+)')

    def parse_file(self, file_path: Path) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        解析 Markdown 文件。
        
        Args:
            file_path: 文件路径。
            
        Returns:
            (properties, blocks) 元组。
            properties: 提取的 Notion 页面属性（如 Tags, Name）。
            blocks: Notion 内容块列表。
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            return {}, []

        # 1. 提取 Frontmatter 和 Body
        frontmatter, body = self._extract_frontmatter(content)
        
        # 2. 生成 Properties
        # 默认使用文件名作为标题
        title = file_path.stem
        properties = self._build_properties(title, frontmatter, file_path)
        
        # 3. 解析 Body 为 Blocks
        blocks = self._parse_body_to_blocks(body)
        
        return properties, blocks

    def _extract_frontmatter(self, content: str) -> Tuple[Dict, str]:
        """提取 YAML Frontmatter。"""
        match = self.frontmatter_pattern.match(content)
        if match:
            yaml_content = match.group(1)
            try:
                frontmatter = yaml.safe_load(yaml_content)
                # 如果 yaml_content 为空或解析失败，yaml.safe_load 可能返回 None
                if frontmatter is None:
                    frontmatter = {}
                return frontmatter, content[match.end():]
            except yaml.YAMLError as e:
                logger.warning(f"Failed to parse YAML frontmatter: {e}")
                return {}, content
        return {}, content

    def _build_properties(self, title: str, frontmatter: Dict, file_path: Path) -> Dict[str, Any]:
        """
        构建 Notion Properties。
        
        映射规则:
        - title -> Name (Title)
        - tags -> Tags (Multi-select)
        - date/created -> Date (Date)
        """
        properties = {
            "Name": {
                "title": [{"text": {"content": title}}]
            }
        }

        # 处理 Tags
        tags = frontmatter.get('tags') or frontmatter.get('tag')
        if tags:
            if isinstance(tags, str):
                # 兼容空格或逗号分隔的标签字符串
                if ',' in tags:
                    tags = [t.strip() for t in tags.split(',')]
                else:
                    tags = tags.split()
            
            if isinstance(tags, list):
                properties["Tags"] = {
                    "multi_select": [{"name": str(t)} for t in tags]
                }

        # 处理 Date (优先使用 date, 其次 created, 最后用文件修改时间)
        date_val = frontmatter.get('date') or frontmatter.get('created')
        if not date_val:
             # 使用文件修改时间
             mtime = file_path.stat().st_mtime
             date_val = datetime.fromtimestamp(mtime).isoformat()
        
        if date_val:
            # 确保是 ISO 格式字符串
            if isinstance(date_val, (datetime,  object)): # date object
                date_val = str(date_val)
            properties["Date"] = {
                "date": {"start": date_val}
            }

        return properties

    def _parse_body_to_blocks(self, body: str) -> List[Dict[str, Any]]:
        """
        将 Markdown 正文转换为 Notion Blocks。
        这是一个简化的按行解析器。
        """
        blocks = []
        lines = body.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i]
            # 跳过空行，但如果需要在 Notion 里面保留空行，可以加一个空的 paragraph
            # 为了美观，Notion block 之间自带间距，通常不需要空 block，除非是显式的空行意图
            if not line.strip():
                # 可以在这里决定是否添加空段落
                # blocks.append(self._create_paragraph_block("")) 
                i += 1
                continue
            
            # 识别 Code Block
            if line.strip().startswith('```'):
                code_content = []
                language = line.strip()[3:].strip()
                i += 1
                while i < len(lines) and not lines[i].strip().startswith('```'):
                    code_content.append(lines[i])
                    i += 1
                # 消费掉结束的 ```
                if i < len(lines):
                    i += 1
                blocks.append(self._create_code_block('\n'.join(code_content), language))
                continue

            # 识别 Heading
            if line.startswith('# '):
                blocks.append(self._create_heading_block(line[2:], 1))
            elif line.startswith('## '):
                blocks.append(self._create_heading_block(line[3:], 2))
            elif line.startswith('### '):
                blocks.append(self._create_heading_block(line[4:], 3))
            
            # 识别 List Item
            elif line.strip().startswith('- ') or line.strip().startswith('* '):
                content = line.strip()[2:]
                # 检查是否是 Todo
                if content.startswith('[ ] '):
                    blocks.append(self._create_todo_block(content[4:], False))
                elif content.startswith('[x] '):
                    blocks.append(self._create_todo_block(content[4:], True))
                else:
                    blocks.append(self._create_bulleted_list_item(content))
            
            # 识别 Numbered List
            elif re.match(r'^\d+\.\s', line.strip()):
                content = re.sub(r'^\d+\.\s', '', line.strip())
                blocks.append(self._create_numbered_list_item(content))
            
            # 识别 Quote
            elif line.strip().startswith('> '):
                blocks.append(self._create_quote_block(line.strip()[2:]))
            
            # 识别 Image (行内图片作为独立 Block 处理)
            # 简化处理：如果一行主要是图片，则作为 Image Block，否则作为 Text
            elif self._is_image_line(line):
                image_block = self._create_image_block(line)
                if image_block:
                    blocks.append(image_block)
                else:
                    blocks.append(self._create_paragraph_block(line))
            
            # 默认 Paragraph
            else:
                blocks.append(self._create_paragraph_block(line))
            
            i += 1
            
        return blocks

    def _create_rich_text(self, text: str) -> List[Dict]:
        """
        处理行内样式（Bold, Italic, Link, Code）并返回 Rich Text 对象列表。
        目前为了简化，主要处理纯文本和简单的 WikiLink 替换。
        """
        # 简单处理：将 [[Link]] 替换为 Link 文本，不带跳转（因为不知道目标 ID）
        # 将 Obsidian 图片 ![[img]] 替换为文本说明
        
        # 替换 Obsidian 图片语法为说明文本
        # 注意：必须在 Wikilink 替换之前执行，因为 ![[...]] 包含 [[...]]
        text = self.obsidian_image_pattern.sub(r'[Image: \1]', text)

        # 替换 Wikilinks
        def replace_wikilink(match):
            page = match.group(1)
            alias = match.group(2)
            return alias if alias else page
        
        text = self.wikilink_pattern.sub(replace_wikilink, text)
        
        # TODO: 支持更多 Markdown 行内样式解析 (Bold, Italic, etc.)
        # Notion API 需要把文本切分成多个 text object 才能应用不同的 annotations
        # 这里仅返回纯文本对象
        
        # 如果文本长度超过 2000，Notion API 会报错，需要截断
        if len(text) > 2000:
            text = text[:1997] + "..."
            
        return [{"text": {"content": text}}]

    def _is_image_line(self, line: str) -> bool:
        return bool(self.md_image_pattern.match(line.strip()) or self.obsidian_image_pattern.match(line.strip()))

    def _create_image_block(self, line: str) -> Optional[Dict]:
        """尝试创建图片块。仅支持网络图片 URL。"""
        # 标准 Markdown 图片 ![alt](url)
        match = self.md_image_pattern.search(line)
        if match:
            url = match.group(2)
            if url.startswith('http'):
                return {
                    "object": "block",
                    "type": "image",
                    "image": {
                        "type": "external",
                        "external": {"url": url}
                    }
                }
        # 如果是本地图片或 Obsidian 内部图片，暂时不支持上传，返回 None 降级为文本
        return None

    def _create_paragraph_block(self, text: str) -> Dict:
        return {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": self._create_rich_text(text)
            }
        }

    def _create_heading_block(self, text: str, level: int) -> Dict:
        block_type = f"heading_{level}"
        return {
            "object": "block",
            "type": block_type,
            block_type: {
                "rich_text": self._create_rich_text(text)
            }
        }

    def _create_bulleted_list_item(self, text: str) -> Dict:
        return {
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": self._create_rich_text(text)
            }
        }

    def _create_numbered_list_item(self, text: str) -> Dict:
        return {
            "object": "block",
            "type": "numbered_list_item",
            "numbered_list_item": {
                "rich_text": self._create_rich_text(text)
            }
        }

    def _create_todo_block(self, text: str, checked: bool) -> Dict:
        return {
            "object": "block",
            "type": "to_do",
            "to_do": {
                "rich_text": self._create_rich_text(text),
                "checked": checked
            }
        }

    def _create_quote_block(self, text: str) -> Dict:
        return {
            "object": "block",
            "type": "quote",
            "quote": {
                "rich_text": self._create_rich_text(text)
            }
        }

    def _create_code_block(self, code: str, language: str) -> Dict:
        # Notion 支持的语言有限，需要做映射，这里简单处理
        if not language:
            language = "plain text"
        
        # 截断过长的代码
        if len(code) > 2000:
             code = code[:1997] + "..."

        return {
            "object": "block",
            "type": "code",
            "code": {
                "rich_text": [{"text": {"content": code}}],
                "language": language.split()[0] if language else "plain text" # 取第一个词，防止 extra info
            }
        }
