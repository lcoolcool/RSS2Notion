"""
主同步流程编排
"""

import logging
import time
from datetime import datetime

from .config import Config
from .converter import entry_to_notion_blocks
from .notion.client import NotionClient
from .notion.cleanup import cleanup_expired_articles
from .notion.subscription import fetch_active_subscriptions, update_subscription_status
from .rss import parse_rss

log = logging.getLogger(__name__)


def run(config: Config) -> None:
    """主同步流程"""
    client = NotionClient(
        api_key=config.notion_api_key,
        retry_times=config.retry_times,
        retry_delay=config.retry_delay,
    )

    # 获取所有活跃订阅
    try:
        subscriptions = fetch_active_subscriptions(client, config.feeds_database_id)
    except Exception as e:
        log.error(f"读取订阅数据库失败: {e}")
        return

    if not subscriptions:
        log.warning("没有活跃的订阅，退出")
        return

    total_written = total_skipped = total_failed = 0

    for subscription in subscriptions:
        log.info(f"── 处理订阅: {subscription.name or subscription.url}")

        # 解析 RSS
        try:
            feed_result = parse_rss(subscription.url, config.timezone)
        except Exception as e:
            log.error(f"  RSS 解析失败: {e}")
            update_subscription_status(
                client, subscription, status="Error", tz=config.timezone
            )
            continue

        entries = feed_result.entries

        # 用 LastUpdate 时间过滤：只处理新文章
        if subscription.last_update:
            before_filter = len(entries)
            entries = [
                e for e in entries
                if not e.published or e.published > subscription.last_update
            ]
            log.info(f"  时间过滤：{before_filter} → {len(entries)} 条新文章")

        if not entries:
            log.info("  没有新文章，跳过")
            update_subscription_status(
                client, subscription,
                status="Active",
                tz=config.timezone,
                feed_title=feed_result.feed_title,
            )
            continue

        # 批量查询已存在的 URL（去重）
        existing_urls: set[str] = set()
        try:
            existing_urls = client.query_pages_by_source(
                config.entries_database_id, subscription.page_id
            )
            log.info(f"  已存在 {len(existing_urls)} 条记录（用于去重）")
        except Exception as e:
            log.warning(f"  批量去重查询失败，将逐条跳过: {e}")

        written = skipped = failed = 0

        for idx, entry in enumerate(entries, 1):
            log.info(f"  [{idx}/{len(entries)}] {entry.title[:60]}")

            # URL 去重
            if entry.url and entry.url in existing_urls:
                log.info("    → 已存在，跳过")
                skipped += 1
                continue

            try:
                if subscription.full_text_enabled:
                    # 全文模式
                    all_blocks = entry_to_notion_blocks(entry)
                    first_batch = all_blocks[:config.notion_block_limit]
                    rest_blocks = all_blocks[config.notion_block_limit:]

                    img_count = sum(1 for b in all_blocks if b.get("type") == "image")
                    log.info(f"    blocks: {len(all_blocks)} 个（含 {img_count} 张图片）")

                    page = client.create_page(
                        database_id=config.entries_database_id,
                        entry=entry,
                        blocks=first_batch,
                        source_page_id=subscription.page_id,
                        extra_tags=subscription.tags,
                    )
                    page_id = page["id"]

                    if rest_blocks:
                        client.append_blocks(page_id, rest_blocks)
                else:
                    # 仅元数据模式
                    page = client.create_page_metadata_only(
                        database_id=config.entries_database_id,
                        entry=entry,
                        source_page_id=subscription.page_id,
                        extra_tags=subscription.tags,
                    )
                    page_id = page["id"]

                log.info(f"    ✓ 写入: {page_id}")
                existing_urls.add(entry.url)  # 防止同一次运行中重复写入
                written += 1

            except Exception as e:
                log.error(f"    ✗ 写入失败: {e}")
                failed += 1

            time.sleep(0.4)  # 控制 Notion API 速率

        log.info(f"  订阅完成 — 写入: {written}  跳过: {skipped}  失败: {failed}")
        total_written += written
        total_skipped += skipped
        total_failed += failed

        # 更新订阅状态
        update_subscription_status(
            client, subscription,
            status="Active",
            tz=config.timezone,
            feed_title=feed_result.feed_title,
        )

    # 自动清理过期文章
    cleanup_expired_articles(client, config.entries_database_id, config.cleanup_days, config.timezone)

    log.info(
        f"\n全部完成 — 写入: {total_written}  跳过: {total_skipped}  失败: {total_failed}"
    )
