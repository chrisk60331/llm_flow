"""Plugin upload/list routes (untrusted python; discovery via AST only)."""
from __future__ import annotations

import ast
import hashlib
import json
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from ..models import PluginKind, PluginListResponse, PluginRecord, PluginUploadResponse
from ..storage import delete_plugin, get_plugin, list_plugins, save_plugin
from .helpers import PLUGINS_DIR, now

router = APIRouter(tags=["plugins"])


def _discover_symbols(kind: PluginKind, source: str) -> dict[str, list[str]]:
    tree = ast.parse(source)

    if kind == PluginKind.LIGHTNING_MODULE:
        class_names: list[str] = []
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            for base in node.bases:
                # Accept LightningModule, L.LightningModule, lightning.LightningModule
                if isinstance(base, ast.Name) and base.id == "LightningModule":
                    class_names.append(node.name)
                    break
                if isinstance(base, ast.Attribute) and base.attr == "LightningModule":
                    class_names.append(node.name)
                    break
        return {"lightning_modules": sorted(set(class_names))}

    if kind == PluginKind.DATALOADERS:
        fn_names: list[str] = []
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                fn_names.append(node.name)
        if "build_dataloaders" not in fn_names:
            msg = "Dataloader plugin must define a top-level function named build_dataloaders"
            raise ValueError(msg)
        return {"functions": sorted(set(fn_names))}

    if kind == PluginKind.BENCHMARK:
        fn_names: list[str] = []
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                fn_names.append(node.name)
        if "run_benchmark" not in fn_names:
            msg = "Benchmark plugin must define a top-level function named run_benchmark"
            raise ValueError(msg)
        return {"functions": sorted(set(fn_names))}

    msg = f"Unsupported plugin kind: {kind}"
    raise ValueError(msg)


@router.post("/plugins/upload", response_model=PluginUploadResponse)
def upload_plugin(
    kind: PluginKind,
    file: UploadFile = File(...),
    name: str | None = None,
) -> PluginUploadResponse:
    if not file.filename or not file.filename.endswith(".py"):
        raise HTTPException(status_code=400, detail="Only .py files are supported")

    plugin_id = str(uuid.uuid4())
    safe_filename = Path(file.filename).name
    dest_path = PLUGINS_DIR / f"{plugin_id}_{kind.value}_{safe_filename}"

    with dest_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    content_bytes = dest_path.read_bytes()
    sha256 = hashlib.sha256(content_bytes).hexdigest()
    source = content_bytes.decode("utf-8")

    try:
        symbols = _discover_symbols(kind, source)
    except Exception as e:
        dest_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(e))

    record = PluginRecord(
        id=plugin_id,
        name=name or Path(safe_filename).stem,
        kind=kind,
        filename=safe_filename,
        path=str(dest_path),
        sha256=sha256,
        symbols=symbols,
        uploaded_at=now(),
    )
    save_plugin(record)
    return PluginUploadResponse(plugin=record)


@router.get("/plugins", response_model=PluginListResponse)
def list_all_plugins() -> PluginListResponse:
    return PluginListResponse(plugins=list_plugins())


@router.get("/plugins/{plugin_id}", response_model=PluginRecord)
def get_plugin_by_id(plugin_id: str) -> PluginRecord:
    plugin = get_plugin(plugin_id)
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")
    return plugin


@router.delete("/plugins/{plugin_id}")
def delete_plugin_by_id(plugin_id: str) -> dict[str, str]:
    plugin = delete_plugin(plugin_id)
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")
    path = Path(plugin.path)
    if path.exists():
        path.unlink()
    return {"status": "deleted", "plugin_id": plugin_id}


@router.get("/plugins/{plugin_id}/source")
def get_plugin_source(plugin_id: str) -> dict[str, str]:
    plugin = get_plugin(plugin_id)
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")
    path = Path(plugin.path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Plugin file not found on disk")
    source = path.read_text(encoding="utf-8")
    return {"source": source, "plugin_id": plugin_id, "name": plugin.name, "kind": plugin.kind.value}


@router.post("/plugins/create-from-source", response_model=PluginUploadResponse)
def create_plugin_from_source(
    kind: PluginKind,
    name: str,
    source: str,
) -> PluginUploadResponse:
    plugin_id = str(uuid.uuid4())
    safe_name = "".join(c if c.isalnum() or c in "_-" else "_" for c in name)
    dest_path = PLUGINS_DIR / f"{plugin_id}_{kind.value}_{safe_name}.py"

    try:
        symbols = _discover_symbols(kind, source)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    dest_path.write_text(source, encoding="utf-8")
    sha256 = hashlib.sha256(source.encode("utf-8")).hexdigest()

    record = PluginRecord(
        id=plugin_id,
        name=name,
        kind=kind,
        filename=f"{safe_name}.py",
        path=str(dest_path),
        sha256=sha256,
        symbols=symbols,
        uploaded_at=now(),
    )
    save_plugin(record)
    return PluginUploadResponse(plugin=record)


