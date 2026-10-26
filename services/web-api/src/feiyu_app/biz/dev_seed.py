"""CE 版启动时 seed 开发数据:test 租户 + 把 admin 用户绑到 tenant-admin。

幂等。SAAS 版本(saas/platform/seed.py::seed_platform_data)做更多事——
建 platform/tenant/project 三个管理演示账号、3 个 feature flag、标注/审核测试账号
等测试账号、清理 legacy 'default' 租户——但 CE 不挂载 saas/ 包,因此本模块
只做最小 seed,保证 dev 环境开箱有一个可登录、可作业的 tenant-admin 账号。

调用时机:Tortoise schema 生成之后、seed_rbac 之后、init_user_admin 之后。
HAS_SAAS=True 时由 app.py 跳过本函数,改走 seed_platform_data。
"""
import asyncio
import shutil
from datetime import datetime
from pathlib import Path

from feiyu_conf.config import gConf

from ..dto.users import UserCreate
from ..log import logger
from .services.user import user_service
from .db.models import (
    Batch,
    MediaFile,
    PlatformFeatureFlag,
    PlatformTenant,
    Project,
    RejectHistory,
    Role,
    TaskSubmission,
    Unit,
    User,
    UserRole,
)
from ..config import settings
from .services.label_v2 import label_service
from ..utils.password import get_password_hash, verify_password

TEST_TENANT_SLUG = "test"

TEST_TENANT = {
    "name": "测试租户",
    "status": "active",
    "plan": "free",
    "quota": {"max_users": 50, "max_projects": 10, "max_storage_gb": 100},
    "settings": {},
}

DEFAULT_FLAGS = [
    {
        "key": "use_new_dashboard",
        "description": "新版仪表盘(2026 Q3 灰度)",
        "enabled": False,
        "rollout_pct": 0,
    },
    {
        "key": "cross_tenant_audit",
        "description": "跨租户审计导出",
        "enabled": True,
        "rollout_pct": 100,
    },
    {
        "key": "wasm_pcd_loader",
        "description": "WASM PCD 解码器(实验)",
        "enabled": False,
        "rollout_pct": 10,
    },
]

# 标注/审核账号用于完整链路测试；三个管理账号由 DEMO_IDENTITIES 显示为一键入口。
ROLE_TEST_ACCOUNTS = ("annotator", "reviewer")
DEMO_EMAIL_DOMAIN = "example.com"
DEMO_ACCOUNT_LOCALS = {
    "platform-admin": "avery.admin",
    "tenant-admin": "avery.tenant",
    "annotator": "avery.annotator",
    "reviewer": "avery.reviewer",
}
LEGACY_DEMO_ACCOUNT_LOCALS = {
    "platform-admin": "test-platform-admin",
    "tenant-admin": "test-tenant-admin",
    "annotator": "test-annotator",
    "reviewer": "test-reviewer",
}


async def _clone_builtin_roles(tenant_slug: str) -> list[str]:
    """把 business-scope 内置角色(tenant_id=None, is_builtin=True)克隆到本租户。

    副本 is_builtin=False, is_system=False,租户管理员可任意编辑/删除。
    幂等:已存在同名副本则同步权限,不重建。
    """
    templates = await Role.filter(
        scope="business", tenant_id=None, is_builtin=True,
    )
    cloned: list[str] = []
    for tmpl in templates:
        clone, _ = await Role.update_or_create(
            scope="business",
            tenant_id=tenant_slug,
            name=tmpl.name,
            defaults={
                "description": tmpl.description,
                "is_system": False,
                "is_builtin": False,
            },
        )
        tmpl_perms = await tmpl.permissions.all()
        await clone.permissions.clear()
        if tmpl_perms:
            await clone.permissions.add(*tmpl_perms)
        cloned.append(tmpl.name)
    return cloned


async def _bind_admin_to_tenant(tenant_slug: str) -> dict:
    """把 admin.user 配置的用户绑到本租户的 tenant-admin 角色。

    init_user_admin 已经创建了该用户(若不存在),这里只补 UserRole 绑定。
    若用户曾被设为 superuser,降级为普通租户管理员。
    """
    email = gConf["admin"]["user"]
    user = await user_service.get_by_email(email)
    if user is None:
        logger.warning(
            f"admin user {email} not found, skip tenant-admin binding "
            f"(init_user_admin should have created it)"
        )
        return {"email": email, "bound": False}

    if user.is_superuser:
        user.is_superuser = False
        await user.save(update_fields=["is_superuser"])
        logger.info(f"demoted {email} → tenant-admin only")

    role = await Role.filter(
        scope="business", tenant_id=tenant_slug, name="tenant-admin",
    ).first()
    if role is None:
        role = await Role.filter(
            scope="business", tenant_id=None, name="tenant-admin",
        ).first()
    if role is None:
        logger.warning(
            f"tenant-admin role not found, {email} left unbound; "
            f"check seed_rbac ordering"
        )
        return {"email": email, "bound": False}

    await UserRole.get_or_create(
        user_id=user.id, role_id=role.id, tenant_id=tenant_slug,
        defaults={"granted_by": None},
    )
    return {"email": email, "bound": True}


async def _migrate_legacy_demo_accounts(cfg: dict) -> None:
    """Rename legacy test accounts in place so existing task ownership survives."""
    for identity, legacy_local in LEGACY_DEMO_ACCOUNT_LOCALS.items():
        legacy_email = f"{legacy_local}@{cfg['test_email_domain']}"
        target_email = f"{DEMO_ACCOUNT_LOCALS[identity]}@{DEMO_EMAIL_DOMAIN}"
        legacy = await User.filter(email=legacy_email).first()
        target = await User.filter(email=target_email).first()
        if legacy is None or target is not None:
            continue
        legacy.email = target_email
        await legacy.save(update_fields=["email", "updated_at"])


async def _retire_legacy_generated_workers(cfg: dict) -> None:
    """Hide pre-Avery generated workers while preserving their task history."""
    legacy_domain = f"@{cfg['test_email_domain']}"
    users = await User.filter(
        is_active=True,
        deleted_at__isnull=True,
        email__endswith=legacy_domain,
    )
    now = datetime.utcnow()
    for user in users:
        local_part = (user.email or "").split("@", 1)[0]
        if not local_part.startswith(("annotator-", "reviewer-")):
            continue
        user.is_active = False
        user.deleted_at = now
        await user.save(update_fields=["is_active", "deleted_at", "updated_at"])


async def _ensure_role_test_account(role_name: str, cfg: dict) -> dict | None:
    """为某个 business-scope 角色建测试账号并绑到 test 租户的对应角色副本。"""
    email = f"{DEMO_ACCOUNT_LOCALS[role_name]}@{DEMO_EMAIL_DOMAIN}"
    user = await user_service.get_by_email(email)
    created = False
    if user is None:
        user = await user_service.create_user(UserCreate(
            email=email,
            password=cfg["test_password"],
            is_active=True,
            is_superuser=False,
        ))
        try:
            await user_service.process_after_create(user)
        except Exception as e:
            logger.warning(f"process_after_create failed for {email}: {e}")
        created = True
    elif not verify_password(cfg["test_password"], user.password):
        user.password = get_password_hash(cfg["test_password"])
        await user.save(update_fields=["password", "updated_at"])

    role = await Role.filter(
        scope="business", tenant_id=TEST_TENANT_SLUG, name=role_name,
    ).first()
    if role is None:
        role = await Role.filter(
            scope="business", tenant_id=None, name=role_name,
        ).first()
    if role is None:
        logger.warning(f"role {role_name} not seeded, skip binding for {email}")
        return None

    await UserRole.get_or_create(
        user_id=user.id, role_id=role.id, tenant_id=TEST_TENANT_SLUG,
        defaults={"granted_by": None},
    )
    return {"role": role_name, "email": email, "created": created}


async def _ensure_named_role_account(
    account_name: str,
    role_name: str,
    scope: str,
    cfg: dict,
    *,
    tenant_id: str | None,
    is_superuser: bool = False,
) -> dict | None:
    email = f"{account_name}@{DEMO_EMAIL_DOMAIN}"
    user = await user_service.get_by_email(email)
    if user is None:
        user = await user_service.create_user(UserCreate(
            email=email,
            password=cfg["test_password"],
            is_active=True,
            is_superuser=is_superuser,
        ))
        try:
            await user_service.process_after_create(user)
        except Exception as e:
            logger.warning(f"process_after_create failed for {email}: {e}")
    elif not verify_password(cfg["test_password"], user.password):
        user.password = get_password_hash(cfg["test_password"])
        await user.save(update_fields=["password", "updated_at"])

    role = await Role.filter(
        scope=scope, tenant_id=tenant_id if scope == "business" else None,
        name=role_name,
    ).first()
    if role is None:
        role = await Role.filter(
            scope=scope, tenant_id=None, name=role_name,
        ).first()
    if role is None:
        logger.warning(f"role {role_name} not seeded, skip binding for {email}")
        return None
    await UserRole.get_or_create(
        user_id=user.id,
        role_id=role.id,
        tenant_id=tenant_id,
        defaults={"granted_by": None},
    )
    return {"role": role_name, "email": email, "created": user.created_at}


async def _ensure_demo_media(
    *,
    tenant_slug: str,
    project_id: int,
    name: str,
    uploaded_by: int,
) -> MediaFile:
    target_name = f"pusht-{name}.mp4"
    legacy_names = [f"demo-{name}.webm", f"demo-{name}.mp4"]
    media = await MediaFile.filter(
        tenant_id=tenant_slug,
        project_id=project_id,
        filename__in=[target_name, *legacy_names],
    ).first()
    media_root = Path(settings.MEDIA_ROOT).expanduser().resolve()
    target_path = media_root / tenant_slug / target_name
    if not target_path.is_file():
        asset_path = (
            Path(__file__).resolve().parents[1]
            / "assets"
            / "pusht-file-000.mp4"
        )
        if not asset_path.is_file():
            raise FileNotFoundError(f"challenge demo video missing: {asset_path}")
        target_path.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(shutil.copyfile, asset_path, target_path)

    if media is None:
        return await MediaFile.create(
            tenant_id=tenant_slug,
            project_id=project_id,
            filename=target_name,
            storage_path=str(target_path),
            mime_type="video/mp4",
            file_size=target_path.stat().st_size,
            duration=2565.0,
            uploaded_by=uploaded_by,
            status="ready",
        )

    # Demo clones share the original storage path. Re-point all of them at the
    # browser-playable file without changing their Unit ids or history.
    old_path = media.storage_path
    await MediaFile.filter(
        tenant_id=tenant_slug,
        project_id=project_id,
        storage_path=old_path,
    ).update(
        storage_path=str(target_path),
        mime_type="video/mp4",
        file_size=target_path.stat().st_size,
        duration=2565.0,
    )
    media = await MediaFile.get(id=media.id)
    media.filename = target_name
    await media.save(update_fields=["filename", "updated_at"])
    return media


async def _clone_demo_media(
    *,
    tenant_slug: str,
    base: MediaFile,
    role: str,
    batch: Batch,
    uploaded_by: int,
) -> MediaFile:
    suffix = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    media = await MediaFile.create(
        tenant_id=tenant_slug,
        project_id=base.project_id,
        filename=f"pusht-{role}-{suffix}.mp4",
        storage_path=base.storage_path,
        mime_type=base.mime_type,
        file_size=base.file_size,
        duration=base.duration,
        uploaded_by=uploaded_by,
        status="ready",
    )
    batch.media_ids = [*(batch.media_ids or []), media.id]
    await batch.save(update_fields=["media_ids", "updated_at"])
    return media


async def _ensure_demo_annotation_task(tenant_slug: str, cfg: dict) -> None:
    """Keep one resettable pending video task for local annotator/reviewer demos."""
    annotator = await User.filter(
        email=f"{DEMO_ACCOUNT_LOCALS['annotator']}@{DEMO_EMAIL_DOMAIN}",
        is_active=True,
    ).first()
    reviewer = await User.filter(
        email=f"{DEMO_ACCOUNT_LOCALS['reviewer']}@{DEMO_EMAIL_DOMAIN}",
        is_active=True,
    ).first()
    if annotator is None or reviewer is None:
        return

    project = await Project.filter(
        tenant_id=tenant_slug, slug="demo-video-project",
    ).first()
    if project is None:
        project = await Project.create(
            tenant_id=tenant_slug,
            name="默认视频标注项目",
            slug="demo-video-project",
            status="active",
            settings={},
        )
    project_settings = dict(project.settings or {})
    default_video_config = {
        "instructions": "请标出机器人抓取、移动、放置和异常动作的完整时间段。",
        "require_label": True,
        "min_interval_seconds": 0.1,
        "label_mode": "preset",
        "label_template": "robotics",
        "fps": 10.0,
        "labels": ["抓取", "放置", "移动", "装配", "检测", "等待", "异常"],
        "return_reasons": [
            {"code": "blur", "label": "视频模糊"},
            {"code": "occluded", "label": "画面遮挡"},
            {"code": "blank", "label": "黑屏或空画面"},
            {"code": "incomplete", "label": "视频内容不完整"},
            {"code": "fps", "label": "帧率异常"},
            {"code": "no_action", "label": "没有可标注动作"},
            {"code": "other", "label": "其他原因"},
        ],
    }
    video_config = dict(project_settings.get("video_annotation") or {})
    for key, value in default_video_config.items():
        video_config.setdefault(key, value)
    project_settings["video_annotation"] = video_config
    if project.settings != project_settings:
        project.settings = project_settings
        await project.save(update_fields=["settings", "updated_at"])

    media = await _ensure_demo_media(
        tenant_slug=tenant_slug,
        project_id=project.id,
        name="default",
        uploaded_by=annotator.id,
    )
    review_media = await _ensure_demo_media(
        tenant_slug=tenant_slug,
        project_id=project.id,
        name="review",
        uploaded_by=annotator.id,
    )

    batch = await Batch.filter(
        tenant_id=tenant_slug, project_id=project.id, slug="demo-video-batch",
    ).first()
    if batch is None:
        batch = await Batch.create(
            tenant_id=tenant_slug,
            project_id=project.id,
            name="默认视频审核演示批次",
            slug="demo-video-batch",
            mission="videoEvents",
            seq_uuid="",
            media_ids=[media.id, review_media.id],
            assignee_strategy="round_robin",
            assignees=[annotator.id],
            reviewers=[reviewer.id],
            status="active",
        )
    elif review_media.id not in (batch.media_ids or []):
        batch.media_ids = [*(batch.media_ids or []), review_media.id]
        await batch.save(update_fields=["media_ids", "updated_at"])

    needs_assigned = not await Unit.filter(
        tenant_id=tenant_slug,
        assignee_id=annotator.id,
        status__in=["assigned", "in_progress", "rejected"],
    ).exists()
    needs_review = not await Unit.filter(
        tenant_id=tenant_slug,
        reviewer_id=reviewer.id,
        status__in=["submitted", "under_review"],
    ).exclude(assignee_id=reviewer.id).exists()

    unit = await Unit.filter(
        tenant_id=tenant_slug, batch_id=batch.id,
        seq=f"media:{media.id}", stream=media.filename,
        frame=0, mission="videoEvents",
    ).first()
    if needs_assigned:
        assigned_media = media
        if unit is not None:
            # Preserve approved/rejected history by creating a fresh queue item.
            assigned_media = await _clone_demo_media(
                tenant_slug=tenant_slug,
                base=media,
                role="annotate",
                batch=batch,
                uploaded_by=annotator.id,
            )
        unit = await Unit.create(
            tenant_id=tenant_slug,
            project_id=project.id,
            batch_id=batch.id,
            seq=f"media:{assigned_media.id}",
            stream=assigned_media.filename,
            frame=0,
            mission="videoEvents",
            assignee_id=annotator.id,
            assigned_at=datetime.utcnow(),
            status="assigned",
            stage_status="pending",
        )

    review_unit = await Unit.filter(
        tenant_id=tenant_slug, batch_id=batch.id,
        seq=f"media:{review_media.id}", stream=review_media.filename,
        frame=0, mission="videoEvents",
    ).first()
    if needs_review:
        active_review_media = review_media
        if review_unit is not None:
            active_review_media = await _clone_demo_media(
                tenant_slug=tenant_slug,
                base=review_media,
                role="review",
                batch=batch,
                uploaded_by=annotator.id,
            )
        review_unit = await Unit.create(
            tenant_id=tenant_slug,
            project_id=project.id,
            batch_id=batch.id,
            seq=f"media:{active_review_media.id}",
            stream=active_review_media.filename,
            frame=0,
            mission="videoEvents",
            assignee_id=annotator.id,
            reviewer_id=reviewer.id,
            assigned_at=datetime.utcnow(),
            review_assigned_at=datetime.utcnow(),
            submitted_at=datetime.utcnow(),
            status="under_review",
            stage_status="in_progress",
            data_version=1,
        )

    if needs_review:
        assert review_unit is not None
        now = datetime.utcnow()
        review_objects = [{
            "id": f"demo-review-{review_unit.id}",
            "label_uuid": f"demo-review-{review_unit.id}",
            "frame_intervals": [{"time_start": 0.0, "time_end": 1.0}],
            "attributes": {"label": "演示动作", "opType": "create"},
        }]
        await asyncio.to_thread(
            label_service._coll.insert_one,
            {
                "tenant_id": tenant_slug,
                "unit_id": review_unit.id,
                "project_id": project.id,
                "mission": "videoEvents",
                "version": 1,
                "creator": annotator.id,
                "created_at": now,
                "updated_at": now,
                "is_deleted": False,
                "objects": review_objects,
                "attrs": {"challenge": True, "demo": True},
            },
        )
        await TaskSubmission.create(
            tenant_id=tenant_slug,
            unit_id=review_unit.id,
            submitted_by=annotator.id,
            submitted_at=now,
            intervals=[{"start": 0.0, "end": 1.0, "label": "演示动作"}],
            total_duration=1.0,
            submission_date=now.date(),
            label_version=1,
            is_valid=True,
        )
        review_unit.status = "under_review"
        review_unit.stage_status = "in_progress"
        review_unit.assignee_id = annotator.id
        review_unit.reviewer_id = reviewer.id
        review_unit.review_assigned_at = now
        review_unit.submitted_at = now
        review_unit.data_version = 1
        await review_unit.save(update_fields=[
            "status", "stage_status", "assignee_id", "reviewer_id",
            "review_assigned_at", "submitted_at", "data_version", "updated_at",
        ])

    async def ensure_extra_state(
        status: str, label: str, reason: str | None = None,
    ) -> None:
        if await Unit.filter(
            tenant_id=tenant_slug,
            batch_id=batch.id,
            status=status,
        ).exists():
            return
        extra_media = await _clone_demo_media(
            tenant_slug=tenant_slug,
            base=media,
            role=status,
            batch=batch,
            uploaded_by=annotator.id,
        )
        now = datetime.utcnow()
        extra = await Unit.create(
            tenant_id=tenant_slug,
            project_id=project.id,
            batch_id=batch.id,
            seq=f"media:{extra_media.id}",
            stream=extra_media.filename,
            frame=0,
            mission="videoEvents",
            assignee_id=annotator.id,
            reviewer_id=reviewer.id if status in {"approved", "rejected", "escalated"} else None,
            assigned_at=now,
            review_assigned_at=now if status in {"approved", "rejected", "escalated"} else None,
            submitted_at=now if status in {"approved", "rejected", "escalated"} else None,
            reviewed_at=now if status in {"approved", "rejected", "escalated"} else None,
            approved_at=now if status == "approved" else None,
            status=status,
            stage_status="done" if status == "approved" else "in_progress",
            current_reject_reason=reason,
            data_version=1,
        )
        interval = {"start": 0.0, "end": 1.0, "label": label}
        await asyncio.to_thread(
            label_service._coll.insert_one,
            {
                "tenant_id": tenant_slug,
                "unit_id": extra.id,
                "project_id": project.id,
                "mission": "videoEvents",
                "version": 1,
                "creator": annotator.id,
                "created_at": now,
                "updated_at": now,
                "is_deleted": False,
                "objects": [{
                    "id": f"demo-{status}-{extra.id}",
                    "label_uuid": f"demo-{status}-{extra.id}",
                    "frame_intervals": [{
                        "time_start": interval["start"],
                        "time_end": interval["end"],
                    }],
                    "attributes": {"label": label, "opType": "create"},
                }],
                "attrs": {"challenge": True, "demo": True},
            },
        )
        if status == "approved":
            await TaskSubmission.create(
                tenant_id=tenant_slug,
                unit_id=extra.id,
                submitted_by=annotator.id,
                submitted_at=now,
                intervals=[interval],
                total_duration=1.0,
                submission_date=now.date(),
                label_version=1,
                is_valid=True,
            )
        if reason:
            await RejectHistory.create(
                tenant_id=tenant_slug,
                unit_id=extra.id,
                reviewer_id=annotator.id if status == "returned" else reviewer.id,
                rejected_at=now,
                reason=reason,
                label_version=1,
            )

    await ensure_extra_state("approved", "抓取")
    await ensure_extra_state("returned", "移动", "视频模糊")


def _test_tenant_cfg() -> dict:
    """test 租户测试账号配置。缺省回落 admin.password 与 feiyu.example.com。"""
    try:
        cfg = gConf["test_tenant"]
    except (KeyError, TypeError):
        cfg = {}
    return {
        "test_password": cfg.get("test_password") or gConf["admin"]["password"],
        "test_email_domain": cfg.get("test_email_domain") or "feiyu.example.com",
    }


async def ensure_demo_workbench_tasks(tenant_slug: str = TEST_TENANT_SLUG) -> None:
    """Public runtime entry point for local demo queue replenishment."""
    await _ensure_demo_annotation_task(tenant_slug, _test_tenant_cfg())


async def seed_dev_data() -> None:
    """CE 启动 seed:test 租户 + 3 feature flag + 角色克隆 + admin 绑定。

    幂等:重复启动只会补缺,不会重复建。
    """
    # 1) test 租户
    await PlatformTenant.update_or_create(
        slug=TEST_TENANT_SLUG,
        defaults=dict(TEST_TENANT),
    )

    # 2) feature flags(仅 dev 参考用,CE 不加载 saas/ 运营面 UI)
    for spec in DEFAULT_FLAGS:
        await PlatformFeatureFlag.update_or_create(
            key=spec["key"],
            defaults={
                "description": spec["description"],
                "enabled": spec["enabled"],
                "rollout_pct": spec["rollout_pct"],
                "included_tenants": [],
                "excluded_tenants": [],
            },
        )

    # 3) 克隆 business-scope 内置角色到 test 租户
    roles_cloned = await _clone_builtin_roles(TEST_TENANT_SLUG)

    # 4) 把 admin.user(prod@feiyu.example.com)绑到 test 租户 tenant-admin
    admin_info = await _bind_admin_to_tenant(TEST_TENANT_SLUG)

    # 5) 建三个管理演示账号；平台账号不绑定租户，租户/项目账号绑定 test。
    cfg = _test_tenant_cfg()
    await _migrate_legacy_demo_accounts(cfg)
    await _retire_legacy_generated_workers(cfg)
    test_users: dict[str, dict] = {}
    for account_name, role_name, scope, tenant_id, is_superuser in (
        ("avery.admin", "platform-admin", "platform", None, True),
        ("avery.tenant", "admin", "admin", TEST_TENANT_SLUG, False),
    ):
        info = await _ensure_named_role_account(
            account_name, role_name, scope, cfg,
            tenant_id=tenant_id, is_superuser=is_superuser,
        )
        if info:
            test_users[role_name] = info
    for role_name in ROLE_TEST_ACCOUNTS:
        info = await _ensure_role_test_account(role_name, cfg)
        if info:
            test_users[role_name] = info

    await _ensure_demo_annotation_task(TEST_TENANT_SLUG, cfg)

    # Remove the former split project-admin demo identity so a fresh/restarted
    # dev environment exposes exactly four test users.
    legacy_project_admin = await user_service.get_by_email(
        f"test-project-admin@{cfg['test_email_domain']}"
    )
    if legacy_project_admin is not None:
        await UserRole.filter(user_id=legacy_project_admin.id).delete()
        legacy_project_admin = await User.filter(id=legacy_project_admin.id).first()
        legacy_project_admin.is_active = False
        legacy_project_admin.deleted_at = datetime.utcnow()
        await legacy_project_admin.save(
            update_fields=["is_active", "deleted_at", "updated_at"]
        )

    # The configured first admin is the single tenant manager in this model.
    # Keep any previous project-admin binding removed from the local test tenant.
    configured_admin = await user_service.get_by_email(gConf["admin"]["user"])
    legacy_project_role = await Role.filter(
        scope="business", tenant_id=TEST_TENANT_SLUG, name="tenant-admin",
    ).first()
    if configured_admin is not None and legacy_project_role is not None:
        await UserRole.filter(
            user_id=configured_admin.id,
            role_id=legacy_project_role.id,
            tenant_id=TEST_TENANT_SLUG,
        ).delete()

    logger.info(
        f"dev seed done: tenant={TEST_TENANT_SLUG}; "
        f"admin={admin_info['email']} (bound={admin_info['bound']}); "
        f"3 feature flags; roles_cloned={roles_cloned}; "
        f"test_users={ {k: v['email'] for k, v in test_users.items()} }"
    )
