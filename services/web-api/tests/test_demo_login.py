import json
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from fastapi import HTTPException
from tortoise import Tortoise

from feiyu_app.apps import auth
from feiyu_app.biz.db.models import Role, User, UserRole
from feiyu_app.biz.services.audit import audit_service
from feiyu_app.biz.services.user import user_service
from feiyu_app.config import settings


TEST_DB = {
    "connections": {"default": "sqlite://:memory:"},
    "apps": {
        "models": {
            "models": ["feiyu_app.biz.db.models"],
            "default_connection": "default",
        }
    },
    "use_tz": False,
    "timezone": "Asia/Shanghai",
}


@pytest_asyncio.fixture(autouse=True)
async def database():
    await Tortoise.init(config=TEST_DB)
    await Tortoise.generate_schemas()
    yield
    await Tortoise.close_connections()


@pytest.mark.asyncio
async def test_demo_login_status_is_disabled_by_default(monkeypatch):
    monkeypatch.setattr(settings, "DEMO_QUICK_LOGIN", False)

    response = await auth.demo_login_status()
    payload = json.loads(response.body)

    assert response.status_code == 200
    assert payload["data"] == {"enabled": False}


@pytest.mark.asyncio
async def test_demo_login_rejects_unknown_identity_when_disabled(monkeypatch):
    monkeypatch.setattr(settings, "DEMO_QUICK_LOGIN", False)

    with pytest.raises(HTTPException) as exc:
        await auth.demo_login("annotator", redis=AsyncMock())

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_demo_login_issues_real_jwt_for_role(monkeypatch):
    monkeypatch.setattr(settings, "DEMO_QUICK_LOGIN", True)
    monkeypatch.setattr(settings, "DEMO_ACCOUNT_DOMAIN", "demo.test")
    monkeypatch.setattr(user_service, "update_last_login", AsyncMock())
    monkeypatch.setattr(audit_service, "log", AsyncMock())

    user = await User.create(
        email="avery.annotator@demo.test",
        password="x",
        is_active=True,
    )
    role = await Role.create(
        name="annotator",
        scope="business",
        tenant_id="test",
        is_system=False,
        is_builtin=False,
    )
    await UserRole.create(user_id=user.id, role_id=role.id, tenant_id="test")

    response = await auth.demo_login("annotator", redis=AsyncMock())
    payload = json.loads(response.body)

    assert response.status_code == 200
    assert payload["data"]["access_token"]
    assert payload["data"]["refresh_token"]
    assert payload["data"]["user_name"] == "avery.annotator@demo.test"
