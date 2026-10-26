"""Reviewer decisions and annotation-return transitions."""

from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException

from ..db.models import RejectHistory, TaskSubmission, Unit, User
from .common import (
    display_name,
    get_tenant_unit,
    latest_intervals,
    media_id,
    media_map,
    refill_demo_workbench,
    require_tenant_role,
)
from .domain import next_reject_state
from .tenant import get_project_video_config


async def approve_unit(*, tenant_id: str, unit_id: int, user: User) -> dict:
    await require_tenant_role(user, tenant_id, "reviewer")
    unit = await get_tenant_unit(tenant_id=tenant_id, unit_id=unit_id)
    if unit.reviewer_id != user.id or unit.assignee_id == user.id:
        raise HTTPException(status_code=403, detail="无权审核此任务")
    if unit.status not in {"submitted", "under_review"}:
        raise HTTPException(status_code=409, detail=f"任务状态 {unit.status} 不可审核")
    now = datetime.utcnow()
    unit.status = "approved"
    unit.stage_status = "done"
    unit.reviewed_at = now
    unit.approved_at = now
    await unit.save(update_fields=[
        "status", "stage_status", "reviewed_at", "approved_at", "updated_at",
    ])
    await refill_demo_workbench(tenant_id)
    return {
        "message": "审核通过",
        "unit_id": unit.id,
        "status": unit.status,
        "approved_at": unit.approved_at,
    }


async def reject_unit(
    *, tenant_id: str, unit_id: int, user: User, reason: str,
) -> dict:
    await require_tenant_role(user, tenant_id, "reviewer")
    unit = await get_tenant_unit(tenant_id=tenant_id, unit_id=unit_id)
    if unit.reviewer_id != user.id or unit.assignee_id == user.id:
        raise HTTPException(status_code=403, detail="无权审核此任务")
    if unit.status not in {"submitted", "under_review"}:
        raise HTTPException(status_code=409, detail=f"任务状态 {unit.status} 不可审核")
    reason = reason.strip()
    if not reason:
        raise HTTPException(status_code=400, detail="必须填写驳回原因")

    new_status, new_count = next_reject_state(unit.reject_count)
    now = datetime.utcnow()
    await TaskSubmission.filter(
        tenant_id=tenant_id, unit_id=unit.id, is_valid=True,
    ).update(is_valid=False)
    await RejectHistory.create(
        tenant_id=tenant_id,
        unit_id=unit.id,
        reviewer_id=user.id,
        rejected_at=now,
        reason=reason,
        label_version=unit.data_version,
    )
    unit.status = new_status
    unit.stage_status = "in_progress"
    unit.reject_count = new_count
    unit.current_reject_reason = reason
    unit.reviewed_at = now
    await unit.save(update_fields=[
        "status", "stage_status", "reject_count",
        "current_reject_reason", "reviewed_at", "updated_at",
    ])
    await refill_demo_workbench(tenant_id)
    return {
        "message": "已驳回，已升级管理员裁决" if new_status == "escalated" else "已驳回",
        "unit_id": unit.id,
        "status": new_status,
        "reject_count": new_count,
        "escalated": new_status == "escalated",
    }


async def return_unit_to_admin(
    *,
    tenant_id: str,
    unit_id: int,
    user: User,
    reason_code: str,
    reason: str = "",
) -> dict:
    await require_tenant_role(user, tenant_id, "annotator")
    unit = await get_tenant_unit(tenant_id=tenant_id, unit_id=unit_id)
    if unit.assignee_id != user.id:
        raise HTTPException(status_code=403, detail="无权回退此任务")
    if unit.status not in {"assigned", "in_progress", "rejected"}:
        raise HTTPException(status_code=409, detail="当前任务状态不可回退视频")
    config = await get_project_video_config(
        tenant_id=tenant_id, project_id=unit.project_id,
    )
    selected = next(
        (
            item for item in config["return_reasons"]
            if item["code"] == reason_code
        ),
        None,
    )
    if selected is None:
        raise HTTPException(status_code=400, detail="请选择有效的回退原因")
    detail = reason.strip()
    if reason_code == "other" and not detail:
        raise HTTPException(status_code=400, detail="请填写其他原因")
    reason_text = selected["label"]
    if detail:
        reason_text = f"{reason_text}：{detail}"

    now = datetime.utcnow()
    await TaskSubmission.filter(
        tenant_id=tenant_id, unit_id=unit.id, is_valid=True,
    ).update(is_valid=False)
    await RejectHistory.create(
        tenant_id=tenant_id,
        unit_id=unit.id,
        reviewer_id=user.id,
        rejected_at=now,
        reason=reason_text,
        label_version=unit.data_version,
    )
    unit.reviewer_id = None
    unit.review_assigned_at = None
    unit.status = "returned"
    unit.stage_status = "in_progress"
    unit.current_reject_reason = reason_text
    unit.reviewed_at = now
    await unit.save(update_fields=[
        "reviewer_id", "review_assigned_at", "status", "stage_status",
        "current_reject_reason", "reviewed_at", "updated_at",
    ])
    return {
        "message": "视频已回退给租户管理员复核",
        "unit_id": unit.id,
        "status": unit.status,
        "reason": reason_text,
    }


async def list_admin_reviews(*, tenant_id: str, user: User) -> dict:
    await require_tenant_role(user, tenant_id, "admin", "tenant-admin")
    units = await Unit.filter(
        tenant_id=tenant_id,
        status__in=[
            "returned", "rejected", "escalated",
            "source_confirmed", "void", "difficult_sample",
        ],
    ).order_by("-updated_at")
    media = await media_map(units)
    user_ids = {
        value
        for unit in units
        for value in (unit.assignee_id, unit.reviewer_id)
        if value
    }
    users = {row.id: row for row in await User.filter(id__in=user_ids)}
    items = []
    for unit in units:
        media_row = media.get(media_id(unit) or -1)
        intervals, _ = await latest_intervals(unit)
        history = await RejectHistory.filter(
            tenant_id=tenant_id, unit_id=unit.id,
        ).order_by("-rejected_at")
        items.append({
            "unit_id": unit.id,
            "video_name": media_row.filename if media_row else unit.stream,
            "video_url": f"/media/{media_row.id}/stream" if media_row else None,
            "video_duration": media_row.duration if media_row else None,
            "status": unit.status,
            "reason": unit.current_reject_reason,
            "intervals": intervals,
            "assignee_id": unit.assignee_id,
            "assignee_name": display_name(users.get(unit.assignee_id)),
            "reviewer_id": unit.reviewer_id,
            "reviewer_name": display_name(users.get(unit.reviewer_id)),
            "reject_count": unit.reject_count,
            "updated_at": unit.updated_at,
            "history": [
                {
                    "actor_id": row.reviewer_id,
                    "actor_name": display_name(users.get(row.reviewer_id)),
                    "reason": row.reason,
                    "rejected_at": row.rejected_at,
                }
                for row in history
            ],
        })
    return {"tasks": items, "total": len(items)}
