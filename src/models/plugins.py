"""Plugin upload models (untrusted Python stored server-side)."""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class PluginKind(str, Enum):
    LIGHTNING_MODULE = "lightning_module"
    DATALOADERS = "dataloaders"
    BENCHMARK = "benchmark"


class PluginRecord(BaseModel):
    id: str
    name: str
    kind: PluginKind
    filename: str
    path: str
    sha256: str
    symbols: dict[str, list[str]] = Field(default_factory=dict)
    uploaded_at: datetime


class PluginListResponse(BaseModel):
    plugins: list[PluginRecord]


class PluginUploadResponse(BaseModel):
    plugin: PluginRecord


