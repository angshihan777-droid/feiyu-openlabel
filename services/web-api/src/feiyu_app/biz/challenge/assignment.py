"""Task queues, task detail, and role pools."""

from __future__ import annotations

from fastapi import HTTPException

from ..db.models import MediaFile, RejectHistory, Role, Unit, User, UserRole
from .common import (
    display_name,
    get_tenant_unit,
    has_tenant_role,
    latest_intervals,
    media_id,
    media_map,
    refill_demo_workbench,
)
from .domain import anonymize_unit, total_duration
from .tenant import get_project_video_config


async def list_annotator_tasks(*, tenant_id: str, user_id: int) -> dict:
    await refill_demo_workbench(tenant_id)
    units = await Unit.filter(
        tenant_id=tenant_id,
        assignee_id=user_id,
        status__in=["assigned", "in_progress", "rejected"],
    ).order_by("-updated_at")
    media = await media_map(units)
    users = {
        row.id: row for row in await User.filter(
            id__in=[unit.reviewer_id for unit in units if unit.reviewer_id]
        )
    }

    items = []
    for unit in units:
        media_row = media.get(media_id(unit) or -1)
        annotation_settings = await get_project_video_config(
            tenant_id=tenant_id, project_id=unit.project_id,
        )
        item = {
            "unit_id": unit.id,
            "video_id": media_row.id if media_row else None,
            "video_name": media_row.filename if media_row else unit.stream,
            "video_duration": media_row.duration if media_row else None,
            "video_url": f"/media/{media_row.id}/stream" if media_row else None,
            "status": unit.status,
            "assigned_at": unit.assigned_at,
            "reject_count": unit.reject_count,
            "reject_reason": unit.current_reject_reason,
            "annotation_settings": annotation_settings,
            "reviewer_name": "匿名" if unit.reviewer_id else None,
            "reviewer_id": unit.reviewer_id,
        }
        if unit.reviewer_id:
            item["reviewer_name"] = display_name(users.get(unit.reviewer_id))
        items.append(anonymize_unit(item, viewer_role="annotator"))
    return {"tasks": items, "total": len(items)}


async def list_reviewer_tasks(*, tenant_id: str, user_id: int) -> dict:
    await refill_demo_workbench(tenant_id)
    units = await Unit.filter(
        tenant_id=tenant_id,
        reviewer_id=user_id,
        status__in=["submitted", "under_review"],
    ).exclude(assignee_id=user_id).order_by("-updated_at")
    media = await media_map(units)

    items = []
    for unit in units:
        intervals, _ = await latest_intervals(unit)
        media_row = media.get(media_id(unit) or -1)
        annotation_settings = await get_project_video_config(
            tenant_id=tenant_id, project_id=unit.project_id,
        )
        history = await RejectHistory.filter(
            tenant_id=tenant_id, unit_id=unit.id,
        ).order_by("-rejected_at")
        item = {
            "unit_id": unit.id,
            "video_id": media_row.id if media_row else None,
            "video_name": media_row.filename if media_row else unit.stream,
            "video_duration": media_row.duration if media_row else None,
            "video_url": f"/media/{media_row.id}/stream" if media_row else None,
            "status": unit.status,
            "submitted_at": unit.submitted_at,
            "annotator_name": "匿名",
            "assignee_id": unit.assignee_id,
            "intervals": intervals,
            "total_duration": total_duration(intervals),
            "annotation_settings": annotation_settings,
            "reject_history": [
                {"rejected_at": row.rejected_at, "reason": row.reason}
                for row in history
            ],
        }
        items.append(anonymize_unit(item, viewer_role="reviewer"))
    return {"tasks": items, "total": len(items)}


async def get_unit_detail(
    *, tenant_id: str, unit_id: int, user: User,
) -> dict:
    unit = await get_tenant_unit(tenant_id=tenant_id, unit_id=unit_id)
    is_project_admin = await has_tenant_role(
        user, tenant_id, "admin", "tenant-admin",
    )
    is_owner = unit.assignee_id == user.id
    is_reviewer = unit.reviewer_id == user.id and unit.assignee_id != user.id
    if not (is_project_admin or is_owner or is_reviewer):
        raise HTTPException(status_code=403, detail="无权访问此任务")

    media = await MediaFile.filter(
        id=media_id(unit) or -1, tenant_id=tenant_id,
    ).first()
    intervals, version = await latest_intervals(unit)
    annotation_settings = await get_project_video_config(
        tenant_id=tenant_id, project_id=unit.project_id,
    )
    assignee = await User.filter(id=unit.assignee_id).first() if unit.assignee_id else None
    reviewer = await User.filter(id=unit.reviewer_id).first() if unit.reviewer_id else None
    data = {
        "unit_id": unit.id,
        "batch_id": unit.batch_id,
        "video": {
            "id": media.id if media else None,
            "filename": media.filename if media else unit.stream,
            "path": f"/media/{media.id}/stream" if media else None,
            "duration": media.duration if media else None,
        },
        "status": unit.status,
        "reject_count": unit.reject_count,
        "reject_reason": unit.current_reject_reason,
        "current_label": {"intervals": intervals, "version": version},
        "annotation_settings": annotation_settings,
        "annotation_config": annotation_settings,
        "assignee_id": unit.assignee_id,
        "reviewer_id": unit.reviewer_id,
        "annotator_name": display_name(assignee),
        "reviewer_name": display_name(reviewer),
    }
    if is_project_admin:
        return data
    if is_owner:
        return anonymize_unit(data, viewer_role="annotator")
    return anonymize_unit(data, viewer_role="reviewer")


async def role_pools(*, tenant_id: str) -> dict:
    roles = await Role.filter(
        scope="business",
        tenant_id=tenant_id,
        name__in=["annotator", "reviewer"],
    )
    role_by_name = {role.name: role for role in roles}
    assignments = await UserRole.filter(
        tenant_id=tenant_id,
        role_id__in=[role.id for role in role_by_name.values()],
    )
    user_ids = {row.user_id for row in assignments}
    users = {
        row.id: row for row in await User.filter(
            id__in=user_ids, is_active=True,
        ).order_by("id")
    }

    def items_for(role_name: str) -> list[dict]:
        role = role_by_name.get(role_name)
        if role is None:
            return []
        ids = {row.user_id for row in assignments if row.role_id == role.id}
        return [
            {
                "id": user.id,
                "name": display_name(user),
                "email": user.email,
            }
            for user_id, user in users.items()
            if user_id in ids
        ]

    return {
        "annotators": items_for("annotator"),
        "reviewers": items_for("reviewer"),
    }
