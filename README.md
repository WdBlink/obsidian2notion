# Obsidian to Notion Sync

这是一个自动将本地 Obsidian 笔记同步到 Notion 数据库的 Python 工具。
核心功能是定期读取本地指定路径下的 Markdown 文件，通过 Notion API 写入 Notion。

## 功能特性

- **定期同步**: 可配置同步间隔时间。
- **智能更新**: 仅同步修改过的文件（基于 MD5 哈希校验）。
- **Markdown 支持**:
  - 标题 (H1-H3)
  - 列表 (无序、有序、Todo)
  - 引用
  - 代码块
  - 图片 (支持网络图片链接)
  - Frontmatter 元数据 (Tags, Date)
- **双向链接转换**: 将 Obsidian 的 `[[WikiLink]]` 转换为文本。

## 环境要求

- Python 3.8+
- Notion Integration Token
- Notion Database ID

## 安装与配置

1. **克隆项目**

```bash
git clone <repository_url>
cd obsidian2notion
```

2. **安装依赖**

```bash
pip install -r requirements.txt
```

3. **配置环境变量**

复制 `.env.example` 为 `.env` 并填入你的配置信息：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

- `NOTION_TOKEN`: 你的 Notion Integration Token ([获取地址](https://www.notion.so/my-integrations))
- `NOTION_DATABASE_ID`: 你的 Notion 数据库 ID (从数据库 URL 中获取)
- `OBSIDIAN_VAULT_PATH`: 你的 Obsidian 仓库本地绝对路径
- `SYNC_INTERVAL_MINUTES`: 同步间隔分钟数 (默认 60)

## Notion 数据库模板

为了确保同步成功，请在 Notion 中创建一个数据库，并包含以下属性：
- **Name** (Title): 笔记标题
- **Tags** (Multi-select): 标签
- **Date** (Date): 日期

## 运行

**启动定时同步任务**:

```bash
python -m src.main
```

**运行一次并退出**:

```bash
python -m src.main --once
```

## 注意事项

- **图片同步**: 目前仅支持标准 Markdown 网络图片链接 `![alt](http://...)`。本地图片暂时无法直接上传到 Notion（API 限制），建议配合图床使用。
- **链接**: Obsidian 的内部链接 `[[Link]]` 会被转换为纯文本，因为无法预知目标页面在 Notion 中的 ID。

## 开发

**运行测试**:

```bash
python -m unittest discover tests
```

Author: wdblink
