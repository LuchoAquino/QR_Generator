from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import List


class QRCodeCreate(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("La URL no puede estar vacía")
        if not v.startswith(("http://", "https://")):
            raise ValueError("La URL debe comenzar con http:// o https://")
        return v


class QRCodeResponse(BaseModel):
    id: int
    url: str
    short_code: str
    created_at: datetime
    scan_count: int = 0

    class Config:
        from_attributes = True


class ScanResponse(BaseModel):
    id: int
    qrcode_id: int
    scanned_at: datetime

    class Config:
        from_attributes = True


class QRCodeWithScans(BaseModel):
    id: int
    url: str
    short_code: str
    created_at: datetime
    total_scans: int
    scans_by_date: List[dict] = []

    class Config:
        from_attributes = True
