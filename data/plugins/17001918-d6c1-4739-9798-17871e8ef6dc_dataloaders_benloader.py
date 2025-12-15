# dataloaders_mnist.py
from __future__ import annotations

from typing import Any

import torch
from torch.utils.data import DataLoader, random_split
from torchvision.datasets import MNIST
from torchvision.transforms import ToTensor


def build_dataloaders(cfg: dict, dataset: dict | None) -> dict[str, DataLoader]:
    """
    Contract:
      build_dataloaders(cfg: dict, dataset: dict|None) -> {"train": DataLoader, "val"?: DataLoader, "test"?: DataLoader}

    Notes:
      - This ignores the passed `dataset` and downloads MNIST locally.
      - Uses only cpu-safe defaults.
    """
    training = (cfg or {}).get("training", {}) if isinstance(cfg, dict) else {}
    user_cfg = (cfg or {}).get("cfg", {}) if isinstance(cfg, dict) else {}

    batch_size = int(user_cfg.get("batch_size", 64))
    num_workers = int(user_cfg.get("num_workers", 0))
    pin_memory = bool(user_cfg.get("pin_memory", False))
    data_dir = str(user_cfg.get("data_dir", "./data/mnist"))

    full = MNIST(root=data_dir, train=True, download=True, transform=ToTensor())
    train_len = int(user_cfg.get("train_len", 55_000))
    val_len = len(full) - train_len
    if train_len <= 0 or val_len <= 0:
        raise ValueError("train_len must be within (0, len(MNIST))")

    g = torch.Generator().manual_seed(int(user_cfg.get("seed", 42)))
    train_ds, val_ds = random_split(full, [train_len, val_len], generator=g)

    test_ds = MNIST(root=data_dir, train=False, download=True, transform=ToTensor())

    train_loader = DataLoader(
        train_ds,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        pin_memory=pin_memory,
        drop_last=True,
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=pin_memory,
        drop_last=False,
    )
    test_loader = DataLoader(
        test_ds,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=pin_memory,
        drop_last=False,
    )

    return {"train": train_loader, "val": val_loader, "test": test_loader}