"""Minimal platform tenant provisioning for the shared CE/SaaS API."""

from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, Field
from tortoise.transactions import in_transaction

from ..apps.ctx import CTX_USER_ID
from ..apps.dependency import permission_required
from ..biz.db.models import PlatformAuditLog, PlatformTenant, Role, User, UserRole
from ..utils.password import get_password_hash

router = APIRouter(tags=["platform-tenants"])


class TenantCreateIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    slug: str = Field(..., min_length=2, max_length=64)
    admin_email: EmailStr
    admin_password: str = Field(..., min_length=10, max_length=128)


@router.get("/platform/tenants")
async def list_platform_tenants(
    _user: User = permission_required("platform:tenant:read"),
):
    tenants = await PlatformTenant.exclude(status="archived").order_by("name")
    return {
        "items": [
            {
                "id": tenant.id,
                "name": tenant.name,
                "slug": tenant.slug,
                "status": tenant.status,
                "created_at": tenant.created_at,
            }
            for tenant in tenants
        ],
        "total": len(tenants),
    }


@router.post("/platform/tenants", status_code=201)
async def create_platform_tenant(
    payload: TenantCreateIn,
    user: User = permission_required("platform:tenant:write"),
):
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,63}", payload.slug):
        raise HTTPException(
            status_code=400,
            detail="租户标识只允许小写字母、数字和短横线",
        )
    if await PlatformTenant.filter(slug=payload.slug).exists():
        raise HTTPException(status_code=409, detail="租户标识已存在")
    if await User.filter(email=str(payload.admin_email)).exists():
        raise HTTPException(status_code=409, detail="租户管理员邮箱已存在")

    admin_role = await Role.filter(scope="admin", name="admin").first()
    if admin_role is None:
        raise HTTPException(status_code=503, detail="租户管理员角色尚未初始化")

    async with in_transaction():
        tenant = await PlatformTenant.create(
            name=payload.name.strip(), slug=payload.slug, status="active",
        )
        admin = await User.create(
            email=str(payload.admin_email),
            password=get_password_hash(payload.admin_password),
            is_active=True,
            is_verified=True,
        )
        await UserRole.create(
            user_id=admin.id,
            role_id=admin_role.id,
            tenant_id=tenant.slug,
            granted_by=int(CTX_USER_ID.get()) if CTX_USER_ID.get() else None,
        )
        await PlatformAuditLog.create(
            actor_id=int(CTX_USER_ID.get()) if CTX_USER_ID.get() else None,
            action="platform.tenant.create",
            tenant_id=tenant.slug,
            resource_type="tenant",
            resource_id=tenant.slug,
            detail={"name": tenant.name, "admin_user_id": admin.id},
        )

    return {
        "id": tenant.id,
        "name": tenant.name,
        "slug": tenant.slug,
        "admin_user_id": admin.id,
        "admin_email": admin.email,
        "status": tenant.status,
    }


@router.delete("/platform/tenants/{slug}")
async def delete_platform_tenant(
    slug: str,
    user: User = permission_required("platform:tenant:write"),
):
    tenant = await PlatformTenant.filter(slug=slug).first()
    if tenant is None or tenant.status == "archived":
        raise HTTPException(status_code=404, detail="租户不存在")
    bindings = await UserRole.filter(tenant_id=slug)
    user_ids = {row.user_id for row in bindings}
    async with in_transaction():
        tenant.status = "archived"
        await tenant.save(update_fields=["status", "updated_at"])
        await UserRole.filter(tenant_id=slug).delete()
        if user_ids:
            await User.filter(id__in=user_ids).update(
                is_active=False,
                deleted_at=tenant.updated_at,
            )
        await PlatformAuditLog.create(
            actor_id=user.id,
            action="platform.tenant.delete",
            tenant_id=slug,
            resource_type="tenant",
            resource_id=slug,
            detail={"name": tenant.name, "affected_users": len(user_ids)},
        )
    return {"message": "租户已删除", "slug": slug}
