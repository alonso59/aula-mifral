from fastapi import APIRouter, Depends
from pydantic import BaseModel

from open_webui.models.settings import AppSettings
from open_webui.utils.auth import get_admin_user


router = APIRouter()


class ClassroomToggle(BaseModel):
    enabled: bool


@router.get("/classroom")
def get_classroom_setting(user=Depends(get_admin_user)):
    row = AppSettings.get("CLASSROOM_MODE")
    enabled = False
    if row and isinstance(row.value, dict):
        enabled = bool(row.value.get("enabled", False))
    return {"enabled": enabled}


@router.put("/classroom")
def set_classroom_setting(toggle: ClassroomToggle, user=Depends(get_admin_user)):
    AppSettings.upsert("CLASSROOM_MODE", {"enabled": bool(toggle.enabled)})
    return {"enabled": bool(toggle.enabled)}
