"""Dataset API routes."""
from __future__ import annotations

import shutil
import uuid
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, File, HTTPException, UploadFile

from ..models import DatasetInfo, DatasetListResponse
from ..storage import (
    delete_dataset as storage_delete_dataset,
    get_dataset,
    list_datasets,
    save_dataset,
)
from .helpers import UPLOAD_DIR, now

router = APIRouter(tags=["datasets"])


@router.post("/datasets/upload", response_model=DatasetInfo)
def upload_dataset(file: UploadFile = File(...)) -> DatasetInfo:
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    dataset_id = str(uuid.uuid4())
    dest_path = UPLOAD_DIR / f"{dataset_id}_{file.filename}"

    with dest_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    frame = pd.read_csv(dest_path)
    info = DatasetInfo(
        id=dataset_id,
        filename=file.filename,
        path=str(dest_path),
        columns=list(frame.columns),
        row_count=len(frame),
        uploaded_at=now(),
    )
    save_dataset(info)
    return info


@router.get("/datasets", response_model=DatasetListResponse)
def list_all_datasets() -> DatasetListResponse:
    return DatasetListResponse(datasets=list_datasets())


@router.get("/datasets/{dataset_id}", response_model=DatasetInfo)
def get_dataset_by_id(dataset_id: str) -> DatasetInfo:
    info = get_dataset(dataset_id)
    if not info:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return info


@router.delete("/datasets/{dataset_id}")
def delete_dataset(dataset_id: str) -> dict[str, str]:
    info = storage_delete_dataset(dataset_id)
    if not info:
        raise HTTPException(status_code=404, detail="Dataset not found")
    path = Path(info.path)
    if path.exists():
        path.unlink()
    return {"status": "deleted", "dataset_id": dataset_id}

