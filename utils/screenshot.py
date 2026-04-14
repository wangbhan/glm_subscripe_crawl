"""截图工具模块 - 在关键节点自动截图用于调试"""

from datetime import datetime
from pathlib import Path

from playwright.sync_api import Page

from utils.logger import get_logger

logger = get_logger(__name__)

SCREENSHOTS_DIR = Path("./screenshots")


def take_screenshot(page: Page, tag: str = "screenshot") -> str:
    """
    对当前页面截图并保存

    Args:
        page: Playwright Page 对象
        tag: 截图标签，用于文件名

    Returns:
        截图文件的绝对路径
    """
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"{tag}_{timestamp}.png"
    filepath = SCREENSHOTS_DIR / filename

    try:
        page.screenshot(path=str(filepath), full_page=False)
        logger.info(f"截图已保存: {filepath}")
        return str(filepath.resolve())
    except Exception as e:
        logger.error(f"截图失败: {e}")
        return ""
