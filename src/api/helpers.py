"""Shared helpers for API routes."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

UPLOAD_DIR = Path("data/uploads")
ARTIFACTS_DIR = Path("artifacts")
CONFIGS_DIR = Path("configs")
PLUGINS_DIR = Path("data/plugins")

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
PLUGINS_DIR.mkdir(parents=True, exist_ok=True)


def now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


def generate_friendly_name() -> str:
    """Generate a friendly config name."""
    import random
    adjectives = ["swift", "bright", "calm", "bold", "keen", "warm", "cool", "quick"]
    nouns = ["falcon", "tiger", "river", "peak", "storm", "wave", "flame", "frost"]
    return f"{random.choice(adjectives)}-{random.choice(nouns)}-{uuid.uuid4().hex[:4]}"

