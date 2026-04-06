English | [简体中文](./README_ZH.md)

<div align="center">

# RSS2Notion

**Automatically sync RSS feeds to Notion — build your personal reading space**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/Python-3.14+-green.svg)](https://www.python.org/)

</div>

---

![Overview](./docs/images/overview.png)

---

## ✨ Features

- **Notion-based subscription management** — Add, edit, and disable RSS sources directly in Notion, no config files needed
- **Full-text or metadata-only mode** — Each subscription can independently enable full-text saving; when disabled, only title, URL, author, and publish date are saved
- **Smart deduplication** — Timestamp-based filtering + batch URL lookup to efficiently avoid duplicate entries
- **Image-text layout** — Article images are fully preserved and interleaved with text in Notion pages
- **Tag aggregation** — RSS tags and subscription-level custom tags are merged automatically
- **Cover image extraction** — Automatically picks the first article image or channel logo as the page cover
- **Reading state tracking** — New articles are automatically marked `Unread`; supports `Reading` / `Starred` states
- **Source relation** — Each article is linked back to its subscription via Notion Relation
- **Auto cleanup** — Periodically deletes overdue unread articles to keep your database tidy (configurable retention period)
- **Subscription status feedback** — Failed subscriptions are automatically marked as `Error` for easy troubleshooting
- **Scheduled via GitHub Actions** — Runs every hour automatically, no server required

---

## 🚀 Quick Start

### Prerequisites

- A [Notion](https://www.notion.so/) account
- A GitHub account

### Step 1: Duplicate the Notion Template

Click the link below to duplicate the template into your Notion workspace:

👉 [**Duplicate Notion Template**](https://aeolian-saga-950.notion.site/RSS-Hub-32c4c2f98bee8000b3e7e7fb4c0d644a) — click "Duplicate" in the top-right corner to add it to your Notion workspace.

The template includes two databases:
- **Subscription Database** — Manage your RSS feed sources
- **Reading Database** — Store synced articles

![Template](./docs/images/template.png)

### Step 2: Create a Notion Integration

1. Go to [Notion Integrations](https://www.notion.so/profile/integrations) and create a new Integration
2. Select your workspace and submit — copy the **Internal Integration Token** (this is your `NOTION_API_KEY`)

![Integration](./docs/images/integration.png)

3. Configure content access permissions for the Integration:

![Integration Permissions](./docs/images/integration_perm.png)

### Step 3: Get Database IDs

Extract the database ID from the Notion page URL:

```
https://www.notion.so/your-workspace/xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx?v=...
                                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                     This 32-character segment is the Database ID
```

- **Articles Database ID** → `NOTION_ARTICLES_DATABASE_ID`
- **Subscription Database ID** → `NOTION_FEEDS_DATABASE_ID`

### Step 4: Fork the Repository and Configure Secrets

1. Click **Fork** in the top-right corner to copy this repository to your GitHub account
2. Go to your forked repo → **Settings** → **Secrets and variables** → **Actions**
3. Add the following **Repository Secrets**:

| Secret Name | Description |
|------------|-------------|
| `NOTION_API_KEY` | Notion Integration Token |
| `NOTION_ARTICLES_DATABASE_ID` | Reading Database ID |
| `NOTION_FEEDS_DATABASE_ID` | Subscription Database ID |

![Secrets](./docs/images/secrets.png)

4. (Optional) Add the following **Repository Variables** (Settings → Secrets and variables → Actions → Variables):

| Variable Name | Default | Description |
|--------------|---------|-------------|
| `TIMEZONE` | `Asia/Shanghai` | Timezone in [IANA format](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones) |
| `CLEANUP_DAYS` | `30` | Dual-purpose: ① on first run, only import articles from the last N days; ② periodically delete Unread articles older than N days. Set to `-1` to import all history on first run and disable auto cleanup |

### Step 5: Enable GitHub Actions and Run Manually

1. Go to the **Actions** tab of your repository
2. If prompted, click **I understand my workflows, go ahead and enable them**
3. Select **RSS Sync** on the left → click **Run workflow** to trigger the first sync manually

![Actions](./docs/images/action.png)

After that, the sync will run automatically every hour.

> **(Optional) Change the sync frequency**
> Edit the cron expression in `.github/workflows/sync.yml`:
> ```yaml
> - cron: '0 * * * *'  # every hour
> ```
> For example: every 30 minutes — `'*/30 * * * *'`, every 6 hours — `'0 */6 * * *'`.
> Use [crontab.guru](https://crontab.guru/) to generate expressions.

---

## ⚙️ Configuration

| Environment Variable | Required | Default | Description |
|--------------------|:--------:|---------|-------------|
| `NOTION_API_KEY` | ✅ | — | Notion Integration Token |
| `NOTION_ARTICLES_DATABASE_ID` | ✅ | — | Reading Database ID |
| `NOTION_FEEDS_DATABASE_ID` | ✅ | — | Subscription Database ID |
| `TIMEZONE` | — | `Asia/Shanghai` | IANA timezone name |
| `CLEANUP_DAYS` | — | `30` | Dual-purpose: ① first run imports only the last N days; ② auto-deletes Unread articles older than N days. `-1` imports all history and disables cleanup |

---

## 🗃️ Notion Database Schema

### Subscription Database

| Property | Type | Description |
|----------|------|-------------|
| `Name` | title | Feed name (auto-filled from RSS channel title if left empty) |
| `URL` | url | RSS feed URL |
| `Disabled` | checkbox | When checked, this subscription will be skipped |
| `FullTextEnabled` | checkbox | When enabled, saves full article content; otherwise saves metadata only |
| `Status` | select | Sync status: `Active` (success) / `Error` (failed) |
| `LastUpdate` | date | Last sync time (maintained automatically) |
| `Tags` | multi_select | Subscription-level tags, appended to all articles from this source |

### Reading Database

| Property | Type | Description |
|----------|------|-------------|
| `Name` | title | Article title |
| `URL` | url | Article link |
| `Published` | date | Publish time |
| `Author` | rich_text | Author |
| `Tags` | multi_select | Tags (merged from RSS tags + subscription tags) |
| `State` | select | Reading state: `Unread` / `Reading` / `Starred` |
| `Source` | relation | Linked to the Subscription Database |

---

## 🛠️ Local Development

```bash
# Clone the repository
git clone https://github.com/your-username/RSS2Notion.git
cd RSS2Notion

# Install dependencies (requires Python 3.14+ and uv)
uv sync

# Set environment variables
export NOTION_API_KEY=your_token
export NOTION_ARTICLES_DATABASE_ID=your_reading_db_id
export NOTION_FEEDS_DATABASE_ID=your_subscription_db_id

# Run
uv run python -m rss2notion
```

---

## 🙏 Acknowledgements

- [watsuyo/notion-rss-reader](https://github.com/watsuyo/notion-rss-reader) — Inspiration
- [Yutu0k/RSS-to-Notion](https://github.com/Yutu0k/RSS-to-Notion) — Inspiration
- [feedparser](https://github.com/kurtmckee/feedparser) — RSS parsing
- [mistletoe](https://github.com/miyuchina/mistletoe) — Markdown AST parsing
- [markdownify](https://github.com/matthewwithanm/python-markdownify) — HTML to Markdown

---

## 📄 License

This project is licensed under the [MIT License](./LICENSE).
