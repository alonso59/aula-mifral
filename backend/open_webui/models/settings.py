import time
from typing import Optional

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, String, JSON, BigInteger

from open_webui.internal.db import Base, get_db


class AppSetting(Base):
    __tablename__ = "app_settings"

    key = Column(String, primary_key=True)
    value = Column(JSON, nullable=True)
    updated_at = Column(BigInteger, nullable=False)


class AppSettingModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    key: str
    value: Optional[dict] = None
    updated_at: int


class AppSettingsTable:
    def get(self, key: str) -> Optional[AppSettingModel]:
        with get_db() as db:
            row = db.get(AppSetting, key)
            return AppSettingModel.model_validate(row) if row else None

    def upsert(self, key: str, value: dict) -> AppSettingModel:
        with get_db() as db:
            row = db.get(AppSetting, key)
            now = int(time.time())
            if row:
                row.value = value
                row.updated_at = now
            else:
                row = AppSetting(key=key, value=value, updated_at=now)
                db.add(row)
            db.commit()
            db.refresh(row)
            return AppSettingModel.model_validate(row)


AppSettings = AppSettingsTable()
