"""Tenant administration, project rules, and generated worker accounts."""

from __future__ import annotations

import secrets
import string
from collections import defaultdict
from datetime import datetime

from fastapi import HTTPException
from tortoise.expressions import Q

from ..db.models import (
    Batch,
    PlatformTenant,
    Project,
    Role,
    Unit,
    User,
    UserRole,
)
from ..services.user import user_service
from ...config import settings
from ...dto.users import UserCreate
from .common import display_name, require_tenant_role


DEFAULT_ANNOTATION_SETTINGS = {
    "instructions": "",
    "require_label": True,
    "min_interval_seconds": 0.1,
}

DEFAULT_RETURN_REASONS = [
    {"code": "blur", "label": "视频模糊"},
    {"code": "occluded", "label": "画面遮挡"},
    {"code": "blank", "label": "黑屏或空画面"},
    {"code": "incomplete", "label": "视频内容不完整"},
    {"code": "fps", "label": "帧率异常"},
    {"code": "no_action", "label": "没有可标注动作"},
    {"code": "other", "label": "其他原因"},
]


def normalize_annotation_settings(value: dict | None) -> dict:
    settings_value = value if isinstance(value, dict) else {}
    result = {
        **DEFAULT_ANNOTATION_SETTINGS,
        **(settings_value.get("annotation_defaults") or {}),
    }
    result["instructions"] = str(result.get("instructions") or "").strip()
    result["require_label"] = bool(result.get("require_label", True))
    result["min_interval_seconds"] = float(
        result.get("min_interval_seconds", 0.1)
    )
    return result


async def get_tenant_annotation_settings(tenant_id: str) -> dict:
    tenant = await PlatformTenant.filter(slug=tenant_id).first()
    return normalize_annotation_settings(tenant.settings if tenant else None)


def normalize_video_config(
    value: dict | None,
    fallback: dict | None = None,
) -> dict:
    base = normalize_annotation_settings(fallback)
    settings_value = value if isinstance(value, dict) else {}
    labels = [
        str(label).strip()
        for label in settings_value.get("labels", [])
        if str(label).strip()
    ]
    reasons = []
    for item in settings_value.get("return_reasons", DEFAULT_RETURN_REASONS):
        if isinstance(item, str) and item.strip():
            reasons.append({"code": item.strip(), "label": item.strip()})
        elif isinstance(item, dict) and item.get("label"):
            reasons.append({
                "code": str(item.get("code") or item["label"]).strip(),
                "label": str(item["label"]).strip(),
            })
    if not reasons:
        reasons = [dict(item) for item in DEFAULT_RETURN_REASONS]
    label_mode = settings_value.get("label_mode", "free")
    if label_mode not in {"preset", "free"}:
        label_mode = "free"
    return {
        **base,
        "instructions": str(
            settings_value.get("instructions", base["instructions"]) or ""
        ).strip(),
        "require_label": bool(
            settings_value.get("require_label", base["require_label"])
        ),
        "min_interval_seconds": float(
            settings_value.get("min_interval_seconds", base["min_interval_seconds"])
        ),
        "label_mode": label_mode,
        "labels": labels if label_mode == "preset" else [],
        "label_template": str(settings_value.get("label_template") or ""),
        "fps": max(1.0, float(settings_value.get("fps", 30.0))),
        "return_reasons": reasons,
    }


async def get_project_video_config(*, tenant_id: str, project_id: int) -> dict:
    project = await Project.filter(tenant_id=tenant_id, id=project_id).first()
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    fallback = await get_tenant_annotation_settings(tenant_id)
    return normalize_video_config(
        (project.settings or {}).get("video_annotation"),
        fallback,
    )


async def update_project_video_config(
    *,
    tenant_id: str,
    project_id: int,
    user: User,
    value: dict,
) -> dict:
    await require_tenant_role(user, tenant_id, "admin", "tenant-admin")
    project = await Project.filter(tenant_id=tenant_id, id=project_id).first()
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    normalized = normalize_video_config(value)
    if normalized["label_mode"] == "preset" and not normalized["labels"]:
        raise HTTPException(status_code=400, detail="预设标签模式至少需要一个标签")
    if len(normalized["labels"]) > 200:
        raise HTTPException(status_code=400, detail="项目标签不能超过 200 个")
    settings_value = dict(project.settings or {})
    settings_value["video_annotation"] = normalized
    project.settings = settings_value
    await project.save(update_fields=["settings", "updated_at"])
    return normalized


async def _tenant_role_rows(
    tenant_id: str, *names: str,
) -> tuple[list[Role], list[UserRole]]:
    roles = await Role.filter(
        scope="business", name__in=list(names),
    ).filter(Q(tenant_id=tenant_id) | Q(tenant_id__isnull=True))
    bindings = await UserRole.filter(
        tenant_id=tenant_id, role_id__in=[role.id for role in roles],
    )
    return roles, bindings


async def tenant_role_user_count(tenant_id: str, role_name: str) -> int:
    roles, bindings = await _tenant_role_rows(tenant_id, role_name)
    user_ids = {binding.user_id for binding in bindings}
    return await User.filter(
        id__in=user_ids, is_active=True, deleted_at__isnull=True,
    ).count() if roles and user_ids else 0


async def tenant_admin_overview(*, tenant_id: str, user: User) -> dict:
    await require_tenant_role(user, tenant_id, "admin")
    units = await Unit.filter(tenant_id=tenant_id)
    status_counts: dict[str, int] = defaultdict(int)
    for unit in units:
        status_counts[unit.status] += 1
    total = len(units)
    approved = sum(unit.status == "approved" for unit in units)
    completed = sum(
        unit.status in {"approved", "difficult_sample"} for unit in units
    )
    reviewed = sum(
        unit.status in {
            "under_review", "rejected", "approved", "escalated",
            "difficult_sample",
        }
        for unit in units
    )
    return {
        "total_tasks": total,
        "completed_tasks": completed,
        "completion_rate": completed / total if total else 0.0,
        "reviewed_tasks": reviewed,
        "approved_tasks": approved,
        "approval_rate": approved / reviewed if reviewed else 0.0,
        "batch_count": await Batch.filter(tenant_id=tenant_id).count(),
        "active_annotators": await tenant_role_user_count(
            tenant_id, "annotator",
        ),
        "active_reviewers": await tenant_role_user_count(
            tenant_id, "reviewer",
        ),
        "returned_tasks": sum(
            unit.status in {"returned", "source_confirmed", "void"}
            for unit in units
        ),
        "problem_tasks": sum(
            unit.status in {
                "returned", "rejected", "escalated",
                "source_confirmed", "void", "difficult_sample",
            }
            for unit in units
        ),
        "status_counts": dict(status_counts),
    }


async def tenant_admin_members(*, tenant_id: str, user: User) -> dict:
    await require_tenant_role(user, tenant_id, "admin")
    roles, bindings = await _tenant_role_rows(
        tenant_id, "annotator", "reviewer",
    )
    role_names = {role.id: role.name for role in roles}
    roles_by_user: dict[int, set[str]] = defaultdict(set)
    for binding in bindings:
        roles_by_user[binding.user_id].add(role_names[binding.role_id])
    users = await User.filter(
        id__in=list(roles_by_user), deleted_at__isnull=True,
    ).order_by("id")
    return {
        "items": [
            {
                "id": row.id,
                "name": display_name(row),
                "email": row.email,
                "is_active": row.is_active,
                "roles": sorted(roles_by_user[row.id]),
            }
            for row in users
        ],
        "total": len(users),
    }


async def create_tenant_worker(
    *, tenant_id: str, role_name: str, user: User,
) -> dict:
    await require_tenant_role(user, tenant_id, "admin")
    if role_name not in {"annotator", "reviewer"}:
        raise HTTPException(status_code=400, detail="只能创建标注员或审核员")
    role = await Role.filter(
        scope="business", tenant_id=tenant_id, name=role_name,
    ).first()
    if role is None:
        role = await Role.filter(
            scope="business", tenant_id=None, name=role_name,
        ).first()
    if role is None:
        raise HTTPException(status_code=503, detail=f"{role_name} 角色未初始化")

    domain = settings.DEMO_ACCOUNT_DOMAIN or "example.com"
    alphabet = string.ascii_lowercase + string.digits
    email = ""
    for _ in range(8):
        token = "".join(secrets.choice(alphabet) for _ in range(8))
        email = f"avery.{role_name}-{token}@{domain}"
        if not await User.filter(email=email).exists():
            break
    else:
        raise HTTPException(status_code=409, detail="无法生成唯一账号，请重试")

    password = (
        "Fy-"
        + "".join(secrets.choice(alphabet) for _ in range(8))
        + "-"
        + str(secrets.randbelow(90) + 10)
    )
    worker = await user_service.create_user(UserCreate(
        email=email,
        password=password,
        is_active=True,
        is_superuser=False,
    ))
    await user_service.process_after_create(worker)
    try:
        await UserRole.create(
            user_id=worker.id,
            role_id=role.id,
            tenant_id=tenant_id,
            granted_by=user.id,
        )
    except Exception:
        worker.is_active = False
        worker.deleted_at = datetime.utcnow()
        await worker.save(update_fields=["is_active", "deleted_at", "updated_at"])
        raise
    return {
        "id": worker.id,
        "role": role_name,
        "email": email,
        "password": password,
        "message": "账号已创建，请立即复制并妥善保存密码",
    }


async def remove_tenant_worker(
    *, tenant_id: str, target_user_id: int, user: User,
) -> dict:
    await require_tenant_role(user, tenant_id, "admin")
    roles, bindings = await _tenant_role_rows(
        tenant_id, "annotator", "reviewer",
    )
    role_names = {role.id: role.name for role in roles}
    removable_role_ids = {
        binding.role_id for binding in bindings
        if binding.user_id == target_user_id
    }
    if not removable_role_ids:
        raise HTTPException(
            status_code=404,
            detail="该用户不是当前租户的标注员或审核员",
        )
    removed_roles = sorted({role_names[rid] for rid in removable_role_ids})
    await UserRole.filter(
        tenant_id=tenant_id,
        user_id=target_user_id,
        role_id__in=list(removable_role_ids),
    ).delete()
    if not await UserRole.filter(user_id=target_user_id).exists():
        target = await User.filter(id=target_user_id).first()
        if target is not None:
            target.is_active = False
            target.deleted_at = datetime.utcnow()
            await target.save(update_fields=[
                "is_active", "deleted_at", "updated_at",
            ])
    return {
        "user_id": target_user_id,
        "removed_roles": removed_roles,
        "message": "已移除该用户在当前租户的作业角色",
    }


async def update_tenant_annotation_settings(
    *, tenant_id: str, user: User, settings_value: dict,
) -> dict:
    await require_tenant_role(user, tenant_id, "admin")
    tenant = await PlatformTenant.filter(slug=tenant_id).first()
    if tenant is None:
        raise HTTPException(status_code=404, detail="租户不存在")
    value = normalize_annotation_settings({"annotation_defaults": settings_value})
    if len(value["instructions"]) > 4000:
        raise HTTPException(status_code=400, detail="标注说明不能超过 4000 字")
    minimum = value["min_interval_seconds"]
    if not 0 <= minimum <= 3600:
        raise HTTPException(
            status_code=400,
            detail="最短标注区间必须介于 0 到 3600 秒",
        )
    settings_data = dict(tenant.settings or {})
    settings_data["annotation_defaults"] = value
    tenant.settings = settings_data
    await tenant.save(update_fields=["settings", "updated_at"])
    return value
