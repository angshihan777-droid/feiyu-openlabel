"""
rest api
"""

__author__ = "Zhang Lizhi"
__date__ = "2024-09-29 甲辰年 八月廿七"

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Annotated

from feiyu_app.dto.users import UpdateAccount
from .ctx import CTX_USER_ID
from ..biz.db.models import User
from ..biz.rbac.resolver import compute_user_permissions, get_user_role_names
from ..dto.response import SuccessJson
from ..biz.services.user import user_service

app = APIRouter()


@app.post("/config", summary="登录用户的全局配置", tags=["system"])
async def system_config():
    conf = {}
    return SuccessJson(data=conf)

@app.post("/user_info", summary="登录用户的信息")
async def get_user():
    user_id = CTX_USER_ID.get()
    if not user_id:
        raise HTTPException(status_code=401, detail="未登录")
    user_obj = await User.filter(id=user_id).first()
    if user_obj is None:
        raise HTTPException(status_code=401, detail="用户不存在")
    user_dict = await user_obj.to_dict(exclude_fields=["password"])
    roles = sorted(await get_user_role_names(user_obj))
    permissions = sorted(await compute_user_permissions(user_obj))

    data = {
        "user": user_dict,
        "roles": roles,
        "permissions": permissions,
    }

    return SuccessJson(data=data)

class UpdatePassword(BaseModel):
    old_password: str
    new_password: Annotated[str, Field(max_length=50, min_length=6)]
    new_password2: Annotated[str, Field(max_length=50, min_length=6)]

@app.post("/update_password", summary="修改密码", tags=["system"])
async def update_password(dto: UpdatePassword):
    await user_service.update_password(
        CTX_USER_ID.get(), dto.old_password, dto.new_password,
    )
    return SuccessJson(statusText="更新成功")

@app.post("/update_account", summary="修改账号信息", tags=["system"])
async def update_account(dto: UpdateAccount):
    await user_service.update_account(CTX_USER_ID.get(), dto)
    return SuccessJson(statusText="更新成功")
