"""
自动清理：删除超过指定天数的 Unread 文章
"""

import logging
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from .client import NotionClient

log = logging.getLogger(__name__)


def cleanup_expired_articles(
    client: NotionClient,
    database_id: str,
    cleanup_days: int,
    tz: ZoneInfo,
) -> int:
    """
    清理 State=Unread 且 Published 超过 cleanup_days 天的文章。
    cleanup_days=-1 时跳过清理。
    删除操作实为移入 Notion 回收站（30 天内可恢复）。
    返回删除数量。
    """
    if cleanup_days < 0:
        log.info("自动清理已禁用（CLEANUP_DAYS=-1）")
        return 0

    cutoff = datetime.now(tz) - timedelta(days=cleanup_days)
    cutoff_iso = cutoff.isoformat()
    log.info(f"清理 {cleanup_days} 天前的 Unread 文章（截止: {cutoff_iso[:10]}）")

    body: dict = {
        "filter": {
            "and": [
                {
                    "property": "State",
                    "select": {"equals": "Unread"},
                },
                {
                    "property": "Published",
                    "date": {"before": cutoff_iso},
                },
            ]
        },
        "page_size": 100,
    }

    deleted_count = 0
    has_more = True
    next_cursor = None

    while has_more:
        if next_cursor:
            body["start_cursor"] = next_cursor

        result = client._request("POST", f"/databases/{database_id}/query", json=body)
        pages = result.get("results", [])

        for page in pages:
            try:
                client.delete_page(page["id"])
                deleted_count += 1
                time.sleep(0.3)  # 控制速率
            except Exception as e:
                log.error(f"删除页面 {page['id']} 失败: {e}")

        has_more = result.get("has_more", False)
        next_cursor = result.get("next_cursor")

    log.info(f"清理完成：删除了 {deleted_count} 篇过期文章")
    return deleted_count
