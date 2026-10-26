"""Daily workload statistics and CSV/dataset reporting."""

from __future__ import annotations

import csv
import io
from collections import defaultdict
from datetime import date
from typing import Optional

from fastapi import HTTPException

from ..db.models import RejectHistory, TaskSubmission, Unit, User
from .common import display_name, latest_intervals, media_id, media_map, require_tenant_role
from .domain import total_duration


async def daily_duration(
    *,
    tenant_id: str,
    batch_id: Optional[int],
    start_date: date,
    end_date: date,
) -> dict:
    if end_date < start_date:
        raise HTTPException(status_code=400, detail="结束日期不能早于开始日期")
    units = await Unit.filter(tenant_id=tenant_id)
    if batch_id is not None:
        units = await Unit.filter(tenant_id=tenant_id, batch_id=batch_id)
    unit_ids = [unit.id for unit in units]
    submissions = await TaskSubmission.filter(
        tenant_id=tenant_id,
        unit_id__in=unit_ids,
        is_valid=True,
        submission_date__gte=start_date,
        submission_date__lte=end_date,
    )
    grouped: dict[tuple[int, str], float] = defaultdict(float)
    for submission in submissions:
        grouped[(submission.submitted_by, submission.submission_date.isoformat())] += (
            submission.total_duration
        )
    users = {
        row.id: row
        for row in await User.filter(id__in={uid for uid, _ in grouped})
    }
    items = [
        {
            "user_id": user_id,
            "username": display_name(users.get(user_id)),
            "date": day,
            "duration": duration,
        }
        for (user_id, day), duration in sorted(
            grouped.items(), key=lambda item: (item[0][1], item[0][0]),
        )
    ]
    return {
        "items": items,
        "total_duration": sum(item["duration"] for item in items),
    }


async def export_workbench_csv(*, tenant_id: str, kind: str) -> str:
    if kind not in {"success", "problem"}:
        raise HTTPException(status_code=400, detail="未知导出类型")
    if kind == "success":
        units = await Unit.filter(
            tenant_id=tenant_id, status="approved",
        ).order_by("-approved_at")
        submissions = await TaskSubmission.filter(
            tenant_id=tenant_id,
            unit_id__in=[unit.id for unit in units],
            is_valid=True,
        ).order_by("label_version")
        latest_submission = {item.unit_id: item for item in submissions}
    else:
        units = await Unit.filter(
            tenant_id=tenant_id,
            status__in=[
                "returned", "rejected", "escalated",
                "source_confirmed", "void", "difficult_sample",
            ],
        ).order_by("-updated_at")
        latest_submission = {}

    media = await media_map(units)
    user_ids = {
        value
        for unit in units
        for value in (unit.assignee_id, unit.reviewer_id)
        if value
    }
    users = {row.id: row for row in await User.filter(id__in=user_ids)}
    histories: dict[int, list[RejectHistory]] = defaultdict(list)
    if kind == "problem":
        for row in await RejectHistory.filter(
            tenant_id=tenant_id, unit_id__in=[unit.id for unit in units],
        ).order_by("rejected_at"):
            histories[row.unit_id].append(row)

    output = io.StringIO()
    writer = csv.writer(output)
    if kind == "success":
        writer.writerow([
            "任务ID", "视频", "标注员", "审核员", "区间",
            "标签", "有效时长(秒)", "提交时间", "审核通过时间",
        ])
        for unit in units:
            submission = latest_submission.get(unit.id)
            intervals = submission.intervals if submission else []
            media_row = media.get(media_id(unit) or -1)
            writer.writerow([
                unit.id,
                media_row.filename if media_row else unit.stream,
                display_name(users.get(unit.assignee_id)),
                display_name(users.get(unit.reviewer_id)),
                " | ".join(
                    f"[{item['start']:g}, {item['end']:g}]"
                    for item in intervals
                ),
                " | ".join(str(item.get("label") or "") for item in intervals),
                submission.total_duration if submission else 0,
                submission.submitted_at.isoformat() if submission else "",
                unit.approved_at.isoformat() if unit.approved_at else "",
            ])
    else:
        writer.writerow([
            "任务ID", "视频", "问题状态", "问题来源", "标注员",
            "审核员/操作人", "原因", "完整原因记录", "更新时间",
        ])
        for unit in units:
            media_row = media.get(media_id(unit) or -1)
            history = histories.get(unit.id, [])
            source = (
                "标注员回退"
                if unit.status in {"returned", "source_confirmed", "void"}
                else "审核员驳回" if unit.status in {"rejected", "escalated"}
                else "管理员标记"
            )
            writer.writerow([
                unit.id,
                media_row.filename if media_row else unit.stream,
                unit.status,
                source,
                display_name(users.get(unit.assignee_id)),
                display_name(users.get(
                    history[-1].reviewer_id if history else unit.reviewer_id
                )),
                unit.current_reject_reason or "",
                " | ".join(item.reason for item in history),
                unit.updated_at.isoformat() if unit.updated_at else "",
            ])
    return output.getvalue()


async def list_video_results(
    *, tenant_id: str, user: User, kind: str,
) -> dict:
    await require_tenant_role(user, tenant_id, "admin", "tenant-admin")
    if kind not in {"success", "problem"}:
        raise HTTPException(status_code=400, detail="未知视频结果分类")
    statuses = (
        ["approved"]
        if kind == "success"
        else [
            "returned", "rejected", "escalated",
            "source_confirmed", "void", "difficult_sample",
        ]
    )
    units = await Unit.filter(
        tenant_id=tenant_id, status__in=statuses,
    ).order_by("-updated_at")
    media = await media_map(units)
    submissions = await TaskSubmission.filter(
        tenant_id=tenant_id,
        unit_id__in=[unit.id for unit in units],
        is_valid=True,
    ).order_by("label_version")
    latest_submission = {row.unit_id: row for row in submissions}
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
        submission = latest_submission.get(unit.id)
        intervals = submission.intervals if submission else await latest_intervals(unit)
        if isinstance(intervals, tuple):
            intervals = intervals[0]
        items.append({
            "unit_id": unit.id,
            "video_id": media_row.id if media_row else None,
            "video_name": media_row.filename if media_row else unit.stream,
            "video_url": f"/media/{media_row.id}/stream" if media_row else None,
            "video_duration": media_row.duration if media_row else None,
            "status": unit.status,
            "reason": unit.current_reject_reason,
            "intervals": intervals,
            "total_duration": submission.total_duration if submission else total_duration(intervals),
            "annotator_name": (
                display_name(users.get(unit.assignee_id))
                if unit.assignee_id else None
            ),
            "reviewer_name": (
                display_name(users.get(unit.reviewer_id))
                if unit.reviewer_id else None
            ),
            "updated_at": unit.updated_at,
        })
    return {"items": items, "total": len(items), "kind": kind}


async def export_csv(
    *, tenant_id: str, batch_id: int, start_date: date, end_date: date,
) -> str:
    submissions = await TaskSubmission.filter(
        tenant_id=tenant_id,
        is_valid=True,
        submission_date__gte=start_date,
        submission_date__lte=end_date,
    ).order_by("submission_date")
    units = {
        row.id: row for row in await Unit.filter(
            tenant_id=tenant_id, batch_id=batch_id,
            id__in=[row.unit_id for row in submissions],
        )
    }
    media = await media_map(units.values())
    user_ids = {
        user_id
        for row in submissions
        for user_id in (
            row.submitted_by,
            units.get(row.unit_id).reviewer_id if units.get(row.unit_id) else None,
        )
        if user_id
    }
    users = {row.id: row for row in await User.filter(id__in=user_ids)}

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "标注员", "审核员", "视频名", "提交日期", "有效时长(秒)", "状态",
    ])
    for submission in submissions:
        unit = units.get(submission.unit_id)
        if unit is None:
            continue
        media_row = media.get(media_id(unit) or -1)
        writer.writerow([
            display_name(users.get(submission.submitted_by)),
            display_name(users.get(unit.reviewer_id)),
            media_row.filename if media_row else unit.stream,
            submission.submission_date.isoformat(),
            f"{submission.total_duration:.3f}",
            unit.status,
        ])
    return output.getvalue()
