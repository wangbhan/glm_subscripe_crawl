"""定时调度模块 - APScheduler cron 触发"""

from apscheduler.schedulers.blocking import BlockingScheduler

from core.browser import BrowserManager
from core.config_loader import AppConfig
from core.notifier import NtfyNotifier
from core.purchaser import Purchaser
from utils.logger import get_logger

logger = get_logger(__name__)


class TaskScheduler:
    """定时任务调度器"""

    def __init__(self, config: AppConfig):
        self._config = config
        self._scheduler = BlockingScheduler()
        self._notifier = NtfyNotifier(config.ntfy)

    def start(self) -> None:
        """启动定时调度（阻塞运行）"""
        time_str = self._config.schedule.time
        parts = time_str.split(":")
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0

        self._scheduler.add_job(
            self._run_purchase,
            "cron",
            hour=hour,
            minute=minute,
            second=0,
            id="glm_purchase",
            name="GLM Coding 抢购",
            max_instances=1,
            misfire_grace_time=30,
        )

        logger.info(f"定时任务已设定：每天 {time_str} 执行抢购")
        logger.info("按 Ctrl+C 可停止调度器")

        try:
            self._scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("调度器已停止")

    def _run_purchase(self) -> None:
        """执行一次抢购任务"""
        logger.info("========== 定时任务触发 ==========")
        self._notifier.notify_purchase_started()

        browser_manager = BrowserManager(self._config.browser)
        purchaser = Purchaser(browser_manager, self._config, self._notifier)

        # skip_wait=False: 让 purchaser 自行等待到 target.start_time
        result = purchaser.execute(skip_wait=False)

        logger.info(
            f"抢购结果: status={result.status.value}, "
            f"message={result.message}"
        )
