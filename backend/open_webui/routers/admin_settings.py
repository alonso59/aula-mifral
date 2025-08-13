from fastapi import APIRouter, Depends
from pydantic import BaseModel

from open_webui.models.settings import AppSettings
from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.env import CLASSROOM_MODE
from open_webui.utils.feature_flags import is_classroom_enabled


router = APIRouter()


class ClassroomToggle(BaseModel):
    enabled: bool


@router.get("/classroom")
def get_classroom_setting(user=Depends(get_verified_user)):
    # Allow verified users (teachers & admins) to read the feature toggle.
    # Only admins are allowed to modify it (PUT remains admin-only).
    enabled = bool(CLASSROOM_MODE or is_classroom_enabled())
    return {"enabled": enabled}


@router.put("/classroom")
def set_classroom_setting(toggle: ClassroomToggle, user=Depends(get_admin_user)):
    AppSettings.upsert("CLASSROOM_MODE", {"enabled": bool(toggle.enabled)})
    return {"enabled": bool(toggle.enabled)}
