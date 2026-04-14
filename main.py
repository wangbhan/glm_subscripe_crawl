"""
GLM Coding 订阅自动抢购脚本

用法:
  python main.py              # 启动定时抢购（每天 10:00）
  python main.py --now        # 立即执行一次（不等待定时）
  python main.py --login      # 首次登录（保存浏览器登录态）
"""

import argparse
import sys

from core.browser import BrowserManager
from core.config_loader import load_config
from core.notifier import NtfyNotifier
from core.purchaser import Purchaser
from core.scheduler import TaskScheduler
from utils.logger import get_logger


def run_login(config) -> None:
    """首次登录模式：打开浏览器等待用户手动登录"""
    logger = get_logger("glm_purchase", level=config.logging.level,
                        log_file=config.logging.file)
    logger.info("=== 首次登录模式 ===")
    logger.info("将打开浏览器，请手动完成登录后按 Enter")

    browser = BrowserManager(config.browser)
    try:
        browser.start()
        browser.navigate("https://bigmodel.cn")
        browser.wait_for_login()
        logger.info("登录完成！登录态已保存到 browser_data/ 目录")
    finally:
        browser.close()


def run_now(config) -> None:
    """立即执行一次抢购"""
    logger = get_logger("glm_purchase", level=config.logging.level,
                        log_file=config.logging.file)
    logger.info("=== 立即执行模式 ===")

    notifier = NtfyNotifier(config.ntfy)
    browser = BrowserManager(config.browser)
    purchaser = Purchaser(browser, config, notifier)

    result = purchaser.execute(skip_wait=True)
    logger.info(f"执行结果: {result.status.value} - {result.message}")


def run_scheduled(config) -> None:
    """启动定时调度"""
    logger = get_logger("glm_purchase", level=config.logging.level,
                        log_file=config.logging.file)
    logger.info("=== 定时调度模式 ===")

    if not config.schedule.enabled:
        logger.error("定时调度未启用（schedule.enabled = false）")
        sys.exit(1)

    scheduler = TaskScheduler(config)
    scheduler.start()


def main():
    parser = argparse.ArgumentParser(
        description="GLM Coding 订阅自动抢购脚本"
    )
    parser.add_argument(
        "--now", action="store_true",
        help="立即执行一次抢购（不等待定时）"
    )
    parser.add_argument(
        "--login", action="store_true",
        help="首次登录模式（打开浏览器手动登录）"
    )
    args = parser.parse_args()

    config = load_config()

    if args.login:
        run_login(config)
    elif args.now:
        run_now(config)
    else:
        run_scheduled(config)


if __name__ == "__main__":
    main()
