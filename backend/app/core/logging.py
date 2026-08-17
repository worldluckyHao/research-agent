import logging


def setup_logging(
    level: str = "INFO",
) -> None:
    """
    初始化 Research Agent 的全局日志系统。

    参数
    ----------
    level:
        日志级别字符串，例如：

        DEBUG
        INFO
        WARNING
        ERROR
        CRITICAL

    这个值现在由：

        backend/.env

    中的：

        LOG_LEVEL

    提供。

    调用链：

        backend/.env
            ↓
        settings.LOG_LEVEL
            ↓
        main.py
            ↓
        setup_logging(level=...)
    """

    # ========================================================
    # 1. 把字符串日志等级转换成 logging 内部数字等级
    # ========================================================
    #
    # 例如：
    #
    # "DEBUG"
    #
    # 转换成：
    #
    # logging.DEBUG
    #
    # 如果传入了一个无法识别的值，
    # 例如：
    #
    # LOG_LEVEL=ABC
    #
    # 那么默认退回：
    #
    # logging.INFO
    #
    numeric_level = getattr(
        logging,
        level.upper(),
        logging.INFO,
    )


    # ========================================================
    # 2. 配置 Python 全局日志
    # ========================================================
    #
    # 最终输出可能类似：
    #
    # 2026-08-17 14:50:00,123 |
    # INFO |
    # backend.app.services.paper_service |
    # Paper created: id=1
    #
    logging.basicConfig(
        level=numeric_level,
        format=(
            "%(asctime)s | "
            "%(levelname)s | "
            "%(name)s | "
            "%(message)s"
        ),
    )