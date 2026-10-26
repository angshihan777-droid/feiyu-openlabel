from datetime import date, datetime
import io
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from fastapi import HTTPException
from starlette.datastructures import UploadFile
from tortoise import Tortoise

from feiyu_app.biz.challenge import service
from feiyu_app.biz.services.batch import BatchService, BatchCreateIn, SpawnUnitsIn
from feiyu_app.biz.db.models import (
    Batch,
    MediaFile,
    PlatformTenant,
    Project,
    RejectHistory,
    Role,
    TaskSubmission,
    Unit,
    User,
    UserRole,
)
from feiyu_app.biz.services.label_v2 import label_service
from feiyu_app.biz.schema_migrations import apply_challenge_schema_migration
from feiyu_app.utils.password import verify_password


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


async def _user(email: str, role_name: str) -> User:
    user = await User.create(email=email, password="x", is_active=True)
    role, _ = await Role.get_or_create(
        name=role_name,
        scope="business",
        tenant_id="tenant-a",
        defaults={"description": role_name, "is_system": False, "is_builtin": False},
    )
    await UserRole.create(
        user_id=user.id, role_id=role.id, tenant_id="tenant-a",
    )
    return user


async def _workflow_fixture():
    annotator = await _user("annotator@test.local", "annotator")
    reviewer = await _user("reviewer@test.local", "reviewer")
    admin = await _user("admin@test.local", "tenant-admin")
    await Project.create(
        tenant_id="tenant-a",
        name="project",
        slug="project",
        status="active",
    )
    batch = await Batch.create(
        tenant_id="tenant-a",
        project_id=1,
        name="batch",
        slug="batch",
        mission="videoEvents",
        seq_uuid="",
        assignees=[annotator.id],
        reviewers=[reviewer.id],
        assignee_strategy="round_robin",
        status="active",
    )
    media = await MediaFile.create(
        tenant_id="tenant-a",
        project_id=1,
        filename="task.mp4",
        storage_path="/tmp/task.mp4",
        file_size=10,
        duration=20.0,
        uploaded_by=admin.id,
    )
    unit = await Unit.create(
        tenant_id="tenant-a",
        project_id=1,
        batch_id=batch.id,
        seq=f"media:{media.id}",
        stream=f"video-{media.id}",
        frame=0,
        mission="videoEvents",
        assignee_id=annotator.id,
        status="assigned",
        stage_status="pending",
    )
    return annotator, reviewer, admin, batch, media, unit


@pytest.mark.asyncio
async def test_annotator_and_reviewer_views_are_mutually_anonymous(monkeypatch):
    annotator, reviewer, _, _, _, unit = await _workflow_fixture()
    unit.reviewer_id = reviewer.id
    unit.status = "rejected"
    await unit.save(update_fields=["reviewer_id", "status"])
    monkeypatch.setattr(
        label_service,
        "get_label",
        AsyncMock(return_value=SimpleNamespace(
            version=1,
            objects=[{
                "id": "a",
                "frame_intervals": [{"time_start": 0, "time_end": 5}],
            }],
        )),
    )

    annotator_tasks = await service.list_annotator_tasks(
        tenant_id="tenant-a", user_id=annotator.id,
    )
    unit.status = "under_review"
    await unit.save(update_fields=["status"])
    reviewer_tasks = await service.list_reviewer_tasks(
        tenant_id="tenant-a", user_id=reviewer.id,
    )

    assert "reviewer_id" not in annotator_tasks["tasks"][0]
    assert annotator_tasks["tasks"][0]["reviewer_name"] == "匿名"
    assert "assignee_id" not in reviewer_tasks["tasks"][0]
    assert reviewer_tasks["tasks"][0]["annotator_name"] == "匿名"


@pytest.mark.asyncio
async def test_submit_snapshots_duration_and_assigns_reviewer(monkeypatch):
    annotator, reviewer, _, _, _, unit = await _workflow_fixture()
    monkeypatch.setattr(
        label_service,
        "save_label",
        AsyncMock(return_value=SimpleNamespace(version=1)),
    )

    result = await service.submit_unit(
        tenant_id="tenant-a",
        unit_id=unit.id,
        user=annotator,
        intervals=[
            {"start": 0, "end": 2.5, "label": "抓取"},
            {"start": 3, "end": 7.25, "label": "放置"},
        ],
    )

    refreshed = await Unit.get(id=unit.id)
    snapshot = await TaskSubmission.get(unit_id=unit.id)
    assert result["total_duration"] == pytest.approx(6.75)
    assert refreshed.status == "under_review"
    assert refreshed.reviewer_id == reviewer.id
    assert snapshot.is_valid is True
    assert snapshot.submission_date == datetime.utcnow().date()


@pytest.mark.asyncio
async def test_save_draft_persists_intervals_without_creating_submission(monkeypatch):
    annotator, _, _, _, _, unit = await _workflow_fixture()
    monkeypatch.setattr(
        label_service,
        "save_label",
        AsyncMock(return_value=SimpleNamespace(version=1)),
    )

    result = await service.save_unit_draft(
        tenant_id="tenant-a",
        unit_id=unit.id,
        user=annotator,
        intervals=[{"start": 0.5, "end": 2.0, "label": "草稿动作"}],
    )

    refreshed = await Unit.get(id=unit.id)
    assert result["version"] == 1
    assert refreshed.status == "in_progress"
    assert refreshed.data_version == 1
    assert await TaskSubmission.filter(unit_id=unit.id).count() == 0


@pytest.mark.asyncio
async def test_tenant_admin_creates_and_removes_login_worker(monkeypatch):
    from feiyu_app.biz.challenge import tenant as tenant_module

    _, _, admin, _, _, _ = await _workflow_fixture()
    monkeypatch.setattr(
        tenant_module.user_service,
        "process_after_create",
        AsyncMock(return_value=None),
    )

    created = await service.create_tenant_worker(
        tenant_id="tenant-a", role_name="annotator", user=admin,
    )
    worker = await User.get(id=created["id"])
    assert created["role"] == "annotator"
    assert created["email"].startswith("avery.annotator-")
    assert verify_password(created["password"], worker.password)
    assert await UserRole.filter(
        user_id=worker.id, tenant_id="tenant-a",
    ).exists()

    await service.remove_tenant_worker(
        tenant_id="tenant-a", target_user_id=worker.id, user=admin,
    )
    worker = await User.get(id=worker.id)
    assert worker.is_active is False
    assert worker.deleted_at is not None


@pytest.mark.asyncio
async def test_project_preset_labels_are_enforced(monkeypatch):
    annotator, _, admin, _, _, unit = await _workflow_fixture()
    config = await service.update_project_video_config(
        tenant_id="tenant-a",
        project_id=unit.project_id,
        user=admin,
        value={
            "instructions": "机器人动作",
            "label_mode": "preset",
            "labels": ["抓取", "放置"],
            "return_reasons": [{"code": "blur", "label": "视频模糊"}],
        },
    )
    assert config["labels"] == ["抓取", "放置"]

    with pytest.raises(HTTPException, match="预设标签"):
        await service.submit_unit(
            tenant_id="tenant-a",
            unit_id=unit.id,
            user=annotator,
            intervals=[{"start": 0, "end": 1, "label": "自定义标签"}],
        )


@pytest.mark.asyncio
async def test_annotator_return_enters_admin_queue_and_problem_csv(monkeypatch):
    annotator, _, admin, _, _, unit = await _workflow_fixture()
    monkeypatch.setattr(
        label_service,
        "get_label",
        AsyncMock(return_value=SimpleNamespace(version=0, objects=[])),
    )
    await service.update_project_video_config(
        tenant_id="tenant-a",
        project_id=unit.project_id,
        user=admin,
        value={
            "label_mode": "free",
            "return_reasons": [
                {"code": "blur", "label": "视频模糊"},
                {"code": "other", "label": "其他原因"},
            ],
        },
    )

    returned = await service.return_unit_to_admin(
        tenant_id="tenant-a",
        unit_id=unit.id,
        user=annotator,
        reason_code="blur",
    )
    assert returned["status"] == "returned"
    from feiyu_app.apps.ctx import CTX_TENANT_ID

    token = CTX_TENANT_ID.set("tenant-a")
    try:
        queue = await service.list_admin_reviews(
            tenant_id="tenant-a", user=admin,
        )
    finally:
        CTX_TENANT_ID.reset(token)
    assert queue["tasks"][0]["reason"] == "视频模糊"

    await service.admin_review_action(
        tenant_id="tenant-a",
        unit_id=unit.id,
        user=admin,
        action="confirm_issue",
        reason="管理员确认画面模糊",
    )
    refreshed = await Unit.get(id=unit.id)
    assert refreshed.status == "source_confirmed"
    problem_csv = await service.export_workbench_csv(
        tenant_id="tenant-a", kind="problem",
    )
    assert "source_confirmed" in problem_csv
    assert "管理员确认画面模糊" in problem_csv


@pytest.mark.asyncio
async def test_overview_video_results_split_pass_and_fail(monkeypatch):
    annotator, reviewer, admin, _, media, unit = await _workflow_fixture()
    now = datetime.utcnow()
    unit.status = "approved"
    unit.reviewer_id = reviewer.id
    unit.approved_at = now
    await unit.save(update_fields=["status", "reviewer_id", "approved_at"])
    await TaskSubmission.create(
        tenant_id="tenant-a",
        unit_id=unit.id,
        submitted_by=annotator.id,
        submitted_at=now,
        intervals=[{"start": 0, "end": 2, "label": "抓取"}],
        total_duration=2,
        submission_date=now.date(),
        label_version=1,
        is_valid=True,
    )

    success = await service.list_video_results(
        tenant_id="tenant-a", user=admin, kind="success",
    )
    assert success["total"] == 1
    assert success["items"][0]["video_name"] == media.filename
    assert success["items"][0]["total_duration"] == 2

    monkeypatch.setattr(
        label_service,
        "get_label",
        AsyncMock(return_value=SimpleNamespace(version=0, objects=[])),
    )
    unit.status = "returned"
    unit.current_reject_reason = "视频模糊"
    await unit.save(update_fields=["status", "current_reject_reason"])
    problem = await service.list_video_results(
        tenant_id="tenant-a", user=admin, kind="problem",
    )
    assert problem["total"] == 1
    assert problem["items"][0]["reason"] == "视频模糊"


@pytest.mark.asyncio
async def test_platform_tenant_delete_archives_users_and_roles():
    from feiyu_app.apps.platform_tenants import delete_platform_tenant

    platform_user = await User.create(
        email="platform@test.local", password="x", is_superuser=True,
    )
    tenant = await PlatformTenant.create(
        name="Delete me", slug="delete-me", status="active",
    )
    role, _ = await Role.get_or_create(
        name="annotator",
        scope="business",
        tenant_id="delete-me",
        defaults={"description": "annotator"},
    )
    worker = await _user("worker@test.local", "reviewer")
    await UserRole.create(
        user_id=worker.id, role_id=role.id, tenant_id=tenant.slug,
    )

    result = await delete_platform_tenant(tenant.slug, user=platform_user)

    refreshed = await PlatformTenant.get(id=tenant.id)
    worker = await User.get(id=worker.id)
    assert result["slug"] == tenant.slug
    assert refreshed.status == "archived"
    assert worker.is_active is False
    assert await UserRole.filter(tenant_id=tenant.slug).count() == 0


@pytest.mark.asyncio
async def test_third_reject_escalates_and_admin_can_force_approve(monkeypatch):
    annotator, reviewer, admin, _, _, unit = await _workflow_fixture()
    version = {"value": 0}

    async def fake_save(**kwargs):
        version["value"] += 1
        return SimpleNamespace(version=version["value"])

    monkeypatch.setattr(label_service, "save_label", AsyncMock(side_effect=fake_save))
    intervals = [{"start": 0, "end": 1, "label": "测试动作"}]

    for expected_count in (1, 2, 3):
        await service.submit_unit(
            tenant_id="tenant-a",
            unit_id=unit.id,
            user=annotator,
            intervals=intervals,
        )
        result = await service.reject_unit(
            tenant_id="tenant-a",
            unit_id=unit.id,
            user=reviewer,
            reason=f"reason-{expected_count}",
        )
        assert result["reject_count"] == expected_count

    assert result["status"] == "escalated"
    assert await RejectHistory.filter(unit_id=unit.id).count() == 3

    approved = await service.force_approve(
        tenant_id="tenant-a", unit_id=unit.id, user=admin, note="accepted",
    )
    assert approved["status"] == "approved"
    assert await TaskSubmission.filter(unit_id=unit.id, is_valid=True).count() == 1
    stats = await service.daily_duration(
        tenant_id="tenant-a",
        batch_id=unit.batch_id,
        start_date=datetime.utcnow().date(),
        end_date=datetime.utcnow().date(),
    )
    assert stats["total_duration"] == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_tenant_boundary_returns_not_found(monkeypatch):
    annotator, _, _, _, _, unit = await _workflow_fixture()

    with pytest.raises(HTTPException) as exc:
        await service.get_unit_detail(
            tenant_id="tenant-b", unit_id=unit.id, user=annotator,
        )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_daily_duration_excludes_invalid_snapshot(monkeypatch):
    annotator, reviewer, _, _, _, unit = await _workflow_fixture()
    monkeypatch.setattr(
        label_service,
        "save_label",
        AsyncMock(side_effect=[
            SimpleNamespace(version=1),
            SimpleNamespace(version=2),
        ]),
    )
    today = date.today()
    await TaskSubmission.create(
        tenant_id="tenant-a",
        unit_id=unit.id,
        submitted_by=annotator.id,
        submitted_at=unit.created_at,
        intervals=[{"start": 0, "end": 2}],
        total_duration=2,
        submission_date=today,
        label_version=1,
        is_valid=False,
    )
    await TaskSubmission.create(
        tenant_id="tenant-a",
        unit_id=unit.id,
        submitted_by=annotator.id,
        submitted_at=unit.created_at,
        intervals=[{"start": 0, "end": 5}],
        total_duration=5,
        submission_date=today,
        label_version=2,
        is_valid=True,
    )

    result = await service.daily_duration(
        tenant_id="tenant-a",
        batch_id=unit.batch_id,
        start_date=today,
        end_date=today,
    )
    assert result["total_duration"] == 5


@pytest.mark.asyncio
async def test_media_upload_is_tenant_scoped_and_rejects_oversize(
    monkeypatch, tmp_path,
):
    _, _, admin, _, _, _ = await _workflow_fixture()
    monkeypatch.setattr(
        "feiyu_app.biz.challenge.submission.settings.MEDIA_ROOT",
        str(tmp_path),
    )
    monkeypatch.setattr(
        "feiyu_app.biz.challenge.submission._probe_video_duration",
        lambda _path: None,
    )

    upload = UploadFile(
        file=io.BytesIO(b"video"),
        filename="../outside.mp4",
        headers={"content-type": "video/mp4"},
    )
    media = await service.store_media_upload(
        tenant_id="tenant-a",
        project_id=1,
        user=admin,
        upload=upload,
    )

    assert media.filename == "outside.mp4"
    assert media.storage_path.startswith(str((tmp_path / "tenant-a").resolve()))
    assert (tmp_path / "outside.mp4").exists() is False
    assert service.resolve_media_path(
        tenant_id="tenant-a", storage_path=media.storage_path,
    ).is_file()

    with pytest.raises(HTTPException) as cross_tenant:
        service.resolve_media_path(
            tenant_id="tenant-b", storage_path=media.storage_path,
        )
    assert cross_tenant.value.status_code == 403

    too_large = UploadFile(
        file=io.BytesIO(b"1234"),
        filename="large.mp4",
        headers={"content-type": "video/mp4"},
    )
    with pytest.raises(HTTPException) as oversize:
        await service.store_media_upload(
            tenant_id="tenant-a",
            project_id=1,
            user=admin,
            upload=too_large,
            max_bytes=3,
        )
    assert oversize.value.status_code == 413


@pytest.mark.asyncio
async def test_video_batch_spawns_one_unit_per_video_with_round_robin():
    annotator_one = await _user("annotator-one@test.local", "annotator")
    annotator_two = await _user("annotator-two@test.local", "annotator")
    reviewer = await _user("reviewer@test.local", "reviewer")
    admin = await _user("admin@test.local", "tenant-admin")
    await Project.create(
        tenant_id="tenant-a", name="project", slug="project", status="active",
    )
    first = await MediaFile.create(
        tenant_id="tenant-a", project_id=1, filename="first.mp4",
        storage_path="/tmp/first.mp4", file_size=1, uploaded_by=admin.id,
    )
    second = await MediaFile.create(
        tenant_id="tenant-a", project_id=1, filename="second.mp4",
        storage_path="/tmp/second.mp4", file_size=1, uploaded_by=admin.id,
    )
    batch = await Batch.create(
        tenant_id="tenant-a", project_id=1, name="media", slug="media",
        mission="videoEvents", seq_uuid="",
        media_ids=[first.id, second.id],
        assignees=[annotator_one.id, annotator_two.id],
        reviewers=[reviewer.id],
        assignee_strategy="round_robin", status="pending",
        sampling_rate=1.0,
    )

    from feiyu_app.apps.ctx import CTX_TENANT_ID

    token = CTX_TENANT_ID.set("tenant-a")
    try:
        result = await BatchService().spawn_units(
            batch_id=batch.id, payload=SpawnUnitsIn(), redis=None,
        )
        units = await Unit.filter(batch_id=batch.id).order_by("id")
    finally:
        CTX_TENANT_ID.reset(token)

    assert result["created"] == 2
    assert len(units) == 2
    assert [unit.assignee_id for unit in units] == [
        annotator_one.id, annotator_two.id,
    ]


@pytest.mark.asyncio
async def test_batch_rejects_same_person_in_annotator_and_reviewer_pools():
    annotator = await _user("annotator@test.local", "annotator")
    await Project.create(
        tenant_id="tenant-a", name="project", slug="project", status="active",
    )
    payload = BatchCreateIn(
        name="invalid",
        slug="invalid",
        mission="videoEvents",
        media_ids=[1],
        assignee_strategy="round_robin",
        assignees=[annotator.id],
        reviewers=[annotator.id],
    )

    from feiyu_app.apps.ctx import CTX_TENANT_ID

    token = CTX_TENANT_ID.set("tenant-a")
    try:
        with pytest.raises(Exception, match="角色分离"):
            await BatchService().create_batch(project_id=1, payload=payload)
    finally:
        CTX_TENANT_ID.reset(token)


@pytest.mark.asyncio
async def test_postgres_schema_migration_is_safe_noop_on_sqlite():
    await apply_challenge_schema_migration()


@pytest.mark.asyncio
async def test_demo_fixture_replenishes_both_workbenches(monkeypatch, tmp_path):
    from types import SimpleNamespace

    from feiyu_app.config import Conf
    from feiyu_app.biz import dev_seed

    await _user("avery.annotator@example.com", "annotator")
    await _user("avery.reviewer@example.com", "reviewer")
    demo_path = tmp_path / "test" / "demo-default.webm"
    demo_path.parent.mkdir(parents=True)
    demo_path.write_bytes(b"video")
    monkeypatch.setattr(
        "feiyu_app.biz.dev_seed.settings.MEDIA_ROOT",
        str(tmp_path),
    )
    monkeypatch.setattr(
        Conf,
        "MG_UNIT_LABEL",
        SimpleNamespace(
            insert_one=lambda _document: None,
        ),
    )

    cfg = {"test_password": "x", "test_email_domain": "demo.test"}
    await dev_seed._ensure_demo_annotation_task("test", cfg)
    assert await Unit.filter(
        tenant_id="test", status__in=["assigned", "in_progress", "rejected"],
    ).count() == 1
    assert await Unit.filter(
        tenant_id="test", status__in=["submitted", "under_review"],
    ).count() == 1
    assert await Unit.filter(tenant_id="test", status="approved").count() == 1
    assert await Unit.filter(tenant_id="test", status="returned").count() == 1

    await Unit.filter(tenant_id="test").update(status="approved")
    await dev_seed._ensure_demo_annotation_task("test", cfg)

    assert await Unit.filter(tenant_id="test", status="assigned").count() == 1
    assert await Unit.filter(tenant_id="test", status="under_review").count() == 1
    assert await Unit.filter(tenant_id="test", status="approved").count() == 4
    assert await Unit.filter(tenant_id="test", status="returned").count() == 1
    assert await Unit.filter(tenant_id="test").count() == 7
    assert await TaskSubmission.filter(tenant_id="test").count() == 3


@pytest.mark.asyncio
async def test_demo_fixture_hides_pre_avery_generated_workers():
    from feiyu_app.biz import dev_seed

    legacy = await User.create(
        email="annotator-legacy123@demo.test",
        password="x",
        is_active=True,
    )
    current = await User.create(
        email="avery.annotator@example.com",
        password="x",
        is_active=True,
    )

    await dev_seed._retire_legacy_generated_workers(
        {"test_email_domain": "demo.test"},
    )

    legacy = await User.get(id=legacy.id)
    current = await User.get(id=current.id)
    assert legacy.is_active is False
    assert legacy.deleted_at is not None
    assert current.is_active is True
