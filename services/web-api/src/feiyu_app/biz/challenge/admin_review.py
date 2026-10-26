"""Tenant-admin review, arbitration, reassignment, and difficult samples."""

from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException

from ..db.models import Batch, RejectHistory, TaskSubmission, Unit, User
from .common import (
    display_name,
    get_tenant_unit,
    has_tenant_role,
    latest_intervals,
    media_id,
    media_map,
    require_tenant_role,
)


ADMIN_REVIEW_STATUSES = {
    "returned", "rejected", "escalated",
    "source_confirmed", "void", "difficult_sample",
}


async def admin_review_action(
    *,
    tenant_id: str,
    unit_id: int,
    user: User,
    action: str,
    reason: str = "",
    new_assignee_id: int | None = None,
) -> dict:
    await require_tenant_role(user, tenant_id, "admin", "tenant-admin")
    unit = await get_tenant_unit(tenant_id=tenant_id, unit_id=unit_id)
    if unit.status not in ADMIN_REVIEW_STATUSES:
        raise HTTPException(status_code=409, detail="当前任务不在管理员复核队列")
    reason = reason.strip()
    now = datetime.utcnow()

    if action == "confirm_issue":
        await TaskSubmission.filter(
            tenant_id=tenant_id, unit_id=unit.id, is_valid=True,
        ).update(is_valid=False)
        unit.status = "source_confirmed"
        unit.stage_status = "done"
        unit.current_reject_reason = reason or unit.current_reject_reason or "管理员确认视频存在问题"
    elif action == "return_to_annotator":
        unit.status = "rejected"
        unit.stage_status = "in_progress"
        unit.current_reject_reason = reason or "管理员复核：标注需要重新处理"
        unit.reviewer_id = None
        unit.review_assigned_at = None
    elif action == "reassign":
        if new_assignee_id is None:
            raise HTTPException(status_code=400, detail="请选择新的标注员")
        assignee = await User.filter(id=new_assignee_id, is_active=True).first()
        if assignee is None or not await has_tenant_role(
            assignee, tenant_id, "annotator",
        ):
            raise HTTPException(status_code=400, detail="新标注员不可用")
        unit.assignee_id = assignee.id
        unit.assigned_at = now
        unit.reviewer_id = None
        unit.review_assigned_at = None
        unit.status = "assigned"
        unit.stage_status = "pending"
        unit.current_reject_reason = reason or unit.current_reject_reason
    elif action == "void":
        await TaskSubmission.filter(
            tenant_id=tenant_id, unit_id=unit.id, is_valid=True,
        ).update(is_valid=False)
        unit.status = "void"
        unit.stage_status = "done"
        unit.current_reject_reason = reason or unit.current_reject_reason or "管理员作废"
    else:
        raise HTTPException(status_code=400, detail="未知复核动作")

    if reason:
        await RejectHistory.create(
            tenant_id=tenant_id,
            unit_id=unit.id,
            reviewer_id=user.id,
            rejected_at=now,
            reason=reason,
            label_version=unit.data_version,
        )
    unit.reviewed_at = now
    await unit.save(update_fields=[
        "assignee_id", "assigned_at", "reviewer_id", "review_assigned_at",
        "status", "stage_status", "current_reject_reason",
        "reviewed_at", "updated_at",
    ])
    return {"message": "管理员复核已保存", "unit_id": unit.id, "status": unit.status}


async def list_escalated(*, tenant_id: str, user: User) -> dict:
    await require_tenant_role(user, tenant_id, "tenant-admin")
    units = await Unit.filter(
        tenant_id=tenant_id, status="escalated",
    ).order_by("-updated_at")
    media = await media_map(units)
    user_ids = {
        user_id
        for unit in units
        for user_id in (unit.assignee_id, unit.reviewer_id)
        if user_id
    }
    users = {row.id: row for row in await User.filter(id__in=user_ids)}
    batches = {
        row.id: row for row in await Batch.filter(
            tenant_id=tenant_id,
            id__in=[unit.batch_id for unit in units if unit.batch_id],
        )
    }

    items = []
    for unit in units:
        intervals, _ = await latest_intervals(unit)
        history = await RejectHistory.filter(
            tenant_id=tenant_id, unit_id=unit.id,
        ).order_by("-rejected_at")
        media_row = media.get(media_id(unit) or -1)
        items.append({
            "unit_id": unit.id,
            "video_id": media_row.id if media_row else None,
            "video_name": media_row.filename if media_row else unit.stream,
            "batch_name": batches.get(unit.batch_id).name if unit.batch_id in batches else None,
            "annotator_id": unit.assignee_id,
            "annotator_name": display_name(users.get(unit.assignee_id)),
            "reviewer_id": unit.reviewer_id,
            "reviewer_name": display_name(users.get(unit.reviewer_id)),
            "status": unit.status,
            "reject_count": unit.reject_count,
            "escalated_at": unit.updated_at,
            "current_intervals": intervals,
            "reject_history": [
                {
                    "rejected_at": row.rejected_at,
                    "reviewer_id": row.reviewer_id,
                    "reviewer_name": display_name(users.get(row.reviewer_id)),
                    "reason": row.reason,
                }
                for row in history
            ],
        })
    return {"tasks": items, "total": len(items)}


async def escalated_unit(tenant_id: str, unit_id: int) -> Unit:
    unit = await get_tenant_unit(tenant_id=tenant_id, unit_id=unit_id)
    if unit.status != "escalated":
        raise HTTPException(status_code=409, detail="任务未升级，无需裁决")
    return unit


async def force_approve(
    *, tenant_id: str, unit_id: int, user: User, note: str = "",
) -> dict:
    await require_tenant_role(user, tenant_id, "tenant-admin")
    unit = await escalated_unit(tenant_id, unit_id)
    now = datetime.utcnow()
    latest_submission = await TaskSubmission.filter(
        tenant_id=tenant_id, unit_id=unit.id,
    ).order_by("-label_version").first()
    if latest_submission is not None:
        latest_submission.is_valid = True
        await latest_submission.save(update_fields=["is_valid", "updated_at"])
    unit.status = "approved"
    unit.stage_status = "done"
    unit.reviewed_at = now
    unit.approved_at = now
    await unit.save(update_fields=[
        "status", "stage_status", "reviewed_at", "approved_at", "updated_at",
    ])
    return {
        "message": "强制通过成功",
        "unit_id": unit.id,
        "status": unit.status,
        "approved_at": unit.approved_at,
        "note": note,
    }


async def reassign_unit(
    *,
    tenant_id: str,
    unit_id: int,
    user: User,
    new_assignee_id: int,
    reason: str = "",
) -> dict:
    await require_tenant_role(user, tenant_id, "tenant-admin")
    unit = await escalated_unit(tenant_id, unit_id)
    batch = await Batch.filter(
        tenant_id=tenant_id, id=unit.batch_id,
    ).first() if unit.batch_id else None
    if batch is None or new_assignee_id not in (batch.assignees or []):
        raise HTTPException(status_code=400, detail="新标注员不在批次标注员池中")
    assignee = await User.filter(id=new_assignee_id, is_active=True).first()
    if assignee is None or not await has_tenant_role(
        assignee, tenant_id, "annotator",
    ):
        raise HTTPException(status_code=400, detail="新标注员不可用")
    await TaskSubmission.filter(
        tenant_id=tenant_id, unit_id=unit.id, is_valid=True,
    ).update(is_valid=False)
    now = datetime.utcnow()
    unit.assignee_id = assignee.id
    unit.assigned_at = now
    unit.reviewer_id = None
    unit.review_assigned_at = None
    unit.status = "assigned"
    unit.stage_status = "pending"
    unit.reject_count = 0
    unit.current_reject_reason = None
    await unit.save(update_fields=[
        "assignee_id", "assigned_at", "reviewer_id", "review_assigned_at",
        "status", "stage_status", "reject_count",
        "current_reject_reason", "updated_at",
    ])
    return {
        "message": "重新分配成功",
        "unit_id": unit.id,
        "new_assignee_id": assignee.id,
        "new_assignee_name": display_name(assignee),
        "status": unit.status,
        "reason": reason,
    }


async def mark_difficult(
    *, tenant_id: str, unit_id: int, user: User, reason: str = "",
) -> dict:
    await require_tenant_role(user, tenant_id, "tenant-admin")
    unit = await escalated_unit(tenant_id, unit_id)
    await TaskSubmission.filter(
        tenant_id=tenant_id, unit_id=unit.id, is_valid=True,
    ).update(is_valid=False)
    unit.status = "difficult_sample"
    unit.stage_status = "pending"
    unit.current_reject_reason = reason.strip() or unit.current_reject_reason
    await unit.save(update_fields=[
        "status", "stage_status", "current_reject_reason", "updated_at",
    ])
    return {
        "message": "已标记为困难样本",
        "unit_id": unit.id,
        "status": unit.status,
    }
