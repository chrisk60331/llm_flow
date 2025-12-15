import torch
from torch import nn
import lightning as L


class SinRegressor(L.LightningModule):
    def __init__(self, cfg: dict):
        super().__init__()
        user_cfg = cfg["cfg"]  # fail fast if missing

        hidden_dim = int(user_cfg["hidden_dim"])
        lr = float(user_cfg["lr"])

        self._lr = lr
        self.net = nn.Sequential(
            nn.Linear(1, hidden_dim),
            nn.Tanh(),
            nn.Linear(hidden_dim, 1),
        )

    @property
    def model(self) -> nn.Module:
        # Expose a stable attribute name for benchmarks: lightning_module.model(x)
        return self.net

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)

    def training_step(self, batch, batch_idx):
        x, y = batch
        y_hat = self(x)
        loss = nn.functional.mse_loss(y_hat, y)
        self.log("train_loss", loss)
        return loss

    def configure_optimizers(self):
        return torch.optim.Adam(self.parameters(), lr=self._lr)
