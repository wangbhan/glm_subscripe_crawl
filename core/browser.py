"""浏览器控制模块 - Playwright 持久化上下文管理"""

from playwright.sync_api import sync_playwright, Page, BrowserContext

from core.config_loader import BrowserConfig
from utils.logger import get_logger

logger = get_logger(__name__)


class BrowserManager:
    """管理 Playwright 浏览器生命周期，使用持久化上下文保持登录态"""

    def __init__(self, config: BrowserConfig):
        self._config = config
        self._playwright = None
        self._context = None
        self._page = None

    def start(self) -> Page:
        """
        启动浏览器并返回活跃页面

        使用 launch_persistent_context 将 cookie/localStorage
        自动持久化到 user_data_dir 目录

        Returns:
            Playwright Page 对象
        """
        if self._page and not self._page.is_closed():
            return self._page

        logger.info("正在启动浏览器...")
        self._playwright = sync_playwright().start()
        self._context = self._playwright.chromium.launch_persistent_context(
            user_data_dir=self._config.user_data_dir,
            headless=self._config.headless,
            viewport=self._config.viewport,
            slow_mo=self._config.slow_mo,
            locale="zh-CN",
            args=["--disable-blink-features=AutomationControlled"],
        )

        # 获取或创建页面
        if self._context.pages:
            self._page = self._context.pages[0]
        else:
            self._page = self._context.new_page()

        logger.info("浏览器启动成功")
        return self._page

    @property
    def page(self) -> Page:
        """获取当前页面"""
        if self._page is None or self._page.is_closed():
            raise RuntimeError("浏览器未启动或页面已关闭")
        return self._page

    @property
    def context(self) -> BrowserContext:
        """获取浏览器上下文"""
        if self._context is None:
            raise RuntimeError("浏览器未启动")
        return self._context

    def navigate(self, url: str, wait_until: str = "networkidle") -> None:
        """
        导航到指定 URL

        Args:
            url: 目标 URL
            wait_until: 等待条件 (load/domcontentloaded/networkidle)
        """
        logger.info(f"正在导航到: {url}")
        self.page.goto(url, wait_until=wait_until, timeout=30000)
        logger.info(f"页面加载完成: {self.page.title()}")

    def reload(self, wait_until: str = "networkidle") -> None:
        """刷新当前页面"""
        logger.info("正在刷新页面...")
        self.page.reload(wait_until=wait_until, timeout=30000)
        logger.info("页面刷新完成")

    def wait_for_login(self) -> None:
        """
        等待用户手动登录（阻塞直到用户在终端确认）

        用于 --login 模式
        """
        input("\n请在浏览器中完成登录后，按 Enter 键继续...")
        logger.info("用户已确认登录完成")

    def close(self) -> None:
        """关闭浏览器并保存上下文"""
        try:
            if self._context:
                self._context.close()
                logger.info("浏览器上下文已关闭（登录态已保存）")
            if self._playwright:
                self._playwright.stop()
        except Exception as e:
            logger.error(f"关闭浏览器时出错: {e}")
        finally:
            self._page = None
            self._context = None
            self._playwright = None
