"""Shared challenge workflow helpers and trust-boundary checks."""

from __future__ import annotations

from typing import Iterable

from fastapi import HTTPException

from ..db.models import MediaFile, Role, Unit, User, UserRole
from ..rbac.resolver import get_user_role_names
from ..services.label_v2 import LabelNotFound, label_service
from ...config import settings
from ...log import logger
from .domain import extract_intervals


class ChallengeError(Exception):
    """Business-rule error converted to HTTP by the router."""


def display_name(user: User | None) -> str:
    if user is None:
        return "未知用户"
    return user.email or user.mobile_phone_no or f"user-{user.id}"


async def has_role(user: User, *allowed: str) -> bool:
    if user.is_superuser:
        return True
    roles = await get_user_role_names(user)
    return bool(roles & set(allowed))


async def has_tenant_role(user: User, tenant_id: str, *allowed: str) -> bool:
    if user.is_superuser:
        return True
    bindings = await UserRole.filter(user_id=user.id, tenant_id=tenant_id)
    if not bindings:
        return False
    roles = await Role.filter(
        id__in=[binding.role_id for binding in bindings],
        scope__in=["admin", "business"],
    )
    accepted = set(allowed)
    if "tenant-admin" in accepted or "admin" in accepted:
        accepted.update({"admin", "tenant-admin"})
    return any(role.name in accepted for role in roles)


async def require_tenant_role(user: User, tenant_id: str, *allowed: str) -> None:
    if not await has_tenant_role(user, tenant_id, *allowed):
        raise HTTPException(
            status_code=403,
            detail=f"当前租户不具备角色:{', '.join(allowed)}",
        )


async def require_role(user: User, *allowed: str) -> None:
    if not await has_role(user, *allowed):
        raise HTTPException(
            status_code=403,
            detail=f"当前用户不具备角色:{', '.join(allowed)}",
        )


async def get_tenant_unit(*, tenant_id: str, unit_id: int) -> Unit:
    unit = await Unit.filter(tenant_id=tenant_id, id=unit_id).first()
    if unit is None:
        # Same response for missing and cross-tenant records avoids ID probing.
        raise HTTPException(status_code=404, detail=f"unit {unit_id} 不存在")
    return unit


async def media_map(units: Iterable[Unit]) -> dict[int, MediaFile]:
    media_ids = []
    for unit in units:
        if unit.seq.startswith("media:"):
            try:
                media_ids.append(int(unit.seq.split(":", 1)[1]))
            except (ValueError, IndexError):
                continue
    if not media_ids:
        return {}
    rows = await MediaFile.filter(id__in=media_ids)
    return {row.id: row for row in rows}


def media_id(unit: Unit) -> int | None:
    if not unit.seq.startswith("media:"):
        return None
    try:
        return int(unit.seq.split(":", 1)[1])
    except (ValueError, IndexError):
        return None


async def latest_intervals(unit: Unit) -> tuple[list[dict], int]:
    try:
        label = await label_service.get_label(unit_id=unit.id)
    except LabelNotFound:
        return [], 0
    return extract_intervals(label.objects), label.version


async def refill_demo_workbench(tenant_id: str) -> None:
    """Keep the local test tenant demonstrable without affecting real tenants."""
    if not settings.DEMO_QUICK_LOGIN or tenant_id != "test":
        return
    try:
        from ..dev_seed import ensure_demo_workbench_tasks

        await ensure_demo_workbench_tasks(tenant_id)
    except Exception:
        # Demo replenishment must never make the real work queue unavailable.
        logger.exception("failed to replenish demo workbench tasks")
