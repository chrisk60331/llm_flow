"""Custom Lightning experiment models."""
from __future__ import annotations

from pydantic import BaseModel, Field


class CustomLightningTrainingConfig(BaseModel):
    max_epochs: int = Field(default=1, ge=1)
    accelerator: str = Field(default="auto")
    devices: int | str = Field(default="auto")
    precision: str = Field(default="32")
    log_every_n_steps: int = Field(default=10, ge=1)


class CustomLightningFullConfig(BaseModel):
    training: CustomLightningTrainingConfig = Field(
        default_factory=CustomLightningTrainingConfig
    )
    cfg: dict = Field(default_factory=dict, description="User-defined config blob.")


class CustomLightningRequest(BaseModel):
    dataset_id: str
    config: CustomLightningFullConfig = Field(default_factory=CustomLightningFullConfig)

    lightning_module_plugin_id: str
    lightning_module_class_name: str

    dataloaders_plugin_id: str
    dataloaders_function_name: str = Field(default="build_dataloaders")

    compute_target_id: str | None = Field(
        default=None, description="Optional compute target for remote execution"
    )


