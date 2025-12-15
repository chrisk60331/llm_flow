import math
import torch
from torch.utils.data import DataLoader, Dataset


class SinDataset(Dataset):
    def __init__(self, n_points: int):
        self.n_points = int(n_points)

    def __len__(self) -> int:
        return self.n_points

    def __getitem__(self, i: int):
        x = float(i) / float(self.n_points)  # 0..~1
        y = math.sin(x)  # sin(x) where x in [0, 1)
        return (
            torch.tensor([x], dtype=torch.float32),
            torch.tensor([y], dtype=torch.float32),
        )


def build_dataloaders(cfg: dict, dataset: dict | None) -> dict[str, DataLoader]:
    user_cfg = cfg["cfg"]  # fail fast if missing

    n_points = int(user_cfg["n_points"])
    batch_size = int(user_cfg["batch_size"])
    num_workers = int(user_cfg["num_workers"])
    seed = int(user_cfg["seed"])

    ds = SinDataset(n_points=n_points)
    g = torch.Generator().manual_seed(seed)

    return {
        "train": DataLoader(
            ds,
            batch_size=batch_size,
            shuffle=True,
            num_workers=num_workers,
            generator=g,
        )
    }