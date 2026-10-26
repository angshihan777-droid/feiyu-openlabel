"""最小冒烟测试:确认 FastAPI app 能在当前 FY_EDITION 下正确装配。
不连接外部服务(lifespan 未触发),只覆盖 router 注册阶段。
"""
import os
import pytest


def _route_paths(app) -> set:
    paths = set()

    def collect(routes):
        for r in routes:
            # fastapi>=0.141 include_router 包装成 _IncludedRouter(无 .path/.routes),
            # 真实路径在 effective_candidates() 里(带 include prefix)
            if hasattr(r, "effective_candidates"):
                collect(r.effective_candidates())
            elif hasattr(r, "original_router"):
                collect(r.original_router.routes)
            elif hasattr(r, "routes"):
                collect(r.routes)
            if getattr(r, "path", ""):
                paths.add(r.path)

    collect(app.routes)
    return paths


def test_app_assembles_under_current_edition():
    """三档 edition 下 app 都应当能装配;此处只断言业务面路由始终存在。"""
    from feiyu_app.app import app

    paths = _route_paths(app)
    assert "/units/my-tasks" in paths, "challenge annotator route missing"
    assert "/units/my-reviews" in paths, "challenge reviewer route missing"
    assert "/stats/daily-duration" in paths, "challenge stats route missing"
    assert any(p.startswith("/workflows") for p in paths) is False
    assert len(app.routes) > 0


def test_challenge_routes_are_additive_and_core_contracts_remain():
    from feiyu_app.app import app

    paths = set(app.openapi()["paths"])
    required = {
        "/units/my-tasks",
        "/units/my-reviews",
        "/units/{unit_id}",
        "/units/{unit_id}/submit",
        "/units/{unit_id}/approve",
        "/units/{unit_id}/reject",
        "/units/{unit_id}/force-approve",
        "/units/{unit_id}/reassign",
        "/units/{unit_id}/mark-difficult",
        "/stats/daily-duration",
        "/stats/export",
        "/media/upload",
        "/media",
        "/media/{media_id}/stream",
        "/tenant-admin/overview",
        "/tenant-admin/members",
        "/tenant-admin/reviews",
        "/tenant-admin/video-results/{kind}",
        "/tenant-admin/export/{kind}.csv",
        "/tenant-admin/annotation-settings",
        "/projects/{project_id}/video-config",
        "/units/{unit_id}/return-video",
        "/units/{unit_id}/admin-review",
        "/api/v1/p/platform/tenants",
        "/api/v1/p/platform/tenants/{slug}",
        "/u/a/noau/demo-login/status",
        "/u/a/noau/demo-login/{identity}",
        "/labels/units/{unit_id}",
        "/projects/{project_id}/batches",
        "/batches/{batch_id}",
    }
    assert required <= paths
    assert "/anno-job/perform" not in paths
    assert "/statistics/my" not in paths
    assert not any(path.startswith("/workflows") for path in paths)


@pytest.mark.ce
def test_ce_exposes_core_platform_tenant_routes():
    """Core tenant provisioning is available in CE."""
    if os.getenv("FY_EDITION", "ce") != "ce":
        pytest.skip("only applicable to CE edition")
    from feiyu_app.app import app

    paths = _route_paths(app)
    assert "/api/v1/p/platform/tenants" in paths


@pytest.mark.ee
def test_ee_routes_partial_when_ee():
    """EE edition 应挂载平台账号 + 审计查询路由,但不应有租户/计费等 SaaS 路由。

    EE 留:auth, audit_route(PlatformAuthControl + 审计查询)
    SaaS 迁走:tenants, users, feature_flags, flow, func, models
    """
    if os.getenv("FY_EDITION", "ce") != "ee":
        pytest.skip("only applicable to EE edition")
    from feiyu_app.app import app

    paths = _route_paths(app)
    # EE 应该有平台登录入口
    assert any("/api/v1/p/" in p and "auth" in p for p in paths), \
        "EE should mount /api/v1/p/auth/*"
    # EE 不应该有租户 CRUD
    assert not any(p.startswith("/api/v1/p/tenants") for p in paths), \
        "EE should NOT mount /api/v1/p/tenants (SaaS-only)"


@pytest.mark.saas
def test_saas_routes_full_when_saas():
    """SaaS edition 应挂载全部平台路由(EE 基础设施 + SaaS 多租户运营)。"""
    if os.getenv("FY_EDITION", "ce") != "saas":
        pytest.skip("only applicable to SaaS edition")
    from feiyu_app.app import app

    paths = _route_paths(app)
    # SaaS 应该有租户 CRUD
    assert any(p.startswith("/api/v1/p/tenants") for p in paths), \
        "SaaS should mount /api/v1/p/tenants"
    # SaaS 也应该继承 EE 的平台登录
    assert any("/api/v1/p/" in p and "auth" in p for p in paths), \
        "SaaS should also mount /api/v1/p/auth/* (inherited from EE)"
