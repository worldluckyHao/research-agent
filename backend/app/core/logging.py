import logging


def setup_logging(
    debug: bool = False,
) -> None:
    """
    初始化 Research Agent 的 Python 日志系统。

    debug=True:
        日志级别使用 DEBUG。

    debug=False:
        日志级别使用 INFO。

    当前 Day9 阶段：
    日志直接输出到控制台。

    后面如果项目部署到服务器，
    可以进一步加入：

    - 文件日志
    - RotatingFileHandler
    - Docker stdout
    - 日志收集平台
    """

    # ========================================================
    # 根据 DEBUG 配置决定日志级别
    # ========================================================

    if debug:
        level = logging.DEBUG
    else:
        level = logging.INFO

    # ========================================================
    # 配置全局日志格式
    # ========================================================

    logging.basicConfig(
        level=level,

        # 日志格式示例：
        #
        # 2026-08-17 13:20:00,123 |
        # INFO |
        # backend.app.services.paper_service |
        # Paper created: id=1
        format=(
            "%(asctime)s | "
            "%(levelname)s | "
            "%(name)s | "
            "%(message)s"
        ),
    )