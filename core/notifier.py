"""ntfy 推送通知模块"""

import requests

from core.config_loader import NtfyConfig
from utils.logger import get_logger

logger = get_logger(__name__)


class NtfyNotifier:
    """通过 ntfy.sh 发送推送通知"""

    def __init__(self, config: NtfyConfig):
        self._url = config.url
        self._enabled = config.enabled

    def _send(self, message: str, title: str = "GLM Coding",
              priority: str = "default", tags: str = "") -> bool:
        """
        发送 ntfy 通知

        Args:
            message: 通知内容（支持中文）
            title: 通知标题（ASCII only，HTTP header 限制）
            priority: 优先级 (min/low/default/high/max)
            tags: 标签（逗号分隔）

        Returns:
            是否发送成功
        """
        if not self._enabled:
            logger.debug("ntfy 通知已禁用，跳过发送")
            return False

        if not self._url:
            logger.warning("ntfy URL 未配置，无法发送通知")
            return False

        headers = {"Title": title, "Priority": priority}
        if tags:
            headers["Tags"] = tags

        try:
            resp = requests.post(
                self._url,
                data=message.encode("utf-8"),
                headers=headers,
                timeout=10,
            )
            if resp.status_code == 200:
                logger.info(f"ntfy 通知发送成功: {title}")
                return True
            else:
                logger.warning(f"ntfy 通知发送失败: HTTP {resp.status_code}")
                return False
        except requests.RequestException as e:
            logger.warning(f"ntfy 通知发送异常: {e}")
            return False

    def notify_purchase_started(self) -> None:
        """通知：抢购已开始"""
        self._send("抢购流程已启动，正在执行...", priority="high", tags="rocket")

    def notify_payment_ready(self, screenshot_path: str = "") -> None:
        """通知：支付二维码已出现，请扫码"""
        msg = "支付弹窗已出现！请尽快扫码支付！"
        if screenshot_path:
            msg += f"\n截图: {screenshot_path}"
        self._send(msg, priority="max", tags="warning,money")

    def notify_success(self) -> None:
        """通知：抢购成功"""
        self._send("抢购+支付流程已完成！", priority="high", tags="white_check_mark")

    def notify_failure(self, reason: str, screenshot_path: str = "") -> None:
        """通知：抢购失败"""
        msg = f"抢购失败\n原因: {reason}"
        if screenshot_path:
            msg += f"\n截图: {screenshot_path}"
        self._send(msg, title="GLM Coding 抢购失败", priority="high", tags="x")

    def notify_login_expired(self) -> None:
        """通知：登录态已过期"""
        self._send("登录态可能已过期，请运行 python main.py --login 重新登录",
                   priority="max", tags="lock")
