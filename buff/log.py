"""日志配置模块"""

import logging

logger = logging.getLogger("buff")


def setup_logging(verbose: bool = False, quiet: bool = False) -> logging.Logger:
    """配置 buff 包的全局日志

    Args:
        verbose: 启用 DEBUG 级别
        quiet:   仅显示 WARNING 及以上
    """
    if verbose:
        level = logging.DEBUG
    elif quiet:
        level = logging.WARNING
    else:
        level = logging.INFO

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    ))

    logger.setLevel(level)
    logger.handlers.clear()
    logger.addHandler(handler)
    return logger
