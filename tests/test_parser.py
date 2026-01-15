"""
Tests for Markdown Parser.

Author: wdblink
"""

import unittest
from pathlib import Path
from src.markdown_parser import MarkdownParser

class TestMarkdownParser(unittest.TestCase):
    def setUp(self):
        self.parser = MarkdownParser()

    def test_extract_frontmatter(self):
        content = """---
tags: [note, test]
date: 2023-01-01
---
# Title
Content"""
        frontmatter, body = self.parser._extract_frontmatter(content)
        self.assertEqual(frontmatter['tags'], ['note', 'test'])
        self.assertEqual(str(frontmatter['date']), '2023-01-01')
        self.assertEqual(body.strip(), "# Title\nContent")

    def test_parse_simple_blocks(self):
        body = """# Heading 1
- List Item 1
- List Item 2
> Quote
"""
        blocks = self.parser._parse_body_to_blocks(body)
        
        self.assertEqual(blocks[0]['type'], 'heading_1')
        self.assertEqual(blocks[0]['heading_1']['rich_text'][0]['text']['content'], 'Heading 1')
        
        self.assertEqual(blocks[1]['type'], 'bulleted_list_item')
        
        self.assertEqual(blocks[3]['type'], 'quote')

    def test_wikilink_replacement(self):
        text = "This is a [[Link]] and [[Link|Alias]]."
        rich_text = self.parser._create_rich_text(text)
        content = rich_text[0]['text']['content']
        self.assertEqual(content, "This is a Link and Alias.")

    def test_obsidian_image_replacement(self):
        text = "Image ![[image.png]] here."
        rich_text = self.parser._create_rich_text(text)
        content = rich_text[0]['text']['content']
        self.assertEqual(content, "Image [Image: image.png] here.")

    def test_external_image_block(self):
        line = "![alt](https://example.com/image.png)"
        block = self.parser._create_image_block(line)
        self.assertIsNotNone(block)
        self.assertEqual(block['type'], 'image')
        self.assertEqual(block['image']['external']['url'], 'https://example.com/image.png')

if __name__ == '__main__':
    unittest.main()
