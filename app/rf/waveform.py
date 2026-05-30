"""
waveform.py — Base waveform object and IQ data container.

A Waveform subclass either:
  1. Holds raw IQ data directly (IQWaveform), or
  2. Implements generate(N, fs) to produce IQ samples on demand.

All waveforms expose:
  .generate(N, fs)  → IQData
  .to_dict()        → JSON-serialisable config
  Waveform.from_dict(d) → reconstructed instance
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from typing import Optional
import json


@dataclass
class IQData:
    """Container for complex IQ samples with sample-rate metadata."""
    samples: np.ndarray          # complex64/128 array, shape (N,)
    sample_rate: float           # Hz

    def __post_init__(self):
        self.samples = np.asarray(self.samples, dtype=np.complex128)

    @property
    def N(self) -> int:
        return len(self.samples)

    @property
    def duration(self) -> float:
        return self.N / self.sample_rate

    @property
    def I(self) -> np.ndarray:
        return self.samples.real

    @property
    def Q(self) -> np.ndarray:
        return self.samples.imag

    def __add__(self, other: "IQData") -> "IQData":
        if self.sample_rate != other.sample_rate:
            raise ValueError("Sample rates must match to add IQData")
        n = min(self.N, other.N)
        return IQData(self.samples[:n] + other.samples[:n], self.sample_rate)

    def power_dB(self) -> float:
        """Mean power in dBFS."""
        p = np.mean(np.abs(self.samples) ** 2)
        return 10 * np.log10(p) if p > 0 else -np.inf

    def save(self, path: str):
        """Save raw complex64 IQ to binary file (I,Q interleaved float32)."""
        self.samples.astype(np.complex64).tofile(path)

    @classmethod
    def load(cls, path: str, sample_rate: float) -> "IQData":
        """Load raw complex64 IQ from binary file."""
        samples = np.fromfile(path, dtype=np.complex64)
        return cls(samples.astype(np.complex128), sample_rate)


class Waveform:
    """
    Abstract base class for all waveform components.

    Subclasses must implement:
        generate(N, fs) -> IQData
        to_dict()       -> dict
    """

    # Registry for from_dict reconstruction
    _registry: dict[str, type] = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        Waveform._registry[cls.__name__] = cls

    def generate_chunk(self, N: int, fs: float, t0 : float) -> IQData:
        raise NotImplementedError

    def to_dict(self) -> dict:
        raise NotImplementedError

    @classmethod
    def from_dict(cls, d: dict) -> "Waveform":
        """Reconstruct any Waveform subclass from a dict produced by to_dict()."""
        type_name = d.get("type")
        if type_name not in cls._registry:
            raise ValueError(f"Unknown waveform type: {type_name!r}. "
                             f"Available: {list(cls._registry)}")
        return cls._registry[type_name]._from_dict(d)

    @classmethod
    def _from_dict(cls, d: dict) -> "Waveform":
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.to_dict()}>"


class IQWaveform(Waveform):
    """
    Waveform backed by pre-computed or externally-supplied IQ data.

    Can be constructed from:
      - a numpy complex array
      - a raw binary file path (complex64, I/Q interleaved)
    """

    def __init__(
        self,
        samples: np.ndarray,
        sample_rate: float,
        name: str = "IQWaveform",
        freq: float = 0.0,
        amplitude: float = 1.0,
    ):
        self.name = name
        self.sample_rate = sample_rate
        self._samples = np.asarray(samples, dtype=np.complex128)
        self.freq = freq   # Hz — applied as complex rotation
        self.amplitude = amplitude

    @classmethod
    def from_file(
        cls,
        path: str,
        sample_rate: float,
        name: str = "",
        freq_offset: float = 0.0,
        amplitude: float = 1.0,
    ) -> "IQWaveform":
        samples = np.fromfile(path, dtype=np.complex64).astype(np.complex128)
        return cls(samples, sample_rate, name or path, freq_offset, amplitude)

    def generate_chunk(self, N: int, fs: float, t0 : float) -> IQData:
        # Tile or truncate stored samples to length N
        reps = int(np.ceil(N / len(self._samples)))
        s = np.tile(self._samples, reps)[:N]
        # Apply freq offset and amplitude
        t = np.arange(N) / fs
        s = s * self.amplitude * np.exp(1j * 2 * np.pi * self.freq_offset * t)
        return IQData(s, fs)

    def to_dict(self) -> dict:
        return {
            "type": "IQWaveform",
            "name": self.name,
            "sample_rate": self.sample_rate,
            "freq_offset": self.freq_offset,
            "amplitude": self.amplitude,
            "n_samples": len(self._samples),
            # Raw samples not serialised — save separately if needed
        }

    @classmethod
    def _from_dict(cls, d: dict) -> "IQWaveform":
        raise ValueError(
            "IQWaveform cannot be fully reconstructed from dict alone "
            "(raw samples not stored). Load from file instead."
        )
