"""
配置管理：从环境变量读取所有配置项
"""

import os
from dataclasses import dataclass
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


@dataclass
class Config:
    notion_api_key: str
    entries_database_id: str           # 文章数据库 ID
    feeds_database_id: str             # 订阅数据库 ID
    timezone: ZoneInfo                 # 时区对象
    cleanup_days: int                  # 清理天数，-1 表示不清理
    notion_block_limit: int = 100      # 首批写入 block 上限
    retry_times: int = 3
    retry_delay: float = 2.0

    @classmethod
    def from_env(cls) -> "Config":
        """从环境变量构建配置，缺失必填项时抛出明确错误"""
        missing = []

        api_key = os.environ.get("NOTION_API_KEY", "")
        if not api_key:
            missing.append("NOTION_API_KEY")

        database_id = os.environ.get("NOTION_ENTRIES_DATABASE_ID", "")
        if not database_id:
            missing.append("NOTION_ENTRIES_DATABASE_ID")

        sub_database_id = os.environ.get("NOTION_FEEDS_DATABASE_ID", "")
        if not sub_database_id:
            missing.append("NOTION_FEEDS_DATABASE_ID")

        if missing:
            raise ValueError(f"缺少必填环境变量: {', '.join(missing)}")

        tz_name = os.environ.get("TIMEZONE", "Asia/Shanghai")
        try:
            tz = ZoneInfo(tz_name)
        except ZoneInfoNotFoundError:
            raise ValueError(f"无效的时区名称: {tz_name}，请使用 IANA 时区格式，如 Asia/Shanghai")

        cleanup_days_str = os.environ.get("CLEANUP_DAYS", "30")
        try:
            cleanup_days = int(cleanup_days_str)
        except ValueError:
            raise ValueError(f"CLEANUP_DAYS 必须为整数，当前值: {cleanup_days_str}")

        return cls(
            notion_api_key=api_key,
            entries_database_id=database_id,
            feeds_database_id=sub_database_id,
            timezone=tz,
            cleanup_days=cleanup_days,
        )
