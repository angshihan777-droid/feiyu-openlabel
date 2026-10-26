"""Challenge-specific HTTP endpoints.

This router is mounted without a prefix. Nginx exposes ``/api/v1/b/*`` by
stripping the business prefix, matching the existing routers.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Query,
    UploadFile,
)
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ..apps.ctx import CTX_USER_ID, get_current_tenant_id
from ..apps.dependency import permission_required
from ..biz.challenge import service
from ..biz.challenge.service import (
    ChallengeError,
    admin_review_action,
    approve_unit,
    create_tenant_worker,
    daily_duration,
    export_csv,
    export_workbench_csv,
    force_approve,
    get_unit_detail,
    list_annotator_tasks,
    list_admin_reviews,
    list_escalated,
    list_media,
    list_reviewer_tasks,
    list_video_results,
    mark_difficult,
    reassign_unit,
    reject_unit,
    remove_tenant_worker,
    return_unit_to_admin,
    resolve_media_path,
    role_pools,
    save_unit_draft,
    store_media_upload,
    submit_unit,
    tenant_admin_members,
    tenant_admin_overview,
    get_tenant_annotation_settings,
    update_tenant_annotation_settings,
    get_project_video_config,
    update_project_video_config,
)
from ..biz.db.models import MediaFile, User

router = APIRouter(tags=["challenge"])

CHUNK_SIZE = 8 * 1024 * 1024


class SubmitIn(BaseModel):
    intervals: list[dict] = Field(default_factory=list)


class RejectIn(BaseModel):
    reason: str = Field(..., min_length=1, max_length=4096)


class ForceApproveIn(BaseModel):
    note: str = Field("", max_length=4096)


class ReassignIn(BaseModel):
    new_assignee_id: int
    reason: str = Field("", max_length=4096)


class DifficultIn(BaseModel):
    reason: str = Field("", max_length=4096)


class AnnotationSettingsIn(BaseModel):
    instructions: str = Field("", max_length=4000)
    require_label: bool = True
    min_interval_seconds: float = Field(0.1, ge=0, le=3600)


class WorkerCreateIn(BaseModel):
    role: str = Field(..., pattern=r"^(annotator|reviewer)$")


class VideoConfigIn(BaseModel):
    instructions: str = Field("", max_length=4000)
    require_label: bool = True
    min_interval_seconds: float = Field(0.1, ge=0, le=3600)
    label_mode: str = Field("free", pattern=r"^(preset|free)$")
    labels: list[str] = Field(default_factory=list, max_length=200)
    label_template: str = Field("", max_length=64)
    fps: float = Field(30.0, ge=1, le=120)
    return_reasons: list[dict] = Field(default_factory=list)


class ReturnVideoIn(BaseModel):
    reason_code: str = Field(..., min_length=1, max_length=64)
    reason: str = Field("", max_length=2000)


class AdminReviewActionIn(BaseModel):
    action: str = Field(
        ..., pattern=r"^(confirm_issue|return_to_annotator|reassign|void)$",
    )
    reason: str = Field("", max_length=2000)
    new_assignee_id: Optional[int] = None


@router.get("/challenge/users/pools")
async def user_pools(
    user: User = permission_required("business:anno-job:write"),
):
    await service.require_tenant_role(user, _tenant(), "admin", "tenant-admin")
    return await role_pools(tenant_id=_tenant())


@router.get("/tenant-admin/overview")
async def tenant_overview(
    user: User = permission_required("admin:project:read"),
):
    return await tenant_admin_overview(tenant_id=_tenant(), user=user)


@router.get("/tenant-admin/members")
async def tenant_members(
    user: User = permission_required("admin:user:read"),
):
    return await tenant_admin_members(tenant_id=_tenant(), user=user)


@router.delete("/tenant-admin/members/{user_id}")
async def remove_tenant_member(
    user_id: int,
    user: User = permission_required("admin:user:write"),
):
    return await remove_tenant_worker(
        tenant_id=_tenant(), target_user_id=user_id, user=user,
    )


@router.post("/tenant-admin/members", status_code=201)
async def create_tenant_member(
    payload: WorkerCreateIn,
    user: User = permission_required("admin:user:write"),
):
    return await create_tenant_worker(
        tenant_id=_tenant(), role_name=payload.role, user=user,
    )


@router.get("/tenant-admin/annotation-settings")
async def tenant_annotation_settings(
    user: User = permission_required("admin:project:read"),
):
    await service.require_tenant_role(user, _tenant(), "admin")
    return await get_tenant_annotation_settings(_tenant())


@router.put("/tenant-admin/annotation-settings")
async def save_tenant_annotation_settings(
    payload: AnnotationSettingsIn,
    user: User = permission_required("admin:project:write"),
):
    return await update_tenant_annotation_settings(
        tenant_id=_tenant(), user=user,
        settings_value=payload.model_dump(),
    )


@router.get("/projects/{project_id}/video-config")
async def project_video_config(
    project_id: int,
    user: User = permission_required("business:project:read"),
):
    await service.require_tenant_role(user, _tenant(), "admin", "tenant-admin")
    return await get_project_video_config(
        tenant_id=_tenant(), project_id=project_id,
    )


@router.put("/projects/{project_id}/video-config")
async def save_project_video_config(
    project_id: int,
    payload: VideoConfigIn,
    user: User = permission_required("business:project:write"),
):
    return await update_project_video_config(
        tenant_id=_tenant(),
        project_id=project_id,
        user=user,
        value=payload.model_dump(),
    )


def _tenant() -> str:
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise HTTPException(status_code=400, detail="当前会话未绑定租户")
    return tenant_id


def _actor() -> int:
    user_id = CTX_USER_ID.get()
    if not user_id:
        raise HTTPException(status_code=401, detail="未登录")
    return int(user_id)


@router.get("/units/my-tasks")
async def my_tasks(
    user: User = permission_required("business:label:read"),
):
    return await list_annotator_tasks(
        tenant_id=_tenant(), user_id=user.id,
    )


@router.get("/units/my-reviews")
async def my_reviews(
    user: User = permission_required("business:review:read"),
):
    return await list_reviewer_tasks(
        tenant_id=_tenant(), user_id=user.id,
    )


@router.get("/tenant-admin/reviews")
async def admin_reviews(
    user: User = permission_required("business:review:read"),
):
    return await list_admin_reviews(tenant_id=_tenant(), user=user)


@router.post("/units/{unit_id}/return-video")
async def return_video(
    unit_id: int,
    payload: ReturnVideoIn,
    user: User = permission_required("business:label:write"),
):
    return await return_unit_to_admin(
        tenant_id=_tenant(),
        unit_id=unit_id,
        user=user,
        reason_code=payload.reason_code,
        reason=payload.reason,
    )


@router.post("/units/{unit_id}/admin-review")
async def admin_review(
    unit_id: int,
    payload: AdminReviewActionIn,
    user: User = permission_required("business:review:approve"),
):
    return await admin_review_action(
        tenant_id=_tenant(),
        unit_id=unit_id,
        user=user,
        action=payload.action,
        reason=payload.reason,
        new_assignee_id=payload.new_assignee_id,
    )


@router.get("/units/escalated")
async def escalated(
    user: User = permission_required("business:stats:read"),
):
    return await list_escalated(tenant_id=_tenant(), user=user)


@router.get("/units/{unit_id}")
async def unit_detail(
    unit_id: int,
    user: User = permission_required("business:label:read"),
):
    return await get_unit_detail(
        tenant_id=_tenant(), unit_id=unit_id, user=user,
    )


@router.post("/units/{unit_id}/submit")
async def submit(
    unit_id: int,
    payload: SubmitIn,
    user: User = permission_required("business:label:write"),
):
    try:
        return await submit_unit(
            tenant_id=_tenant(),
            unit_id=unit_id,
            user=user,
            intervals=payload.intervals,
        )
    except ChallengeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/units/{unit_id}/draft")
async def save_draft(
    unit_id: int,
    payload: SubmitIn,
    user: User = permission_required("business:label:write"),
):
    try:
        return await save_unit_draft(
            tenant_id=_tenant(),
            unit_id=unit_id,
            user=user,
            intervals=payload.intervals,
        )
    except ChallengeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/units/{unit_id}/approve")
async def approve(
    unit_id: int,
    user: User = permission_required("business:review:approve"),
):
    return await approve_unit(
        tenant_id=_tenant(), unit_id=unit_id, user=user,
    )


@router.post("/units/{unit_id}/reject")
async def reject(
    unit_id: int,
    payload: RejectIn,
    user: User = permission_required("business:review:reject"),
):
    return await reject_unit(
        tenant_id=_tenant(), unit_id=unit_id,
        user=user, reason=payload.reason,
    )


@router.post("/units/{unit_id}/force-approve")
async def force_approve_route(
    unit_id: int,
    payload: ForceApproveIn,
    user: User = permission_required("business:review:approve"),
):
    return await force_approve(
        tenant_id=_tenant(), unit_id=unit_id,
        user=user, note=payload.note,
    )


@router.post("/units/{unit_id}/reassign")
async def reassign_route(
    unit_id: int,
    payload: ReassignIn,
    user: User = permission_required("business:anno-job:write"),
):
    return await reassign_unit(
        tenant_id=_tenant(), unit_id=unit_id, user=user,
        new_assignee_id=payload.new_assignee_id, reason=payload.reason,
    )


@router.post("/units/{unit_id}/mark-difficult")
async def mark_difficult_route(
    unit_id: int,
    payload: DifficultIn,
    user: User = permission_required("business:anno-job:write"),
):
    return await mark_difficult(
        tenant_id=_tenant(), unit_id=unit_id,
        user=user, reason=payload.reason,
    )


@router.get("/stats/daily-duration")
async def daily_stats(
    start_date: date,
    end_date: date,
    batch_id: Optional[int] = None,
    user: User = permission_required("business:stats:read"),
):
    await service.require_tenant_role(user, _tenant(), "admin", "tenant-admin")
    return await daily_duration(
        tenant_id=_tenant(), batch_id=batch_id,
        start_date=start_date, end_date=end_date,
    )


@router.get("/stats/export")
async def export_stats(
    batch_id: int,
    start_date: date,
    end_date: date,
    user: User = permission_required("business:export:read"),
):
    await service.require_tenant_role(user, _tenant(), "admin", "tenant-admin")
    content = await export_csv(
        tenant_id=_tenant(), batch_id=batch_id,
        start_date=start_date, end_date=end_date,
    )
    return StreamingResponse(
        iter([content.encode("utf-8-sig")]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": (
                f'attachment; filename="batch_{batch_id}_stats.csv"'
            )
        },
    )


@router.get("/tenant-admin/export/{kind}.csv")
async def export_workbench(
    kind: str,
    user: User = permission_required("business:export:read"),
):
    await service.require_tenant_role(user, _tenant(), "admin")
    content = await export_workbench_csv(tenant_id=_tenant(), kind=kind)
    return StreamingResponse(
        iter([content.encode("utf-8-sig")]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": (
                f'attachment; filename="video-{kind}-{date.today().isoformat()}.csv"'
            )
        },
    )


@router.get("/tenant-admin/video-results/{kind}")
async def video_results(
    kind: str,
    user: User = permission_required("business:stats:read"),
):
    return await list_video_results(
        tenant_id=_tenant(), user=user, kind=kind,
    )


@router.post("/media/upload")
async def upload_video(
    project_id: int = Form(...),
    file: UploadFile = File(...),
    user: User = permission_required("business:dataset:write"),
):
    tenant_id = _tenant()
    await service.require_tenant_role(user, _tenant(), "admin", "tenant-admin")
    media = await store_media_upload(
        tenant_id=tenant_id,
        project_id=project_id,
        user=user,
        upload=file,
    )
    return {
        "media_id": media.id,
        "file_id": media.id,
        "filename": media.filename,
        "path": f"/media/{media.id}/stream",
        "size": media.file_size,
        "duration": media.duration,
    }


@router.get("/media")
async def media_list(
    project_id: int,
    user: User = permission_required("business:dataset:read"),
):
    await service.require_tenant_role(user, _tenant(), "admin", "tenant-admin")
    return await list_media(tenant_id=_tenant(), project_id=project_id)


@router.get("/media/{media_id}/stream")
async def stream_video(
    media_id: int,
    range_header: Optional[str] = Header(None, alias="Range"),
    user: User = permission_required("business:dataset:read"),
):
    tenant_id = _tenant()
    media = await MediaFile.filter(
        tenant_id=tenant_id, id=media_id, status="ready",
    ).first()
    if media is None:
        raise HTTPException(status_code=404, detail="视频不存在")
    path = resolve_media_path(
        tenant_id=tenant_id, storage_path=media.storage_path,
    )

    size = path.stat().st_size
    start = 0
    end = size - 1
    status_code = 200
    if range_header:
        match = re.fullmatch(r"bytes=(\d*)-(\d*)", range_header.strip())
        if not match:
            raise HTTPException(status_code=416, detail="非法 Range")
        start_text, end_text = match.groups()
        if start_text:
            start = int(start_text)
        if end_text:
            end = min(int(end_text), size - 1)
        if not start_text and end_text:
            suffix = min(int(end_text), size)
            start = size - suffix
        if start >= size or start > end:
            raise HTTPException(
                status_code=416,
                detail="Range 超出视频大小",
                headers={"Content-Range": f"bytes */{size}"},
            )
        status_code = 206

    def body():
        remaining = end - start + 1
        with path.open("rb") as source:
            source.seek(start)
            while remaining > 0:
                chunk = source.read(min(CHUNK_SIZE, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk

    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(end - start + 1),
    }
    if status_code == 206:
        headers["Content-Range"] = f"bytes {start}-{end}/{size}"
    return StreamingResponse(
        body(), status_code=status_code,
        media_type=media.mime_type, headers=headers,
    )
