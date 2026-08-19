import logging

from fastapi import Request
from fastapi.responses import JSONResponse


# ============================================================
# 当前模块的日志对象
# ============================================================
#
# __name__ 会自动变成：
#
# backend.app.core.exceptions
#
# 以后日志输出时，就知道是哪一个模块产生的日志。
logger = logging.getLogger(__name__)


# ============================================================
# 业务异常基类
# ============================================================

class AppException(Exception):
    """
    Research Agent 项目所有“业务异常”的基类。

    例如：

    PaperNotFoundException
    PaperDOIExistsException
    EmptyUpdateException

    都继承自 AppException。

    参数说明：
    ----------
    code:
        给前端程序使用的错误代码，例如：
        PAPER_NOT_FOUND

    message:
        给用户看的错误信息，例如：
        Paper not found

    status_code:
        HTTP 状态码，例如：
        404
        409
        400
    """

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code

        # 调用 Python Exception 的初始化方法，
        # 这样 traceback 中也能正确显示 message。
        super().__init__(message)


# ============================================================
# Paper 不存在
# ============================================================

class PaperNotFoundException(AppException):
    """
    当用户访问一个不存在的 Paper 时抛出。

    例如：

    GET /api/v1/papers/999999
    """

    def __init__(self):
        super().__init__(
            code="PAPER_NOT_FOUND",
            message="Paper not found",
            status_code=404,
        )

class ProjectNotFoundException(AppException):
    """
    当前用户访问的研究项目不存在。

    这里既可能是真的不存在，
    也可能是该项目不属于当前用户。
    """

    def __init__(self):
        super().__init__(
            code="PROJECT_NOT_FOUND",
            message="Project not found",
            status_code=404,
        )


# ============================================================
# DOI 重复
# ============================================================

class PaperDOIExistsException(AppException):
    """
    当创建或修改 Paper 时，
    DOI 已经存在于数据库中时抛出。

    HTTP 409 Conflict 表示：

    请求本身可能没有格式问题，
    但是和数据库当前资源状态冲突。
    """

    def __init__(self):
        super().__init__(
            code="PAPER_DOI_EXISTS",
            message="Paper with this DOI already exists",
            status_code=409,
        )


# ============================================================
# PATCH 请求为空
# ============================================================

class EmptyUpdateException(AppException):
    """
    当 PATCH 请求没有提交任何修改字段时抛出。

    例如：

    PATCH /api/v1/papers/1

    Body:

    {}
    """

    def __init__(self):
        super().__init__(
            code="EMPTY_UPDATE",
            message="No fields provided for update",
            status_code=400,
        )


# ============================================================
# Username 已存在
# ============================================================

class UsernameAlreadyExistsException(AppException):
    """
    用户注册时 username 已经被其他账号使用。
    """

    def __init__(self):
        super().__init__(
            code="USERNAME_ALREADY_EXISTS",
            message="Username already exists",
            status_code=409,
        )


# ============================================================
# Email 已存在
# ============================================================

class EmailAlreadyExistsException(AppException):
    """
    用户注册时 email 已经被其他账号使用。
    """

    def __init__(self):
        super().__init__(
            code="EMAIL_ALREADY_EXISTS",
            message="Email already exists",
            status_code=409,
        )

# ============================================================
# 登录凭据错误
# ============================================================

class InvalidCredentialsException(AppException):
    """
    用户登录失败。

    例如：

    - username 不存在
    - password 错误
    - JWT 无效
    - JWT 已过期

    对客户端统一返回 401。
    """

    def __init__(self):
        super().__init__(
            code="INVALID_CREDENTIALS",
            message="Could not validate credentials",
            status_code=401,
        )


# ============================================================
# 用户账号已禁用
# ============================================================

class InactiveUserException(AppException):
    """
    用户存在，但：

        is_active = False

    不允许继续访问受保护资源。
    """

    def __init__(self):
        super().__init__(
            code="INACTIVE_USER",
            message="Inactive user",
            status_code=403,
        )

class ProjectNotFoundException(AppException):
    """ResearchProject 不存在。"""

    def __init__(self):
        super().__init__(
            code="PROJECT_NOT_FOUND",
            message="Research project not found",
            status_code=404,
        )


class ProjectAccessDeniedException(AppException):
    """当前用户不是项目 owner。"""

    def __init__(self):
        super().__init__(
            code="PROJECT_ACCESS_DENIED",
            message="You do not have permission to access this project",
            status_code=403,
        )


class ProjectPaperAlreadyExistsException(AppException):
    """Paper 已经存在于该项目。"""

    def __init__(self):
        super().__init__(
            code="PROJECT_PAPER_ALREADY_EXISTS",
            message="Paper already exists in this project",
            status_code=409,
        )


class ProjectPaperNotFoundException(AppException):
    """Paper 不在该项目中。"""

    def __init__(self):
        super().__init__(
            code="PROJECT_PAPER_NOT_FOUND",
            message="Paper is not in this project",
            status_code=404,
        )

# ============================================================
# 统一业务异常 Handler
# ============================================================

async def app_exception_handler(
    request: Request,
    exc: AppException,
):
    """
    FastAPI 统一处理 AppException。

    例如：

    raise PaperNotFoundException()

    会进入这里，并最终返回：

    {
        "code": "PAPER_NOT_FOUND",
        "message": "Paper not found"
    }

    HTTP 状态码为 404。
    """

    # 业务错误通常不是系统崩溃，
    # 因此这里记录 WARNING 即可。
    logger.warning(
        "Application error: code=%s method=%s path=%s",
        exc.code,
        request.method,
        request.url.path,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.code,
            "message": exc.message,
        },
    )


# ============================================================
# 未知异常兜底 Handler
# ============================================================

async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
):
    """
    处理所有没有被业务异常系统捕获的未知错误。

    例如：

    - AttributeError
    - RuntimeError
    - 数据库突然断开
    - 程序 Bug
    - 其他未知 Exception

    注意：

    详细错误只写到服务器日志。

    不要把 str(exc) 直接返回给客户端，
    否则可能泄露：

    - SQL
    - 数据库结构
    - 文件路径
    - 内部代码信息
    """

    # logger.exception() 会自动记录完整 traceback。
    logger.exception(
        "Unhandled exception: method=%s path=%s",
        request.method,
        request.url.path,
    )

    # 客户端只看到统一、安全的错误。
    return JSONResponse(
        status_code=500,
        content={
            "code": "INTERNAL_SERVER_ERROR",
            "message": "Internal server error",
        },
    )