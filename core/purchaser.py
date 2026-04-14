"""抢购核心流程模块"""

import time
from datetime import datetime
from enum import Enum

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout

from core.browser import BrowserManager
from core.config_loader import AppConfig
from core.notifier import NtfyNotifier
from utils.logger import get_logger
from utils.screenshot import take_screenshot

logger = get_logger(__name__)


class PurchaseStatus(Enum):
    """抢购结果状态"""
    SUCCESS = "success"
    PAYMENT_READY = "payment_ready"
    SOLD_OUT = "sold_out"
    FAILED = "failed"
    LOGIN_EXPIRED = "login_expired"


class PurchaseResult:
    """抢购结果"""

    def __init__(self, status: PurchaseStatus, message: str = "",
                 screenshot_path: str = ""):
        self.status = status
        self.message = message
        self.screenshot_path = screenshot_path
        self.timestamp = datetime.now()


class Purchaser:
    """抢购核心流程"""

    def __init__(self, browser_manager: BrowserManager, config: AppConfig,
                 notifier: NtfyNotifier):
        self._browser = browser_manager
        self._config = config
        self._notifier = notifier

    def execute(self, skip_wait: bool = False) -> PurchaseResult:
        """
        执行完整抢购流程

        Args:
            skip_wait: 是否跳过定时等待（--now 模式）

        Returns:
            PurchaseResult 抢购结果
        """
        try:
            page = self._browser.start()

            # 步骤1: 打开页面预热
            self._prewarm(page)

            # 步骤2: 等待到目标时间
            if not skip_wait:
                self._wait_until_target_time()

            # 步骤3: 尝试点击订阅（带重试）
            result = self._attempt_purchase(page)

            return result

        except Exception as e:
            logger.error(f"抢购流程异常: {e}", exc_info=True)
            screenshot = ""
            try:
                screenshot = take_screenshot(self._browser.page, "error")
            except Exception:
                pass
            self._notifier.notify_failure(str(e), screenshot)
            return PurchaseResult(PurchaseStatus.FAILED, str(e), screenshot)
        finally:
            self._browser.close()

    def _prewarm(self, page: Page) -> None:
        """提前打开页面预热，确保资源已加载"""
        logger.info("=== 开始页面预热 ===")
        self._browser.navigate(self._config.target.url)
        take_screenshot(page, "prewarm")
        logger.info("页面预热完成")

    def _wait_until_target_time(self) -> None:
        """精确等待到 start_time（自旋等待，10ms精度）"""
        now = datetime.now()
        h, m = map(int, self._config.target.start_time.split(":"))
        target = now.replace(hour=h, minute=m, second=0, microsecond=0)

        if target <= now:
            logger.warning(f"开始时间 {self._config.target.start_time} 已过，立即执行")
            return

        diff = (target - now).total_seconds()
        logger.info(f"等待开始时间 {self._config.target.start_time}（还有 {diff:.0f} 秒）")

        # 粗等到还剩1秒
        if diff > 1:
            time.sleep(diff - 1)

        # 精确自旋等待
        while datetime.now() < target:
            time.sleep(0.01)

        logger.info("已到达目标时间！")

    def _attempt_purchase(self, page: Page) -> PurchaseResult:
        """多轮多重重试的抢购尝试"""
        rounds = self._config.purchase.rounds
        round_interval = self._config.purchase.round_interval
        max_retries = self._config.purchase.max_retries
        retry_interval = self._config.purchase.retry_interval

        for round_num in range(1, rounds + 1):
            logger.info(f"====== 第 {round_num}/{rounds} 轮 ======")

            # 每轮开始前刷新页面
            if round_num > 1 or self._config.purchase.page_refresh_before_click:
                self._browser.reload()
                take_screenshot(page, f"round_{round_num}_start")

            # 检查登录态
            if self._check_login_expired(page):
                self._notifier.notify_login_expired()
                return PurchaseResult(
                    PurchaseStatus.LOGIN_EXPIRED,
                    "登录态可能已过期，请重新登录"
                )

            # 检查售罄
            if self._check_sold_out(page):
                logger.info("检测到售罄标识")

            # 每轮内重试
            for attempt in range(1, max_retries + 1):
                logger.info(f"--- 第 {attempt}/{max_retries} 次尝试 ---")

                # 尝试点击订阅按钮
                click_result = self._click_subscribe(page)
                if click_result:
                    # 检测支付弹窗
                    payment_result = self._detect_payment(page)
                    if payment_result:
                        return payment_result

                if attempt < max_retries:
                    logger.warning(f"尝试失败，{retry_interval}秒后重试...")
                    time.sleep(retry_interval)

            # 本轮全部失败
            if round_num < rounds:
                logger.warning(f"第 {round_num} 轮失败，{round_interval}秒后开始下一轮")
                time.sleep(round_interval)

        # 所有轮次用尽
        screenshot = take_screenshot(page, "failed_all_rounds")
        msg = f"抢购失败（已执行 {rounds} 轮，每轮 {max_retries} 次）"
        self._notifier.notify_failure(msg, screenshot)
        return PurchaseResult(PurchaseStatus.FAILED, msg, screenshot)

    def _check_login_expired(self, page: Page) -> bool:
        """检查是否跳转到了登录页面"""
        current_url = page.url
        login_indicators = ["login", "signin", "passport"]
        return any(indicator in current_url.lower() for indicator in login_indicators)

    def _check_sold_out(self, page: Page) -> bool:
        """检查售罄标识"""
        selector = self._config.selectors.sold_out_indicator
        if not selector:
            return False

        try:
            element = page.query_selector(selector)
            return element is not None and element.is_visible()
        except Exception:
            return False

    def _click_subscribe(self, page: Page) -> bool:
        """
        尝试点击订阅按钮

        Returns:
            是否成功点击
        """
        selector = self._config.selectors.subscribe_button
        if not selector:
            logger.error("subscribe_button 选择器未配置，无法点击")
            return False

        try:
            logger.info(f"等待订阅按钮出现: {selector}")
            page.wait_for_selector(
                selector,
                timeout=self._config.purchase.click_timeout,
                state="visible"
            )

            logger.info("订阅按钮已出现，准备点击")
            page.click(selector)
            logger.info("已点击订阅按钮！")
            take_screenshot(page, "after_click")
            return True

        except PlaywrightTimeout:
            logger.warning("等待订阅按钮超时")
            take_screenshot(page, "button_timeout")
            return False
        except Exception as e:
            logger.error(f"点击订阅按钮异常: {e}")
            take_screenshot(page, "click_error")
            return False

    def _detect_payment(self, page: Page) -> PurchaseResult | None:
        """
        检测支付弹窗

        Returns:
            PurchaseResult 如果检测到支付弹窗；None 如果未检测到
        """
        selector = self._config.selectors.payment_dialog
        if not selector:
            logger.warning("payment_dialog 选择器未配置，跳过支付检测")
            return None

        try:
            logger.info(f"等待支付弹窗出现: {selector}")
            page.wait_for_selector(
                selector,
                timeout=self._config.purchase.payment_wait_timeout,
                state="visible"
            )

            logger.info("支付弹窗已出现！")
            screenshot = take_screenshot(page, "payment_ready")

            # 发送通知提醒扫码
            self._notifier.notify_payment_ready(screenshot)

            # 等待用户完成支付（持续监测页面变化）
            payment_done = self._wait_for_payment_complete(page)

            if payment_done:
                self._notifier.notify_success()
                return PurchaseResult(
                    PurchaseStatus.SUCCESS,
                    "抢购成功，支付已完成",
                    screenshot
                )
            else:
                return PurchaseResult(
                    PurchaseStatus.PAYMENT_READY,
                    "支付弹窗已出现，等待用户扫码",
                    screenshot
                )

        except PlaywrightTimeout:
            logger.warning("等待支付弹窗超时")
            take_screenshot(page, "payment_timeout")
            return None
        except Exception as e:
            logger.error(f"检测支付弹窗异常: {e}")
            return None

    def _wait_for_payment_complete(self, page: Page,
                                    timeout: int = 180) -> bool:
        """
        等待用户完成支付

        通过监测支付弹窗消失或页面跳转来判断

        Args:
            page: Playwright Page
            timeout: 最大等待秒数

        Returns:
            是否在超时前完成支付
        """
        selector = self._config.selectors.payment_dialog
        start_time = time.time()

        logger.info(f"等待支付完成（超时 {timeout}秒）...")

        while time.time() - start_time < timeout:
            try:
                # 检查支付弹窗是否消失
                element = page.query_selector(selector)
                if element is None or not element.is_visible():
                    logger.info("支付弹窗已消失，支付可能已完成")
                    return True
            except Exception:
                # 页面可能已跳转
                return True

            time.sleep(2)

        logger.warning("等待支付超时")
        return False
