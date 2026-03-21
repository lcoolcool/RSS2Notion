"""
Notion API 基础客户端
"""

import logging
import time

import requests

log = logging.getLogger(__name__)


class NotionClient:
    BASE = "https://api.notion.com/v1"

    def __init__(self, api_key: str, retry_times: int = 3, retry_delay: float = 2.0):
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        }
        self.retry_times = retry_times
        self.retry_delay = retry_delay

    def _request(self, method: str, path: str, **kwargs) -> dict:
        url = f"{self.BASE}{path}"
        for attempt in range(1, self.retry_times + 1):
            try:
                resp = requests.request(method, url, headers=self.headers, **kwargs)
                if resp.status_code == 429:
                    wait = float(resp.headers.get("Retry-After", self.retry_delay))
                    log.warning(f"触发速率限制，等待 {wait}s …")
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                return resp.json()
            except requests.HTTPError as e:
                log.error(f"HTTP 错误 [{attempt}/{self.retry_times}]: {e.response.text}")
                if attempt == self.retry_times:
                    raise
                time.sleep(self.retry_delay)
        return {}

    # ─────────────────────────────────────────────
    # 阅读数据库操作
    # ─────────────────────────────────────────────

    def query_pages_by_source(self, database_id: str, source_page_id: str) -> set[str]:
        """
        批量查询阅读数据库中指定订阅源的所有已存在 URL，返回 URL 集合。
        用于高效去重：避免逐条 API 查询。
        """
        existing_urls: set[str] = set()
        body = {
            "filter": {
                "property": "Source",
                "relation": {"contains": source_page_id},
            },
            "page_size": 100,
        }
        has_more = True
        next_cursor = None

        while has_more:
            if next_cursor:
                body["start_cursor"] = next_cursor
            result = self._request("POST", f"/databases/{database_id}/query", json=body)
            for page in result.get("results", []):
                url_prop = page.get("properties", {}).get("URL", {})
                url = url_prop.get("url") or ""
                if url:
                    existing_urls.add(url)
            has_more = result.get("has_more", False)
            next_cursor = result.get("next_cursor")

        return existing_urls

    def create_page(
        self,
        database_id: str,
        entry,
        blocks: list[dict],
        source_page_id: str | None = None,
        extra_tags: list[str] | None = None,
    ) -> dict:
        """创建阅读数据库页面（全文模式）"""
        merged_tags = _merge_tags(entry.tags, extra_tags or [])
        properties = _build_entry_properties(entry, merged_tags, source_page_id)
        payload: dict = {
            "parent": {"database_id": database_id},
            "properties": properties,
            "children": blocks,
        }
        if entry.cover_image:
            payload["cover"] = {
                "type": "external",
                "external": {"url": entry.cover_image},
            }
        return self._request("POST", "/pages", json=payload)

    def create_page_metadata_only(
        self,
        database_id: str,
        entry,
        source_page_id: str | None = None,
        extra_tags: list[str] | None = None,
    ) -> dict:
        """创建阅读数据库页面（仅元数据模式，FullTextEnabled=false 时使用）"""
        merged_tags = _merge_tags(entry.tags, extra_tags or [])
        properties = _build_entry_properties(entry, merged_tags, source_page_id)
        payload: dict = {
            "parent": {"database_id": database_id},
            "properties": properties,
        }
        if entry.cover_image:
            payload["cover"] = {
                "type": "external",
                "external": {"url": entry.cover_image},
            }
        return self._request("POST", "/pages", json=payload)

    def append_blocks(self, page_id: str, blocks: list[dict]) -> None:
        """分批追加 blocks（每批最多 100 个）"""
        for i in range(0, len(blocks), 100):
            self._request(
                "PATCH",
                f"/blocks/{page_id}/children",
                json={"children": blocks[i: i + 100]},
            )

    def delete_page(self, page_id: str) -> dict:
        """将页面移入回收站（30 天内可在 Notion 回收站恢复）"""
        return self._request("DELETE", f"/pages/{page_id}")


# ─────────────────────────────────────────────
# 内部辅助函数
# ─────────────────────────────────────────────

def _merge_tags(entry_tags: list[str], subscription_tags: list[str]) -> list[str]:
    """合并文章标签和订阅标签，去重保持顺序"""
    seen: set[str] = set()
    result = []
    for tag in entry_tags + subscription_tags:
        tag = tag[:100]  # Notion 选项名最长 100 字符
        if tag and tag not in seen:
            seen.add(tag)
            result.append(tag)
    return result[:100]  # 最多 100 个选项


def _build_entry_properties(entry, tags: list[str], source_page_id: str | None) -> dict:
    """构建阅读数据库页面的 properties"""
    properties: dict = {
        "Name":      {"title": [{"text": {"content": entry.title[:2000]}}]},
        "URL":       {"url": entry.url or None},
        "Published": {"date": {"start": entry.published}},
        "Author":    {"rich_text": [{"text": {"content": entry.author[:2000]}}]},
        "State":     {"select": {"name": "Unread"}},
    }
    if tags:
        properties["Tags"] = {
            "multi_select": [{"name": t} for t in tags]
        }
    if source_page_id:
        properties["Source"] = {
            "relation": [{"id": source_page_id}]
        }
    return properties
