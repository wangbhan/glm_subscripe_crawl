"""日志工具模块 - 控制台彩色输出 + 文件轮转"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


class ColorFormatter(logging.Formatter):
    """控制台彩色格式化器"""

    COLORS = {
        logging.DEBUG: "\033[36m",     # 青色
        logging.INFO: "\033[32m",      # 绿色
        logging.WARNING: "\033[33m",   # 黄色
        logging.ERROR: "\033[31m",     # 红色
        logging.CRITICAL: "\033[35m",  # 紫色
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelno, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


def get_logger(
    name: str = "glm_purchase",
    level: str = "INFO",
    log_file: str = "./logs/app.log",
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
) -> logging.Logger:
    """
    获取配置好的 Logger 实例

    Args:
        name: logger 名称
        level: 日志级别
        log_file: 日志文件路径
        max_bytes: 单个日志文件最大字节数
        backup_count: 保留的日志文件数量
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    fmt = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
    date_fmt = "%Y-%m-%d %H:%M:%S"

    # 控制台 handler（彩色）
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(ColorFormatter(fmt, date_fmt))
    logger.addHandler(console_handler)

    # 文件 handler（轮转）
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
    )
    file_handler.setFormatter(logging.Formatter(fmt, date_fmt))
    logger.addHandler(file_handler)

    return logger
