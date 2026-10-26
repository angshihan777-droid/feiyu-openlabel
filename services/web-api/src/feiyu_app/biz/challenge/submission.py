"""Video drafts, final submission, and tenant-scoped media storage."""

from __future__ import annotations

import mimetypes
import re
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException
from starlette.datastructures import UploadFile

from ..db.models import Batch, MediaFile, Project, TaskSubmission, User
from ..services.label_v2 import LabelSaveIn, label_service
from ...config import settings
from .common import (
    ChallengeError,
    get_tenant_unit,
    has_tenant_role,
    media_id,
    refill_demo_workbench,
    require_tenant_role,
)
from .domain import (
    IntervalValidationError,
    pick_round_robin,
    total_duration,
    validate_intervals,
)
from .tenant import get_project_video_config


MAX_UPLOAD_BYTES = 500 * 1024 * 1024
UPLOAD_CHUNK_SIZE = 8 * 1024 * 1024
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm", ".mkv", ".avi"}


def objects_from_intervals(intervals: list[dict]) -> list[dict]:
    return [
        {
            "id": str(uuid4()),
            "label_uuid": str(uuid4()),
            "frame_intervals": [
                {
                    "time_start": interval["start"],
                    "time_end": interval["end"],
                }
            ],
            "attributes": {
                "label": interval.get("label", ""),
                "opType": "create",
            },
        }
        for interval in intervals
    ]


async def save_unit_draft(
    *,
    tenant_id: str,
    unit_id: int,
    user: User,
    intervals: list[dict],
) -> dict:
    """Persist an editable annotation draft without advancing the workflow."""
    await require_tenant_role(user, tenant_id, "annotator")
    unit = await get_tenant_unit(tenant_id=tenant_id, unit_id=unit_id)
    if unit.assignee_id != user.id:
        raise HTTPException(status_code=403, detail="无权编辑此任务")
    if unit.status not in {"assigned", "in_progress", "rejected"}:
        raise HTTPException(status_code=409, detail=f"任务状态 {unit.status} 不可编辑")

    media = await MediaFile.filter(id=media_id(unit) or -1).first()
    try:
        normalized = (
            validate_intervals(intervals, duration=media.duration if media else None)
            if intervals
            else []
        )
    except IntervalValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        label = await label_service.save_label(
            unit_id=unit.id,
            project_id=unit.project_id,
            mission=unit.mission,
            payload=LabelSaveIn(
                objects=objects_from_intervals(normalized),
                attrs={"challenge": True, "draft": True},
            ),
            expected_version=unit.data_version,
            actor_id=user.id,
        )
    except Exception as exc:
        if exc.__class__.__name__ == "LabelConflict":
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        raise

    unit.data_version = label.version
    unit.status = "in_progress"
    unit.stage_status = "in_progress"
    await unit.save(update_fields=[
        "data_version", "status", "stage_status", "updated_at",
    ])
    return {
        "message": "草稿已保存",
        "unit_id": unit.id,
        "status": unit.status,
        "version": label.version,
        "intervals": normalized,
    }


async def submit_unit(
    *,
    tenant_id: str,
    unit_id: int,
    user: User,
    intervals: list[dict],
) -> dict:
    await require_tenant_role(user, tenant_id, "annotator")
    unit = await get_tenant_unit(tenant_id=tenant_id, unit_id=unit_id)
    if unit.assignee_id != user.id:
        raise HTTPException(status_code=403, detail="无权提交此任务")
    if unit.status not in {"assigned", "in_progress", "rejected"}:
        raise HTTPException(status_code=409, detail=f"任务状态 {unit.status} 不可提交")

    media = await MediaFile.filter(id=media_id(unit) or -1).first()
    try:
        normalized = validate_intervals(
            intervals, duration=media.duration if media else None,
        )
    except IntervalValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    annotation_settings = await get_project_video_config(
        tenant_id=tenant_id, project_id=unit.project_id,
    )
    if annotation_settings["require_label"] and any(
        not interval.get("label") for interval in normalized
    ):
        raise HTTPException(status_code=400, detail="每个标注区间都必须填写标签")
    if (
        annotation_settings["label_mode"] == "preset"
        and any(
            interval.get("label") not in annotation_settings["labels"]
            for interval in normalized
        )
    ):
        raise HTTPException(status_code=400, detail="请选择项目预设标签")
    min_interval_seconds = annotation_settings["min_interval_seconds"]
    if any(
        interval["end"] - interval["start"] < min_interval_seconds
        for interval in normalized
    ):
        raise HTTPException(
            status_code=400,
            detail=f"标注区间不能短于 {min_interval_seconds:g} 秒",
        )

    batch = await Batch.filter(
        tenant_id=tenant_id, id=unit.batch_id,
    ).first() if unit.batch_id else None
    reviewer_pool = [int(i) for i in ((batch.reviewers if batch else []) or [])]
    reviewer_id = pick_round_robin(
        reviewer_pool, ordinal=unit.id, exclude={user.id},
    )
    if reviewer_id is None:
        raise ChallengeError("批次没有可用审核员")
    reviewer = await User.filter(id=reviewer_id, is_active=True).first()
    if reviewer is None or not await has_tenant_role(
        reviewer, tenant_id, "reviewer",
    ):
        raise ChallengeError(f"审核员 {reviewer_id} 不可用")

    now = datetime.utcnow()
    try:
        label = await label_service.save_label(
            unit_id=unit.id,
            project_id=unit.project_id,
            mission=unit.mission,
            payload=LabelSaveIn(
                objects=objects_from_intervals(normalized),
                attrs={"challenge": True},
            ),
            expected_version=unit.data_version,
            actor_id=user.id,
        )
    except Exception as exc:
        if exc.__class__.__name__ == "LabelConflict":
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        raise

    valid_duration = total_duration(normalized)
    await TaskSubmission.filter(
        tenant_id=tenant_id, unit_id=unit.id, is_valid=True,
    ).update(is_valid=False)
    await TaskSubmission.create(
        tenant_id=tenant_id,
        unit_id=unit.id,
        submitted_by=user.id,
        submitted_at=now,
        intervals=normalized,
        total_duration=valid_duration,
        submission_date=now.date(),
        label_version=label.version,
        is_valid=True,
    )

    unit.data_version = label.version
    unit.status = "under_review"
    unit.stage_status = "in_progress"
    unit.reviewer_id = reviewer.id
    unit.review_assigned_at = now
    unit.submitted_at = now
    unit.current_reject_reason = None
    await unit.save(update_fields=[
        "data_version", "status", "stage_status", "reviewer_id",
        "review_assigned_at", "submitted_at", "current_reject_reason",
        "updated_at",
    ])
    await refill_demo_workbench(tenant_id)
    return {
        "message": "提交成功",
        "unit_id": unit.id,
        "status": unit.status,
        "submitted_at": unit.submitted_at,
        "total_duration": valid_duration,
    }


async def list_media(*, tenant_id: str, project_id: int) -> dict:
    rows = await MediaFile.filter(
        tenant_id=tenant_id, project_id=project_id, status="ready",
    ).order_by("-created_at")
    return {
        "items": [
            {
                "id": row.id,
                "filename": row.filename,
                "size": row.file_size,
                "duration": row.duration,
                "path": f"/media/{row.id}/stream",
                "created_at": row.created_at,
            }
            for row in rows
        ],
        "total": len(rows),
    }


def _media_root(tenant_id: str) -> tuple[Path, Path]:
    safe_tenant = re.sub(r"[^A-Za-z0-9_-]", "_", tenant_id)
    media_root = Path(settings.MEDIA_ROOT).expanduser().resolve()
    tenant_dir = (media_root / safe_tenant).resolve()
    if media_root != tenant_dir and media_root not in tenant_dir.parents:
        raise HTTPException(status_code=400, detail="非法租户路径")
    return media_root, tenant_dir


def _probe_video_duration(path: Path) -> float | None:
    """Best-effort duration probe using the installed OpenCV package."""
    try:
        import cv2

        capture = cv2.VideoCapture(str(path))
        try:
            fps = float(capture.get(cv2.CAP_PROP_FPS) or 0)
            frames = float(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            if fps > 0 and frames > 0:
                return frames / fps
        finally:
            capture.release()
    except Exception:
        return None
    return None


async def store_media_upload(
    *,
    tenant_id: str,
    project_id: int,
    user: User,
    upload: UploadFile,
    max_bytes: int = MAX_UPLOAD_BYTES,
) -> MediaFile:
    import asyncio

    if not await Project.filter(
        tenant_id=tenant_id, id=project_id,
    ).exclude(status="archived").exists():
        raise HTTPException(status_code=404, detail="项目不存在或已归档")

    original_name = Path(upload.filename or "video.mp4").name
    extension = Path(original_name).suffix.lower()
    if extension not in ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(status_code=415, detail="不支持的视频格式")

    _, tenant_dir = _media_root(tenant_id)
    tenant_dir.mkdir(parents=True, exist_ok=True)
    destination = tenant_dir / f"{uuid4().hex}{extension}"
    written = 0
    try:
        with destination.open("wb") as output:
            while chunk := await upload.read(UPLOAD_CHUNK_SIZE):
                written += len(chunk)
                if written > max_bytes:
                    raise HTTPException(status_code=413, detail="视频超过 500MB 限制")
                output.write(chunk)
        if written == 0:
            raise HTTPException(status_code=400, detail="上传文件为空")
        duration = await asyncio.to_thread(_probe_video_duration, destination)
        return await MediaFile.create(
            tenant_id=tenant_id,
            project_id=project_id,
            filename=original_name,
            storage_path=str(destination),
            mime_type=(
                upload.content_type
                or mimetypes.guess_type(original_name)[0]
                or "video/mp4"
            ),
            file_size=written,
            duration=duration,
            uploaded_by=user.id,
            status="ready",
        )
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    finally:
        await upload.close()


def resolve_media_path(*, tenant_id: str, storage_path: str) -> Path:
    _, tenant_dir = _media_root(tenant_id)
    path = Path(storage_path).resolve()
    if path != tenant_dir and tenant_dir not in path.parents:
        raise HTTPException(status_code=403, detail="非法视频路径")
    if not path.is_file():
        raise HTTPException(status_code=404, detail="视频文件不存在")
    return path
