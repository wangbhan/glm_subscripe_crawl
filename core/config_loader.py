"""配置加载与校验模块"""

import shutil
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from utils.logger import get_logger

logger = get_logger(__name__)

CONFIG_FILE = "config.yaml"
EXAMPLE_FILE = "config_example.yaml"

# 全局配置单例
_config = None


@dataclass
class TargetConfig:
    url: str = "https://bigmodel.cn/glm-coding"
    pre_open_seconds: int = 15


@dataclass
class ScheduleConfig:
    enabled: bool = True
    time: str = "10:00"


@dataclass
class BrowserConfig:
    user_data_dir: str = "./browser_data"
    headless: bool = False
    viewport: dict = field(default_factory=lambda: {"width": 1280, "height": 800})
    slow_mo: int = 50


@dataclass
class SelectorsConfig:
    subscribe_button: str = ""
    payment_dialog: str = ""
    sold_out_indicator: str = ""


@dataclass
class PurchaseConfig:
    max_retries: int = 3
    retry_interval: int = 2
    page_refresh_before_click: bool = True
    click_timeout: int = 5000
    payment_wait_timeout: int = 60000


@dataclass
class NtfyConfig:
    enabled: bool = True
    url: str = ""


@dataclass
class LoggingConfig:
    level: str = "INFO"
    file: str = "./logs/app.log"
    max_bytes: int = 10 * 1024 * 1024
    backup_count: int = 5


@dataclass
class AppConfig:
    target: TargetConfig = field(default_factory=TargetConfig)
    schedule: ScheduleConfig = field(default_factory=ScheduleConfig)
    browser: BrowserConfig = field(default_factory=BrowserConfig)
    selectors: SelectorsConfig = field(default_factory=SelectorsConfig)
    purchase: PurchaseConfig = field(default_factory=PurchaseConfig)
    ntfy: NtfyConfig = field(default_factory=NtfyConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)


def _dict_to_dataclass(cls, data: dict):
    """将字典转换为 dataclass 实例，忽略多余字段"""
    if not isinstance(data, dict):
        return cls()
    valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
    filtered = {k: v for k, v in data.items() if k in valid_fields}
    return cls(**filtered)


def _validate_config(config: AppConfig) -> list[str]:
    """校验配置项，返回警告信息列表"""
    warnings = []

    if not config.selectors.subscribe_button:
        warnings.append(
            "selectors.subscribe_button 未配置，请用 F12 确认后填入 config.yaml"
        )

    if not config.selectors.payment_dialog:
        warnings.append(
            "selectors.payment_dialog 未配置，请用 F12 确认后填入 config.yaml"
        )

    if config.ntfy.enabled and not config.ntfy.url:
        warnings.append("ntfy.url 未配置，通知功能将不可用")

    return warnings


def load_config(path: str = CONFIG_FILE) -> AppConfig:
    """
    加载并校验配置文件

    如果配置文件不存在，自动从示例文件复制一份

    Args:
        path: 配置文件路径

    Returns:
        AppConfig 实例
    """
    config_path = Path(path)

    if not config_path.exists():
        example_path = Path(EXAMPLE_FILE)
        if example_path.exists():
            shutil.copy2(example_path, config_path)
            logger.info(f"已从 {EXAMPLE_FILE} 复制配置文件到 {path}")
            logger.info(f"请编辑 {path} 填写实际配置后重新运行")
        else:
            logger.warning(f"配置文件 {path} 不存在，将使用默认配置")

    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
    else:
        raw = {}

    config = AppConfig(
        target=_dict_to_dataclass(TargetConfig, raw.get("target", {})),
        schedule=_dict_to_dataclass(ScheduleConfig, raw.get("schedule", {})),
        browser=_dict_to_dataclass(BrowserConfig, raw.get("browser", {})),
        selectors=_dict_to_dataclass(SelectorsConfig, raw.get("selectors", {})),
        purchase=_dict_to_dataclass(PurchaseConfig, raw.get("purchase", {})),
        ntfy=_dict_to_dataclass(NtfyConfig, raw.get("ntfy", {})),
        logging=_dict_to_dataclass(LoggingConfig, raw.get("logging", {})),
    )

    warnings = _validate_config(config)
    for w in warnings:
        logger.warning(w)

    return config


def get_config() -> AppConfig:
    """获取全局配置单例"""
    global _config
    if _config is None:
        _config = load_config()
    return _config
