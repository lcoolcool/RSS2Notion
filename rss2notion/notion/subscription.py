"""
订阅数据库：读取活跃订阅、更新订阅状态
"""

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from ..models import Subscription
from .client import NotionClient

log = logging.getLogger(__name__)


def fetch_active_subscriptions(client: NotionClient, database_id: str) -> list[Subscription]:
    """从订阅数据库读取所有 Disabled=false 的订阅（带分页）"""
    body: dict = {
        "filter": {
            "property": "Disabled",
            "checkbox": {"equals": False},
        },
        "page_size": 100,
    }
    subscriptions = []
    has_more = True
    next_cursor = None

    while has_more:
        if next_cursor:
            body["start_cursor"] = next_cursor
        result = client._request("POST", f"/databases/{database_id}/query", json=body)

        for page in result.get("results", []):
            sub = _parse_subscription(page)
            if sub:
                subscriptions.append(sub)

        has_more = result.get("has_more", False)
        next_cursor = result.get("next_cursor")

    log.info(f"读取到 {len(subscriptions)} 个活跃订阅")
    return subscriptions


def update_subscription_status(
    client: NotionClient,
    subscription: Subscription,
    status: str,
    tz: ZoneInfo,
    feed_title: str | None = None,
) -> None:
    """
    更新订阅的 Status 和 LastUpdate（始终更新为当前运行时间）。
    如果订阅的 Name 为空且 feed_title 不为空，自动回填站点名。
    """
    now_iso = datetime.now(tz).isoformat()
    properties: dict = {
        "Status":     {"select": {"name": status}},
        "LastUpdate": {"date": {"start": now_iso}},
    }

    # 空 Name 时自动回填
    if not subscription.name and feed_title:
        properties["Name"] = {
            "title": [{"text": {"content": feed_title[:2000]}}]
        }

    client._request(
        "PATCH",
        f"/pages/{subscription.page_id}",
        json={"properties": properties},
    )


# ─────────────────────────────────────────────
# 内部辅助函数
# ─────────────────────────────────────────────

def _parse_subscription(page: dict) -> Subscription | None:
    """将 Notion 页面对象解析为 Subscription"""
    try:
        props = page.get("properties", {})

        # Name（title 类型）
        name_items = props.get("Name", {}).get("title", [])
        name = "".join(item.get("plain_text", "") for item in name_items).strip()

        # URL（url 类型）
        url = props.get("URL", {}).get("url") or ""
        if not url:
            log.warning(f"订阅页面 {page['id']} 缺少 URL，跳过")
            return None

        # Disabled（checkbox 类型）
        disabled = props.get("Disabled", {}).get("checkbox", False)

        # FullTextEnabled（checkbox 类型）
        full_text_enabled = props.get("FullTextEnabled", {}).get("checkbox", False)

        # Status（select 类型）
        status_obj = props.get("Status", {}).get("select") or {}
        status = status_obj.get("name", "")

        # LastUpdate（date 类型）
        date_obj = props.get("LastUpdate", {}).get("date") or {}
        last_update = date_obj.get("start")

        # Tags（multi_select 类型）
        tags = [
            t.get("name", "")
            for t in props.get("Tags", {}).get("multi_select", [])
            if t.get("name")
        ]

        return Subscription(
            page_id=page["id"],
            name=name,
            url=url,
            disabled=disabled,
            full_text_enabled=full_text_enabled,
            status=status,
            last_update=last_update,
            tags=tags,
        )
    except Exception as e:
        log.error(f"解析订阅页面失败 {page.get('id', '?')}: {e}")
        return None
