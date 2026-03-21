"""
命令行入口：python -m rss2notion
"""

import logging

from .config import Config
from .sync import run

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def main() -> None:
    config = Config.from_env()
    run(config)


if __name__ == "__main__":
    main()
