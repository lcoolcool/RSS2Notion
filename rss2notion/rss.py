"""
RSS 解析：获取订阅条目
"""

import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import feedparser

from .models import RSSEntry, FeedResult

log = logging.getLogger(__name__)


def parse_date(raw: str, tz: ZoneInfo) -> str:
    """将 RSS 日期字符串解析为带时区的 ISO 格式，统一转换到配置时区"""
    # (格式字符串, 解析出的 naive datetime 所对应的时区)
    # GMT/Z 后缀代表 UTC；无时区信息则使用配置时区
    _UTC = timezone.utc
    formats = [
        ("%a, %d %b %Y %H:%M:%S %z", None),   # 自带时区，直接用
        ("%a, %d %b %Y %H:%M:%S GMT", _UTC),   # GMT = UTC
        ("%Y-%m-%dT%H:%M:%S%z",       None),   # 自带时区，直接用
        ("%Y-%m-%dT%H:%M:%SZ",        _UTC),   # Z = UTC
    ]
    for fmt, fallback_tz in formats:
        try:
            dt = datetime.strptime(raw, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=fallback_tz or tz)
            # 统一转到配置时区，确保后续字符串比较等价于时间比较
            return dt.astimezone(tz).isoformat()
        except (ValueError, TypeError):
            continue
    # 无法解析时使用当前时间
    return datetime.now(tz).isoformat()


def parse_rss(url: str, tz: ZoneInfo) -> FeedResult:
    """解析 RSS feed，返回频道标题和条目列表"""
    log.info(f"解析 RSS: {url}")
    feed = feedparser.parse(url)

    if feed.bozo and not feed.entries:
        raise ValueError(f"RSS 解析异常: {feed.bozo_exception}")

    feed_title = getattr(feed.feed, "title", "") or ""

    # 提取频道级封面图（RSS <image> 标签）
    channel_image = ""
    if hasattr(feed.feed, "image"):
        channel_image = feed.feed.image.get("url", "")
    elif hasattr(feed.feed, "logo"):
        channel_image = feed.feed.logo

    entries = []
    for e in feed.entries:
        html_content = ""
        if hasattr(e, "content"):
            for c in e.content:
                if c.get("type") == "text/html":
                    html_content = c.get("value", "")
                    break
        if not html_content:
            html_content = getattr(e, "summary", "") or ""

        # 条目级缩略图（media:thumbnail / enclosure 图片）
        entry_thumb = ""
        if hasattr(e, "media_thumbnail") and e.media_thumbnail:
            entry_thumb = e.media_thumbnail[0].get("url", "")
        elif hasattr(e, "enclosures"):
            for enc in e.enclosures:
                if enc.get("type", "").startswith("image/"):
                    entry_thumb = enc.get("url", "")
                    break

        tags = [t.get("term", "") for t in getattr(e, "tags", [])]
        published = parse_date(e.get("published", ""), tz)

        entry = RSSEntry(
            title=e.get("title", "无标题"),
            url=e.get("link", ""),
            published=published,
            author=e.get("author", ""),
            tags=[t for t in tags if t],
            content_html=html_content,
            channel_image=channel_image,
        )
        # 条目级缩略图优先级最高（覆盖内容里提取的图）
        if entry_thumb:
            entry.cover_image = entry_thumb
        entries.append(entry)

    log.info(f"获取到 {len(entries)} 条条目，频道: {feed_title or url}")
    return FeedResult(feed_title=feed_title, entries=entries)
