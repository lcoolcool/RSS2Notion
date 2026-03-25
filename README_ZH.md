[English](./README.md) | 简体中文

<div align="center">

# RSS2Notion

**将 RSS 订阅自动同步到 Notion，在 Notion 中打造你的个人阅读空间**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/Python-3.14+-green.svg)](https://www.python.org/)

</div>

---

![Overview](./docs/images/overview.png)

---

## ✨ 功能特性

- **Notion 订阅管理** — 直接在 Notion 中增删改查订阅源，无需修改配置文件
- **全文 / 仅元数据 两种模式** — 每个订阅可独立开启全文保存，关闭时仅保存标题、链接、作者等元信息
- **智能去重** — 基于时间戳过滤 + URL 批量查询双重去重，高效避免重复写入
- **图文混排** — 完整保留文章图片，图文交替写入 Notion 页面
- **标签聚合** — RSS 标签与订阅级自定义标签自动合并
- **封面图提取** — 自动提取文章内图片或频道封面作为页面封面
- **阅读状态追踪** — 文章自动标记为 `Unread`，支持 `Reading` / `Starred` 状态流转
- **订阅源关联** — 通过 Relation 将每篇文章关联回对应的订阅源
- **自动清理** — 定期删除超期未读文章，保持数据库整洁（可配置保留天数）
- **订阅状态反馈** — 同步失败时自动将订阅标记为 `Error`，方便排查
- **GitHub Actions 定时运行** — 每小时自动同步，无需自建服务器

---

## 🚀 快速开始

### 前置条件

- 一个 [Notion](https://www.notion.so/) 账号
- 一个 GitHub 账号

### 步骤 1：复制 Notion 模板

点击下方链接将模板复制到你的 Notion 工作区：

👉 [**点击复制 Notion 模板**](https://aeolian-saga-950.notion.site/RSS-Hub-32c4c2f98bee8000b3e7e7fb4c0d644a)，点击右上角“Duplicate”，在你的 Notion 中创建一个副本。

模板包含两个数据库：
- **订阅数据库** — 管理你的 RSS 订阅源
- **阅读数据库** — 存放同步的文章

> ⚠️ **注意！不要修改 database 的 properties 的名称，否则会无法正常工作**

![Template](./docs/images/template.png)

### 步骤 2：创建 Notion Integration

1. 前往 [Notion Integrations](https://www.notion.so/profile/integrations) 创建一个新的 Integration
2. 选择你的工作区，提交后获取 **Internal Integration Token**（即 `NOTION_API_KEY`）

![Integration](./docs/images/integration.png)

3. 为 Integration 配置内容访问权限：

![Integration Permissions](./docs/images/integration_perm.png)

### 步骤 3：获取数据库 ID

从 Notion 数据库页面的 URL 中提取 ID：

```
https://www.notion.so/your-workspace/xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx?v=...
                                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                     这一段（32位）即为数据库 ID
```

- **文章数据库 ID** → `NOTION_ARTICLES_DATABASE_ID`
- **订阅数据库 ID** → `NOTION_FEEDS_DATABASE_ID`

### 步骤 4：Fork 仓库并配置 Secrets

1. 点击右上角 **Fork** 将本仓库复制到你的 GitHub 账号
2. 进入你 Fork 后的仓库 → **Settings** → **Secrets and variables** → **Actions**
3. 添加以下 **Repository Secrets**：

| Secret 名称 | 说明                       |
|------------|--------------------------|
| `NOTION_API_KEY` | Notion Integration Token |
| `NOTION_ARTICLES_DATABASE_ID` | 文章数据库 ID                 |
| `NOTION_FEEDS_DATABASE_ID` | 订阅数据库 ID                 |

![Secrets](./docs/images/secrets.png)

4. （可选）添加以下 **Repository Variables**（Settings → Secrets and variables → Actions → Variables）：

| Variable 名称 | 默认值 | 说明 |
|--------------|--------|------|
| `TIMEZONE` | `Asia/Shanghai` | 时区，使用 [IANA 格式](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones) |
| `CLEANUP_DAYS` | `30` | 保留天数（双重作用）：① 首次运行时只导入最近 N 天的文章；② 定期清理超过 N 天的 Unread 文章。设为 `-1` 则首次导入全部历史数据且禁用自动清理 |

### 步骤 5：启用 GitHub Actions 并手动触发

1. 进入仓库的 **Actions** 标签页
2. 如果看到提示，点击 **I understand my workflows, go ahead and enable them**
3. 左侧选择 **RSS Sync** → 点击 **Run workflow** 手动触发第一次同步

![Actions](./docs/images/action.png)

之后每小时整点会自动运行。

> **（可选）更改同步频率**
> 编辑 `.github/workflows/sync.yml` 中的 cron 表达式：
> ```yaml
> - cron: '0 * * * *'  # 每小时整点
> ```
> 例如改为每 30 分钟：`'*/30 * * * *'`，每 6 小时：`'0 */6 * * *'`。
> 可使用 [crontab.guru](https://crontab.guru/) 生成表达式。

---

## ⚙️ 配置说明

| 环境变量 | 必填 | 默认值 | 说明 |
|---------|:----:|--------|------|
| `NOTION_API_KEY` | ✅ | — | Notion Integration Token |
| `NOTION_ARTICLES_DATABASE_ID` | ✅ | — | 阅读数据库 ID |
| `NOTION_FEEDS_DATABASE_ID` | ✅ | — | 订阅数据库 ID |
| `TIMEZONE` | — | `Asia/Shanghai` | IANA 时区名称 |
| `CLEANUP_DAYS` | — | `30` | 保留天数（双重作用）：① 首次运行只导入最近 N 天；② 定期清理超过 N 天的 Unread 文章。`-1` 则导入全部历史数据且禁用自动清理 |

---

## 🗃️ Notion 数据库说明

### 订阅数据库属性

| 属性名 | 类型 | 说明 |
|--------|------|------|
| `Name` | title | 订阅站点名（为空时自动填入 RSS 频道标题） |
| `URL` | url | RSS 订阅链接 |
| `Disabled` | checkbox | 勾选后该订阅不会被同步 |
| `FullTextEnabled` | checkbox | 开启后保存完整正文；关闭则仅保存元数据 |
| `Status` | select | 同步状态：`Active`（成功）/ `Error`（失败） |
| `LastUpdate` | date | 上次同步时间（自动维护） |
| `Tags` | multi_select | 订阅级别标签，会附加到该订阅的所有文章 |

### 阅读数据库属性

| 属性名 | 类型 | 说明 |
|--------|------|------|
| `Name` | title | 文章标题 |
| `URL` | url | 文章链接 |
| `Published` | date | 发布时间 |
| `Author` | rich_text | 作者 |
| `Tags` | multi_select | 标签（RSS 标签 + 订阅标签合并） |
| `State` | select | 阅读状态：`Unread` / `Reading` / `Starred` |
| `Source` | relation | 关联到订阅数据库 |

---

## 🛠️ 本地开发

```bash
# 克隆仓库
git clone https://github.com/your-username/RSS2Notion.git
cd RSS2Notion

# 安装依赖（需要 Python 3.14+ 和 uv）
uv sync

# 配置环境变量
export NOTION_API_KEY=your_token
export NOTION_ARTICLES_DATABASE_ID=your_reading_db_id
export NOTION_FEEDS_DATABASE_ID=your_subscription_db_id

# 运行
uv run python -m rss2notion
```

---

## 🙏 致谢

- [lcoolcool/notion-rss-reader](https://github.com/lcoolcool/notion-rss-reader) — 灵感参考
- [feedparser](https://github.com/kurtmckee/feedparser) — RSS 解析
- [mistletoe](https://github.com/miyuchina/mistletoe) — Markdown AST 解析
- [markdownify](https://github.com/matthewwithanm/python-markdownify) — HTML 转 Markdown

---

## 📄 License

本项目基于 [MIT License](./LICENSE) 开源。
