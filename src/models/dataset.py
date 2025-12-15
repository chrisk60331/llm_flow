"""Dataset-related Pydantic models."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class DatasetInfo(BaseModel):
    id: str
    filename: str
    path: str
    columns: list[str]
    row_count: int
    uploaded_at: datetime


class DatasetListResponse(BaseModel):
    datasets: list[DatasetInfo]

