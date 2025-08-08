import os
from open_webui.models.settings import AppSettings


def is_classroom_enabled() -> bool:
    raw = os.environ.get("CLASSROOM_MODE")
    if raw is not None:
        val = raw.strip().lower()
        if val in ("true", "1", "yes", "on"):
            return True
        if val in ("false", "0", "no", "off"):
            return False
    row = AppSettings.get("CLASSROOM_MODE")
    if row and isinstance(row.value, dict):
        return bool(row.value.get("enabled", False))
    return False
