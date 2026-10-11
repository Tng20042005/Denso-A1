from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

from denso_a1.schema import SampleBatch, SampleMetadata


@dataclass(frozen=True)
class VAEConfig:
    """Frozen lightweight conditional 1-D VAE configuration for the T2 gate."""

    signal_length: int = 4096
    condition_dim: int = 3
    hidden_dim: int = 128
    latent_dim: int = 16
    batch_size: int = 64
    epochs: int = 20
    patience: int = 5
    learning_rate: float = 1e-3
    beta_kl: float = 1e-3
    spectral_weight: float = 0.05
    envelope_weight: float = 0.02
    seed: int = 0
    device: str = "cpu"

    def digest(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(payload).hexdigest()


def condition_vector(metadata: list[SampleMetadata]) -> np.ndarray:
    """Use only metadata available in the measured Paderborn records."""
    return np.asarray(
        [
            [
                float(item.operating_cond.get("speed_rpm", 0.0)) / 2000.0,
                float(item.operating_cond.get("torque_nm", 0.0)),
                float(item.operating_cond.get("radial_force_n", 0.0)) / 1000.0,
            ]
            for item in metadata
        ],
        dtype=np.float32,
    )


def _torch():
    try:
        import torch
        from torch import nn
    except ImportError as exc:  # pragma: no cover - exercised only in missing-dependency envs
        raise RuntimeError("T2 conditional VAE requires the torch extra in the T2 environment") from exc
    return torch, nn


class ConditionalVAE:
    def __init__(self, config: VAEConfig) -> None:
        torch, nn = _torch()
        self.torch = torch
        self.config = config
        torch.manual_seed(config.seed)
        self.model = nn.Module()
        self.model.encoder = nn.Sequential(
            nn.Linear(config.signal_length + config.condition_dim, config.hidden_dim),
            nn.ReLU(),
            nn.Linear(config.hidden_dim, config.hidden_dim),
            nn.ReLU(),
        )
        self.model.mu = nn.Linear(config.hidden_dim, config.latent_dim)
        self.model.logvar = nn.Linear(config.hidden_dim, config.latent_dim)
        self.model.decoder = nn.Sequential(
            nn.Linear(config.latent_dim + config.condition_dim, config.hidden_dim),
            nn.ReLU(),
            nn.Linear(config.hidden_dim, config.hidden_dim),
            nn.ReLU(),
            nn.Linear(config.hidden_dim, config.signal_length),
        )
        self.model.to(config.device)
        self.best_state: dict[str, Any] | None = None
        self.history: list[dict[str, float]] = []

    def _forward(self, x, c, *, sample: bool = True):
        torch = self.torch
        h = self.model.encoder(torch.cat([x, c], dim=1))
        mu = self.model.mu(h)
        logvar = self.model.logvar(h).clamp(-12.0, 12.0)
        if sample:
            z = mu + torch.exp(0.5 * logvar) * torch.randn_like(mu)
        else:
            z = mu
        return self.model.decoder(torch.cat([z, c], dim=1)), mu, logvar

    def _loss(self, x, c, *, sample: bool) -> tuple[Any, dict[str, float]]:
        torch = self.torch
        reconstruction, mu, logvar = self._forward(x, c, sample=sample)
        mse = torch.mean((reconstruction - x) ** 2)
        # The two frequency terms are train-data-supported diagnostics from the T0 failure
        # audit: resonance/PSD and envelope modulation were the dominant mismatches.
        centered_x = x - torch.mean(x, dim=1, keepdim=True)
        centered_y = reconstruction - torch.mean(reconstruction, dim=1, keepdim=True)
        psd_x = torch.log1p(torch.abs(torch.fft.rfft(centered_x, dim=1)))
        psd_y = torch.log1p(torch.abs(torch.fft.rfft(centered_y, dim=1)))
        spectral = torch.mean((psd_x - psd_y) ** 2)
        env_x = torch.abs(centered_x)
        env_y = torch.abs(centered_y)
        env_x = env_x - torch.mean(env_x, dim=1, keepdim=True)
        env_y = env_y - torch.mean(env_y, dim=1, keepdim=True)
        envelope = torch.mean(
            (torch.log1p(torch.abs(torch.fft.rfft(env_x, dim=1)))
             - torch.log1p(torch.abs(torch.fft.rfft(env_y, dim=1)))) ** 2
        )
        kl = -0.5 * torch.mean(1.0 + logvar - mu.pow(2) - logvar.exp())
        loss = mse + self.config.beta_kl * kl
        loss = loss + self.config.spectral_weight * spectral + self.config.envelope_weight * envelope
        return loss, {
            "loss": float(loss.detach().cpu()),
            "mse": float(mse.detach().cpu()),
            "kl": float(kl.detach().cpu()),
            "spectral": float(spectral.detach().cpu()),
            "envelope": float(envelope.detach().cpu()),
        }

    def _tensor_batch(self, batch: SampleBatch):
        torch = self.torch
        x = torch.as_tensor(batch.signals, dtype=torch.float32, device=self.config.device)
        c = torch.as_tensor(condition_vector(batch.metadata), dtype=torch.float32, device=self.config.device)
        return x, c

    def fit(self, train_fault: SampleBatch, val_fault: SampleBatch | None = None) -> list[dict[str, float]]:
        torch = self.torch
        if len(train_fault.signals) == 0:
            raise ValueError("T2 VAE requires at least one real training fault signal")
        if train_fault.signals.shape[1] != self.config.signal_length:
            raise ValueError("T2 VAE signal length does not match frozen config")
        torch.manual_seed(self.config.seed)
        optimizer = torch.optim.Adam(self.model.parameters(), lr=self.config.learning_rate)
        train_x, train_c = self._tensor_batch(train_fault)
        val_x, val_c = self._tensor_batch(val_fault) if val_fault is not None and len(val_fault.signals) else (None, None)
        best = float("inf")
        stale = 0
        generator = torch.Generator(device=self.config.device).manual_seed(self.config.seed)
        for epoch in range(self.config.epochs):
            self.model.train()
            order = torch.randperm(len(train_x), generator=generator, device=self.config.device)
            train_parts: list[dict[str, float]] = []
            for start in range(0, len(order), self.config.batch_size):
                index = order[start : start + self.config.batch_size]
                optimizer.zero_grad(set_to_none=True)
                loss, parts = self._loss(train_x[index], train_c[index], sample=True)
                loss.backward()
                optimizer.step()
                train_parts.append(parts)
            self.model.eval()
            with torch.no_grad():
                if val_x is not None:
                    _, val_parts = self._loss(val_x, val_c, sample=False)
                else:
                    val_parts = {"loss": float(np.mean([p["loss"] for p in train_parts]))}
            record = {
                "epoch": float(epoch + 1),
                "train_loss": float(np.mean([p["loss"] for p in train_parts])),
                "val_loss": float(val_parts["loss"]),
            }
            self.history.append(record)
            if record["val_loss"] < best - 1e-8:
                best = record["val_loss"]
                stale = 0
                self.best_state = deepcopy(self.model.state_dict())
            else:
                stale += 1
                if stale >= self.config.patience:
                    break
        if self.best_state is not None:
            self.model.load_state_dict(self.best_state)
        return self.history

    def generate(
        self,
        *,
        n: int,
        condition_metadata: list[SampleMetadata],
        source_groups: tuple[str, ...],
        seed: int,
        source_dataset: str = "Paderborn_Bearing_DataCenter",
    ) -> SampleBatch:
        torch = self.torch
        if n <= 0 or not condition_metadata:
            raise ValueError("T2 generation needs positive n and condition metadata")
        torch.manual_seed(seed)
        rng = np.random.default_rng(seed)
        chosen = [condition_metadata[int(i)] for i in rng.integers(0, len(condition_metadata), size=n)]
        cond = torch.as_tensor(condition_vector(chosen), dtype=torch.float32, device=self.config.device)
        z = torch.randn((n, self.config.latent_dim), device=self.config.device)
        self.model.eval()
        with torch.no_grad():
            signals = self.model.decoder(torch.cat([z, cond], dim=1)).cpu().numpy().astype(np.float64)
        config_hash = self.config.digest()
        metadata = []
        for ordinal, parent in enumerate(chosen):
            metadata.append(
                SampleMetadata(
                    sample_id=f"t2-vae-{seed}-{ordinal:04d}",
                    source_type="generated",
                    fault_origin="algorithmic_injection",
                    source_dataset=source_dataset,
                    source_version="t2-conditional-vae-v1",
                    raw_record_id=parent.raw_record_id,
                    group_id=f"generated-t2-{seed}-{ordinal:04d}",
                    condition_id=parent.condition_id,
                    parent_ids=[],
                    parent_group_ids=list(source_groups),
                    split_role="train",
                    fs_hz=parent.fs_hz,
                    n_samples=self.config.signal_length,
                    units=parent.units,
                    label_binary=1,
                    label_condition="t2_learned_synthesis",
                    generator="t2_conditional_vae",
                    generator_version="1.0",
                    config_hash=config_hash,
                    generator_seed=seed,
                    operating_cond=parent.operating_cond.copy(),
                    created_at=parent.created_at,
                )
            )
        return SampleBatch(signals, metadata)
