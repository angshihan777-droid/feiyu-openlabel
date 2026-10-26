import traceback

from fastapi import FastAPI
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Request, Response, HTTPException, status, Depends
from fastapi.responses import ORJSONResponse, JSONResponse

from feiyu_app.exceptions import (
    DoesNotExist,
    HTTPException,
    IntegrityError,
    RequestValidationError,
    ResponseValidationError,
)
from feiyu_app.config import settings
from ..log import logger
from ..exceptions import BizException

# from .taxonomy_app import app as taxonomy_app
from .openpgl_app import app as openlabel
from .system_app import app as system_app
from .auth import router as auth_app
from .projects import router as projects_app
from .taxonomies import router as taxonomies_app
from .labels import router as labels_app
from .batches import router as batches_app
from .challenge import router as challenge_app
from .me import router as me_app
from .audit import router as audit_app
from .notifications import router as notifications_app
from .platform_tenants import router as platform_tenants_app

# Stage 5 联调:把 admin/captcha/platform 三个独立 FastAPI app 的路由合并进主 app,
# 这样 uvicorn 单进程 8423 就能服务所有 /api/v1/{a,b,c,p}/* 前缀。
from ..admin.main import api_router as admin_api_router
from ..captcha.api import api_router as captcha_router
from ..captcha.email_code import api_router as email_code_router
from ..captcha.mobile_short_msg import api_router as mobile_short_msg_router

# 版本门控:ce < ee < saas
from ..edition import HAS_EE, HAS_SAAS

if HAS_EE:
    from ..ee.platform.auth import router as platform_auth_router
    from ..ee.platform.audit_route import router as platform_audit_router
    from ..ee.platform.audit_middleware import HttpAuditLogMiddleware
    from ..ee.platform.sso.oidc import router as sso_oidc_router
    from ..ee.platform.sso.ldap_login import router as sso_ldap_router
    from ..ee.platform.backup.routes import router as platform_backup_router
    EE_ROUTERS = [
        platform_auth_router,
        platform_audit_router,
        sso_oidc_router,
        sso_ldap_router,
        platform_backup_router,
    ]

if HAS_SAAS:
    from ..saas.platform.tenants import router as platform_tenants_router
    from ..saas.platform.users import router as platform_users_router
    from ..saas.platform.feature_flags import router as platform_feature_flags_router
    from ..saas.platform.flow import router as platform_flow_router
    from ..saas.platform.func import router as platform_func_router
    from ..saas.platform.models import router as platform_models_router
    from ..saas.platform.usage.middleware import QuotaMiddleware
    from ..saas.platform.billing.stripe_webhook import router as stripe_webhook_router
    from ..saas.platform.billing.routes import router as platform_billing_mgmt_router
    from ..saas.platform.signup.routes import router as platform_signup_router
    from ..saas.platform.ops_dashboard.routes import router as platform_ops_dashboard_router
    SAAS_ROUTERS = [
        platform_tenants_router, platform_users_router,
        platform_feature_flags_router, platform_flow_router,
        platform_func_router, platform_models_router,
        stripe_webhook_router, platform_billing_mgmt_router,
        platform_signup_router, platform_ops_dashboard_router,
    ]

def register_routers(app: FastAPI):
    # 登录后才能访问
    # app.include_router(taxonomy_app, prefix="/taxonomy")
    app.include_router(openlabel, prefix="/openlabel")
    app.include_router(system_app, prefix="/system")
    # Stage 4 新增:租户感知的项目 / 标签集 路由
    app.include_router(projects_app, prefix="/projects")
    app.include_router(taxonomies_app, prefix="/taxonomies")
    # Stage 6:unit label 写入(对接工作流)
    app.include_router(labels_app, prefix="/labels")
    # Stage 7:Batch + Unit 调度(router 内含完整 path:/projects/{pid}/batches|units、/batches/{id}、/units/{id}/*)
    app.include_router(batches_app)
    # Challenge-specific role-separated annotation workflow. Existing API
    # namespaces stay intact; these routes are additive.
    app.include_router(challenge_app)
    # Stage 8:业务面剩余路由
    app.include_router(me_app, prefix="/me")
    # Stage 9.7:租户审计日志(管理面 AuditLog 视图)
    app.include_router(audit_app, prefix="/audit-logs")
    # Stage 12:实时通知(SSE + REST)
    app.include_router(notifications_app, prefix="/notifications")
    # Keep the core tenant-provisioning surface available in CE as well.
    app.include_router(platform_tenants_app, prefix="/api/v1/p")
    
    # 无需登录即可访问
    app.include_router(auth_app, prefix="/u/a/noau")

    # === admin/captcha/platform 路由合并(单进程 8423) ===
    # admin app 自己的 api_router 已经带 /api/v1/a 前缀,这里直接挂
    app.include_router(admin_api_router)
    # captcha 三个 router 原本挂在 /captcha /emailcode /mobilecode,这里加 /api/v1/c 外层前缀
    app.include_router(captcha_router, prefix="/api/v1/c")
    app.include_router(email_code_router, prefix="/api/v1/c")
    app.include_router(mobile_short_msg_router, prefix="/api/v1/c")
    # platform routers 原本在 platform/main.py 里挂在 /api/v1/p 下,这里同样处理。
    # ce edition 下不挂载,整段 /api/v1/p/* 直接 404。
    if HAS_EE:
        for r in EE_ROUTERS:
            app.include_router(r, prefix="/api/v1/p")
    if HAS_SAAS:
        for r in SAAS_ROUTERS:
            app.include_router(r, prefix="/api/v1/p")

async def all_exception_handler(request: Request, exc: Exception) -> Response:
    logger.exception(exc)
    logger.error("---------------")
    return JSONResponse(
        status_code=500,
        content={"message": "服务端程序异常"},
    )
def make_middlewares():
    middleware = [
        Middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins_list,
            allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
            allow_methods=settings.cors_methods_list,
            allow_headers=settings.cors_headers_list,
        ),
    ]
    if HAS_EE:
        # EE 增量:HTTP 全局审计中间件,记录所有 mutation 请求到业务 AuditLog。
        # fire-and-forget,不影响响应延迟。
        middleware.append(
            Middleware(HttpAuditLogMiddleware)
        )
    if HAS_SAAS:
        # SaaS 增量:按 tenant 维度 API 配额中间件,Redis pipeline + 本地缓存。
        middleware.append(
            Middleware(QuotaMiddleware)
        )
    return middleware


async def DoesNotExistHandle(req: Request, exc: DoesNotExist) -> JSONResponse:
    content = dict(
        status=404,
        statusText=f"Object has not found, exc: {exc}, query_params: {req.query_params}",
    )
    return JSONResponse(content=content, status_code=404)


async def IntegrityHandle(_: Request, exc: IntegrityError) -> JSONResponse:
    content = dict(
        status=500,
        statusText=f"IntegrityError，{exc}",
    )
    logger.error(exc)
    traceback.print_exception(exc)
    return JSONResponse(content=content, status_code=500)


async def HttpExcHandle(_: Request, exc: HTTPException) -> JSONResponse:
    logger.error(exc)
    traceback.print_exception(exc)
    content = dict(status=exc.status_code, statusText=exc.detail, data=None)
    return JSONResponse(content=content, status_code=exc.status_code)


async def RequestValidationHandle(_: Request, exc: RequestValidationError) -> JSONResponse:
    logger.error(exc)
    traceback.print_exception(exc)
    content = dict(status=422, statusText=f"RequestValidationError, {exc}")
    return JSONResponse(content=content, status_code=422)


async def ResponseValidationHandle(_: Request, exc: ResponseValidationError) -> JSONResponse:
    logger.error(exc)
    traceback.print_exception(exc)
    content = dict(status=500, statusText=f"ResponseValidationError, {exc}")
    return JSONResponse(content=content, status_code=500)

async def BizException_handler(request: Request, exc: BizException) -> Response:
    logger.error(exc)
    traceback.print_exception(exc)
    return JSONResponse(
        content={"status": exc.status, "statusText": exc.statusText},
    )
    
def register_exceptions(app: FastAPI):
    app.add_exception_handler(DoesNotExist, DoesNotExistHandle)
    app.add_exception_handler(HTTPException, HttpExcHandle)
    app.add_exception_handler(IntegrityError, IntegrityHandle)
    app.add_exception_handler(RequestValidationError, RequestValidationHandle)
    app.add_exception_handler(ResponseValidationError, ResponseValidationHandle)
    app.add_exception_handler(BizException, BizException_handler)
    app.add_exception_handler(Exception, all_exception_handler)
