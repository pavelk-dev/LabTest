"""
rf_blocks.py — RF processing block chain.

Architecture
------------
RFBlock is an abstract base class for any element that transforms IQ data.
Blocks are chained in a list and applied in succession:

    chain = [RFAmplifier(...), BandpassFilter(...), Mixer(...)]
    iq = apply_chain(chain, iq_in)

Signal convention
-----------------
All power quantities are in dBm referenced to a normalised 1-Ω system,
so power in mW = mean(|x|²).  No impedance factor — this is a theoretical
simulation, not a circuit simulator.

    P_mW  = mean(|x|²)
    P_dBm = 10·log10(P_mW + ε)

Available blocks
----------------
    RFAmplifier    — gain + 3rd-order nonlinearity (P1dB / OIP3)
    BandpassFilter — ideal brickwall or raised-cosine roll-off in freq domain
    Mixer          — frequency translation by a local oscillator
"""

from __future__ import annotations
from abc import ABC, abstractmethod
import numpy as np
from .waveform import IQData


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _power_dbm(samples: np.ndarray) -> float:
    """Normalised power of a sample array in dBm (1-Ω convention)."""
    return float(10 * np.log10(np.mean(np.abs(samples) ** 2) + 1e-30))


def _dbm_to_amplitude(power_dbm: float) -> float:
    """RMS amplitude corresponding to a normalised power level."""
    return float(np.sqrt(10 ** (power_dbm / 10)))


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class RFBlock(ABC):
    """
    Abstract base class for RF processing blocks.

    Subclasses implement process() which takes IQData and returns IQData.
    The sample rate may change (e.g. after a decimating filter) but the
    time-domain meaning of the samples must remain consistent.
    """

    name: str = "RFBlock"

    @abstractmethod
    def process(self, data: IQData) -> IQData:
        """Transform input IQ data and return output IQ data."""

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} '{self.name}'>"


# ---------------------------------------------------------------------------
# Chain helper
# ---------------------------------------------------------------------------

def apply_chain(blocks: list[RFBlock], data: IQData) -> IQData:
    """
    Apply a list of RFBlocks in order.

        iq_out = block_n( ... block_1( block_0(iq_in) ) ... )

    Parameters
    ----------
    blocks : list[RFBlock]
        Processing chain, applied left to right.
    data : IQData
        Input samples.

    Returns
    -------
    IQData
        Output after all blocks.
    """
    for block in blocks:
        data = block.process(data)
    return data


# ---------------------------------------------------------------------------
# RFAmplifier
# ---------------------------------------------------------------------------

class RFAmplifier(RFBlock):
    """
    Memoryless 3rd-order complex baseband amplifier.

    Model
    -----
        y = a1·x + a3·x·|x|²

    a1 and a3 are derived from gain_db and p1db_in_dbm so that the
    single-tone 1 dB compression point is exactly reproduced.

    OIP3 (informational) ≈ P1dB_out + 9.6 dB for a memoryless amplifier.

    Parameters
    ----------
    gain_db : float
        Small-signal power gain in dB.
    p1db_in_dbm : float
        Input-referred 1 dB compression point in dBm.
    oip3_dbm : float | None
        Output IP3 in dBm — stored for reference only.
        If None it is estimated as P1dB_out + 9.6 dB.
    noise_figure_db : float
        Noise figure in dB.  0 = noiseless.
    name : str
    """

    PARAMS = [
        {"name": "gain_db",         "label": "Gain",        "unit": "dB",  "default": 20.0},
        {"name": "p1db_in_dbm",     "label": "P1dB (in)",   "unit": "dBm", "default": 3.0},
        {"name": "oip3_dbm",        "label": "OIP3",        "unit": "dBm", "default": 33.0},
        {"name": "noise_figure_db", "label": "NF",          "unit": "dB",  "default": 5.0},
    ]

    def __init__(
        self,
        gain_db: float = 20.0,
        p1db_in_dbm: float = 3.0,
        oip3_dbm: float | None = None,
        noise_figure_db: float = 5.0,
        name: str = "Amplifier",
    ):
        self.gain_db         = gain_db
        self.p1db_in_dbm     = p1db_in_dbm
        self.noise_figure_db = noise_figure_db
        self.name            = name

        # Voltage gain (normalised, no impedance)
        self.a1 = 10 ** (gain_db / 20)

        # Derive a3 from the single-tone 1dBCP condition:
        #   |a1 + a3·A²| = a1·10^(-1/20)  at A = rms_amplitude(p1db_in)
        # Since power_mw = A_rms² and peak = sqrt(2)·A_rms for a sinusoid:
        #   A_peak² = 2 · 10^(p1db_in/10)
        # Compression factor:
        #   a1·(1 - 10^(-1/20)) = |a3|·A_peak²
        A_peak_sq  = 2 * (10 ** (p1db_in_dbm / 10))
        comp       = 1.0 - 10 ** (-1.0 / 20)   # ≈ 0.10875
        self.a3    = -(self.a1 * comp) / A_peak_sq   # negative = compressive

        # OIP3 — either supplied or estimated
        p1db_out_dbm = p1db_in_dbm + gain_db
        self.oip3_dbm = oip3_dbm if oip3_dbm is not None else p1db_out_dbm + 9.6

        # Noise: additive at output, scaled per chunk by sample rate
        # noise_power_density (normalised mW/Hz) = kT·(F-1) in 1-Ω system
        # kT at 290 K in normalised mW/Hz ≈ 4e-18 (tiny — but keeps NF meaningful)
        noise_factor         = 10 ** (noise_figure_db / 10)
        kT_norm              = 4e-18          # normalised kT, mW/Hz
        self.noise_psd       = kT_norm * (noise_factor - 1.0)

    # ------------------------------------------------------------------
    def process(self, data: IQData) -> IQData:
        x   = data.samples
        y   = self.a1 * x + self.a3 * x * (np.abs(x) ** 2)

        if self.noise_figure_db > 0:
            noise_power = self.noise_psd * data.sample_rate
            sigma       = np.sqrt(noise_power / 2.0)
            y          += (  np.random.randn(len(y))
                           + 1j * np.random.randn(len(y))) * sigma

        return IQData(y, data.sample_rate)

    # ------------------------------------------------------------------
    def gain_compression_db(self, input_power_dbm: float) -> float:
        """Gain compression in dB at the given input power."""
        A_peak_sq      = 2 * (10 ** (input_power_dbm / 10))
        gain_compressed = abs(self.a1 + self.a3 * A_peak_sq)
        return float(20 * np.log10(self.a1 / (gain_compressed + 1e-30)))

    def to_dict(self) -> dict:
        return dict(type="RFAmplifier", name=self.name,
                    gain_db=self.gain_db, p1db_in_dbm=self.p1db_in_dbm,
                    oip3_dbm=self.oip3_dbm, noise_figure_db=self.noise_figure_db)

    @classmethod
    def _from_dict(cls, d: dict) -> "RFAmplifier":
        return cls(gain_db=d.get("gain_db", 20.0),
                   p1db_in_dbm=d.get("p1db_in_dbm", 3.0),
                   oip3_dbm=d.get("oip3_dbm"),
                   noise_figure_db=d.get("noise_figure_db", 5.0),
                   name=d.get("name", "Amplifier"))


# ---------------------------------------------------------------------------
# BandpassFilter
# ---------------------------------------------------------------------------

class BandpassFilter(RFBlock):
    """
    Frequency-domain bandpass filter applied to baseband IQ.

    The filter is applied via FFT → multiply by mask → IFFT, so it is
    effectively a linear phase (zero group-delay-distortion) FIR.

    Two window shapes are available:
        "brick"   — ideal rectangular passband (Gibbs ringing in time domain)
        "cosine"  — raised-cosine roll-off (softer edges, less ringing)

    Parameters
    ----------
    center_hz : float
        Passband centre frequency relative to the baseband carrier (Hz).
        0 = centred on DC (i.e. centred on the carrier).
    bandwidth_hz : float
        Passband 3 dB bandwidth in Hz.
    shape : str
        "brick" or "cosine".
    name : str
    """

    PARAMS = [
        {"name": "center_hz",    "label": "Centre",     "unit": "Hz", "default": 0.0},
        {"name": "bandwidth_hz", "label": "Bandwidth",  "unit": "Hz", "default": 1e6},
        {"name": "shape",        "label": "Shape",                    "default": "cosine"},
    ]

    def __init__(
        self,
        center_hz: float = 0.0,
        bandwidth_hz: float = 1e6,
        shape: str = "cosine",
        name: str = "BPF",
    ):
        self.center_hz    = center_hz
        self.bandwidth_hz = bandwidth_hz
        self.shape        = shape
        self.name         = name

    def _make_mask(self, N: int, fs: float) -> np.ndarray:
        freqs    = np.fft.fftshift(np.fft.fftfreq(N, d=1.0 / fs))
        rel      = freqs - self.center_hz
        half_bw  = self.bandwidth_hz / 2.0

        if self.shape == "brick":
            mask = (np.abs(rel) <= half_bw).astype(float)
        else:
            # Raised-cosine roll-off over 10% of bandwidth on each edge
            roll  = 0.1 * half_bw
            mask  = np.zeros(N, dtype=float)
            inner = np.abs(rel) <= (half_bw - roll)
            outer = (np.abs(rel) > (half_bw - roll)) & (np.abs(rel) <= (half_bw + roll))
            mask[inner] = 1.0
            mask[outer] = 0.5 * (1 + np.cos(
                np.pi * (np.abs(rel[outer]) - (half_bw - roll)) / (2 * roll)
            ))
        return mask

    def process(self, data: IQData) -> IQData:
        X    = np.fft.fftshift(np.fft.fft(data.samples))
        mask = self._make_mask(len(data.samples), data.sample_rate)
        y    = np.fft.ifft(np.fft.ifftshift(X * mask))
        return IQData(y, data.sample_rate)

    def to_dict(self) -> dict:
        return dict(type="BandpassFilter", name=self.name,
                    center_hz=self.center_hz, bandwidth_hz=self.bandwidth_hz,
                    shape=self.shape)

    @classmethod
    def _from_dict(cls, d: dict) -> "BandpassFilter":
        return cls(center_hz=d.get("center_hz", 0.0),
                   bandwidth_hz=d.get("bandwidth_hz", 1e6),
                   shape=d.get("shape", "cosine"),
                   name=d.get("name", "BPF"))


# ---------------------------------------------------------------------------
# Mixer
# ---------------------------------------------------------------------------

class Mixer(RFBlock):
    """
    Ideal complex mixer — frequency translation by a local oscillator.

    Multiplies the input by exp(j·2π·lo_freq·t), which shifts the
    spectrum by +lo_freq Hz.  Use a negative lo_freq to shift down.

    In a real receiver the LO also introduces phase noise; a simple
    phase noise model is included via phase_noise_dbc_hz.

    Parameters
    ----------
    lo_freq_hz : float
        LO frequency offset in Hz.  Positive = upconvert.
    lo_power_dbm : float
        LO power in dBm — affects conversion loss scaling.
        In an ideal mixer conversion loss = 0 dB regardless; this
        parameter is stored for display/documentation only.
    phase_noise_dbc_hz : float
        Single-sideband phase noise floor in dBc/Hz (e.g. -120).
        Set to -np.inf or None to disable.
    name : str
    """

    PARAMS = [
        {"name": "lo_freq_hz",        "label": "LO Freq",     "unit": "Hz",    "default": 10e6},
        {"name": "lo_power_dbm",      "label": "LO Power",    "unit": "dBm",   "default": 10.0},
        {"name": "phase_noise_dbc_hz","label": "Phase Noise", "unit": "dBc/Hz","default": -120.0},
    ]

    def __init__(
        self,
        lo_freq_hz: float = 10e6,
        lo_power_dbm: float = 10.0,
        phase_noise_dbc_hz: float | None = -120.0,
        name: str = "Mixer",
    ):
        self.lo_freq_hz         = lo_freq_hz
        self.lo_power_dbm       = lo_power_dbm
        self.phase_noise_dbc_hz = phase_noise_dbc_hz
        self.name               = name

        # Phase noise sigma per sample — precomputed constant
        # SSB phase noise L(f) in dBc/Hz → total phase variance per sample:
        #   σ²_φ = 10^(L/10) * fs   (integrated over fs/2 each side)
        # We store the dBc/Hz value and compute per-chunk given fs.
        self._pn_enabled = (
            phase_noise_dbc_hz is not None
            and np.isfinite(phase_noise_dbc_hz)
        )

    # ------------------------------------------------------------------
    def _lo_signal(self, N: int, fs: float, t0: float = 0.0) -> np.ndarray:
        t  = t0 + np.arange(N) / fs
        lo = np.exp(1j * 2 * np.pi * self.lo_freq_hz * t)

        if self._pn_enabled:
            # Phase noise: white phase noise approximation
            # σ²_φ per sample = 10^(L/10) * fs
            pn_var   = (10 ** (self.phase_noise_dbc_hz / 10)) * fs
            pn_sigma = np.sqrt(pn_var)
            phase_noise = np.cumsum(np.random.randn(N)) * pn_sigma / np.sqrt(N)
            lo *= np.exp(1j * phase_noise)

        return lo

    def process(self, data: IQData, t0: float = 0.0) -> IQData:
        lo = self._lo_signal(len(data.samples), data.sample_rate, t0)
        y  = data.samples * lo
        return IQData(y, data.sample_rate)

    def to_dict(self) -> dict:
        return dict(type="Mixer", name=self.name,
                    lo_freq_hz=self.lo_freq_hz, lo_power_dbm=self.lo_power_dbm,
                    phase_noise_dbc_hz=self.phase_noise_dbc_hz)

    @classmethod
    def _from_dict(cls, d: dict) -> "Mixer":
        return cls(lo_freq_hz=d.get("lo_freq_hz", 10e6),
                   lo_power_dbm=d.get("lo_power_dbm", 10.0),
                   phase_noise_dbc_hz=d.get("phase_noise_dbc_hz", -120.0),
                   name=d.get("name", "Mixer"))
