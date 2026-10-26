"""Compatibility facade for the split challenge workflow modules.

HTTP routes and existing imports continue to use this module, while the
implementation lives in responsibility-focused modules.
"""

from ...config import settings
from ..services.user import user_service
from .admin_review import (
    admin_review_action,
    force_approve,
    list_escalated,
    mark_difficult,
    reassign_unit,
)
from .assignment import (
    get_unit_detail,
    list_annotator_tasks,
    list_reviewer_tasks,
    role_pools,
)
from .common import (
    ChallengeError,
    display_name,
    get_tenant_unit,
    has_role,
    has_tenant_role,
    require_role,
    require_tenant_role,
)
from .reporting import (
    daily_duration,
    export_csv,
    export_workbench_csv,
    list_video_results,
)
from .review import (
    approve_unit,
    list_admin_reviews,
    reject_unit,
    return_unit_to_admin,
)
from .submission import (
    ALLOWED_VIDEO_EXTENSIONS,
    MAX_UPLOAD_BYTES,
    UPLOAD_CHUNK_SIZE,
    _probe_video_duration,
    list_media,
    resolve_media_path,
    save_unit_draft,
    store_media_upload,
    submit_unit,
)
from .tenant import (
    DEFAULT_ANNOTATION_SETTINGS,
    DEFAULT_RETURN_REASONS,
    create_tenant_worker,
    get_project_video_config,
    get_tenant_annotation_settings,
    normalize_annotation_settings,
    normalize_video_config,
    remove_tenant_worker,
    tenant_admin_members,
    tenant_admin_overview,
    update_project_video_config,
    update_tenant_annotation_settings,
)

__all__ = [
    "ALLOWED_VIDEO_EXTENSIONS",
    "ChallengeError",
    "DEFAULT_ANNOTATION_SETTINGS",
    "DEFAULT_RETURN_REASONS",
    "MAX_UPLOAD_BYTES",
    "UPLOAD_CHUNK_SIZE",
    "_probe_video_duration",
    "admin_review_action",
    "approve_unit",
    "create_tenant_worker",
    "daily_duration",
    "display_name",
    "export_csv",
    "export_workbench_csv",
    "force_approve",
    "get_project_video_config",
    "get_tenant_annotation_settings",
    "get_tenant_unit",
    "get_unit_detail",
    "has_role",
    "has_tenant_role",
    "list_admin_reviews",
    "list_annotator_tasks",
    "list_escalated",
    "list_media",
    "list_reviewer_tasks",
    "list_video_results",
    "mark_difficult",
    "normalize_annotation_settings",
    "normalize_video_config",
    "reassign_unit",
    "reject_unit",
    "remove_tenant_worker",
    "require_role",
    "require_tenant_role",
    "resolve_media_path",
    "return_unit_to_admin",
    "role_pools",
    "save_unit_draft",
    "settings",
    "store_media_upload",
    "submit_unit",
    "tenant_admin_members",
    "tenant_admin_overview",
    "update_project_video_config",
    "update_tenant_annotation_settings",
    "user_service",
]
