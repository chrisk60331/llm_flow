from __future__ import annotations

from typing import Any

import torch
from torch import nn, optim
import lightning as L


class LitAutoEncoder(L.LightningModule):
    """
    Expects cfg shaped like:
      {
        "training": {...},
        "cfg": {
          "input_dim": 784,
          "hidden_dim": 64,
          "latent_dim": 3,
          "lr": 1e-3
        }
      }
    """

    def __init__(self, cfg: dict):
        super().__init__()

        if not isinstance(cfg, dict):
            raise TypeError("cfg must be a dict")

        user_cfg = cfg["cfg"]  # fail fast if missing
        if not isinstance(user_cfg, dict):
            raise TypeError('cfg["cfg"] must be a dict')

        input_dim = int(user_cfg["input_dim"])
        hidden_dim = int(user_cfg["hidden_dim"])
        latent_dim = int(user_cfg["latent_dim"])
        lr = float(user_cfg["lr"])

        self._lr = lr

        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, latent_dim),
        )
        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, input_dim),
        )

    def training_step(self, batch: Any, batch_idx: int):
        x, _ = batch
        x = x.view(x.size(0), -1)
        z = self.encoder(x)
        x_hat = self.decoder(z)
        loss = nn.functional.mse_loss(x_hat, x)
        self.log("train_loss", loss, prog_bar=True)
        return loss

    def validation_step(self, batch: Any, batch_idx: int):
        x, _ = batch
        x = x.view(x.size(0), -1)
        z = self.encoder(x)
        x_hat = self.decoder(z)
        loss = nn.functional.mse_loss(x_hat, x)
        self.log("val_loss", loss, prog_bar=True)
        return loss

    def test_step(self, batch: Any, batch_idx: int):
        x, _ = batch
        x = x.view(x.size(0), -1)
        z = self.encoder(x)
        x_hat = self.decoder(z)
        loss = nn.functional.mse_loss(x_hat, x)
        self.log("test_loss", loss, prog_bar=True)
        return loss

    def configure_optimizers(self):
        return optim.Adam(self.parameters(), lr=self._lr)