"""
数据模型定义
"""

from dataclasses import dataclass, field
from typing import Optional

from .converter import split_html_to_blocks


@dataclass
class RSSEntry:
    title: str
    url: str
    published: str
    author: str
    tags: list[str]
    content_html: str
    # 频道级封面图（RSS <image> 标签），条目无图时兜底使用
    channel_image: str = ""
    # 解析后的「块列表」，每个块是 ("text", markdown字符串) 或 ("image", url)
    blocks: list[tuple] = field(default_factory=list, init=False)
    # 最终封面：优先取文章第一张图，没有则用频道图
    cover_image: str = field(default="", init=False)

    def __post_init__(self):
        if self.content_html:
            self.blocks = split_html_to_blocks(self.content_html)
        # 优先用文章内第一张图，无图则降级到频道封面
        for kind, val in self.blocks:
            if kind == "image":
                self.cover_image = val
                break
        if not self.cover_image:
            self.cover_image = self.channel_image


@dataclass
class FeedResult:
    """parse_rss 的返回值"""
    feed_title: str
    entries: list[RSSEntry]


@dataclass
class Subscription:
    """对应 Notion 订阅数据库中的一行"""
    page_id: str
    name: str
    url: str
    disabled: bool
    full_text_enabled: bool
    status: str                     # Active / Error
    last_update: Optional[str]      # ISO 日期，可为 None
    tags: list[str]
