"""
components.py — Built-in waveform component types.

Each class is a Waveform subclass that generates IQ samples analytically.

Available components:
    CWTone        — pure complex sinusoid
    AMWaveform    — amplitude-modulated carrier
    FMWaveform    — frequency-modulated carrier
    ChirpWaveform — linear frequency sweep
    AWGNWaveform  — additive white Gaussian noise band
    BPSKWaveform  — BPSK with random or fixed symbols
    QPSKWaveform  — QPSK with random or fixed symbols
    ScriptWaveform — arbitrary user Python expression/function
"""

from __future__ import annotations
import numpy as np
from typing import Optional, Sequence
from .waveform import Waveform, IQData


def _awgn(N: int, sigma: float) -> np.ndarray:
    """Complex AWGN with given std-dev per component."""
    if sigma <= 0:
        return np.zeros(N, dtype=np.complex128)
    return (np.random.randn(N) + 1j * np.random.randn(N)) * (sigma / np.sqrt(2))


class CWTone(Waveform):
    """
    Pure complex sinusoid (CW carrier).

        s(t) = amplitude * exp(j * 2π * freq_offset * t)

    Parameters
    ----------
    freq : float
        Carrier frequency offset from DC, in Hz.
    amplitude : float
        Linear amplitude (voltage units).
    phase : float
        Initial phase in radians.
    noise_sigma : float
        Std-dev of additive complex Gaussian noise.
    """

    def __init__(
        self,
        freq: float = 0.0,
        amplitude: float = 1.0,
        phase: float = 0.0,
        noise_sigma: float = 0.0,
        name: str = "CW",
    ):
        self.freq = freq
        self.amplitude = amplitude
        self.phase = phase
        self.bw = 0
        self.noise_sigma = noise_sigma
        self.name = name

    def generate_chunk(self,N: int,fs: float,t0: float = 0.0, bb_freq : float = 0.0) -> IQData:
        t = t0 + np.arange(N) / fs

        s = (self.amplitude * np.exp(1j * (2 * np.pi * bb_freq * t+ self.phase)))

        s += _awgn(N,self.noise_sigma)

        return IQData(s, fs)

    def to_dict(self) -> dict:
        return dict(type="CWTone", name=self.name,
                    freq=self.freq, amplitude=self.amplitude,
                    phase=self.phase, noise_sigma=self.noise_sigma)

    @classmethod
    def _from_dict(cls, d: dict) -> "CWTone":
        return cls(d["freq"], d.get("amplitude", 1.0),
                   d.get("phase", 0.0), d.get("noise_sigma", 0.0), d.get("name", "CW"))


class AMWaveform(Waveform):
    """
    Amplitude-modulated carrier.

        s(t) = amplitude * (1 + depth * cos(2π * mod_rate * t)) * exp(j * 2π * freq * t)

    Produces a carrier + two sidebands separated by ±mod_rate from freq.

    Parameters
    ----------
    freq : float
        Carrier frequency in Hz.
    mod_rate : float
        Modulation (tone) frequency in Hz.
    depth : float
        Modulation depth 0–1 (1 = 100% AM).
    amplitude : float
        Peak carrier amplitude.
    noise_sigma : float
        AWGN noise std-dev.
    """

    def __init__(
        self,
        freq: float = 0.0,
        mod_rate: float = 1e6,
        depth: float = 0.5,
        amplitude: float = 1.0,
        noise_sigma: float = 0.0,
        name: str = "AM",
    ):
        self.freq = freq
        self.mod_rate = mod_rate
        self.depth = depth
        self.bw = 2 * mod_rate
        self.amplitude = amplitude
        self.noise_sigma = noise_sigma
        self.name = name

    def generate_chunk(self,N: int,fs: float = 0,t0: float = 0.0, bb_freq : float = 0.0) -> IQData:

        t = t0 + np.arange(N) / fs

        envelope = 1.0 + self.depth * np.cos(
            2 * np.pi * self.mod_rate * t
        )

        carrier = np.exp(
            1j * 2 * np.pi * bb_freq* t
        )

        s = self.amplitude * envelope * carrier
        s += _awgn(N, self.noise_sigma)

        return IQData(s, fs)

    def to_dict(self) -> dict:
        return dict(type="AMWaveform", name=self.name,
                    freq=self.freq, mod_rate=self.mod_rate,
                    depth=self.depth, amplitude=self.amplitude,
                    noise_sigma=self.noise_sigma)

    @classmethod
    def _from_dict(cls, d: dict) -> "AMWaveform":
        return cls(d["freq"], d["mod_rate"], d.get("depth", 0.5),
                   d.get("amplitude", 1.0), d.get("noise_sigma", 0.0), d.get("name", "AM"))


class FMWaveform(Waveform):
    """
    Frequency-modulated carrier.

        phi(t) = 2π * freq * t + (kf / fm) * sin(2π * mod_rate * t)
        s(t)   = amplitude * exp(j * phi(t))

    where kf = freq_deviation (peak frequency swing in Hz).
    Carson bandwidth ≈ 2 * (freq_deviation + mod_rate).

    Parameters
    ----------
    freq : float
        Carrier centre frequency in Hz.
    mod_rate : float
        Modulating signal frequency in Hz.
    freq_deviation : float
        Peak frequency deviation in Hz.
    amplitude : float
        Signal amplitude.
    noise_sigma : float
        AWGN noise std-dev.
    """

    def __init__(
        self,
        freq: float = 0.0,
        mod_rate: float = 0.5e6,
        freq_deviation: float = 1e6,
        amplitude: float = 1.0,
        noise_sigma: float = 0.0,
        name: str = "FM",
    ):
        self.freq = freq
        self.mod_rate = mod_rate
        self.freq_deviation = freq_deviation
        self.bw = 2 * (freq_deviation + mod_rate)
        self.amplitude = amplitude
        self.noise_sigma = noise_sigma
        self.name = name

    def generate_chunk(self, N: int, fs: float, t0: float = 0.0, bb_freq = float) -> IQData:
        t = t0 + np.arange(N) / fs

        phi = (
                2 * np.pi * bb_freq * t
                + (self.freq_deviation / self.mod_rate)
                * np.sin(
            2 * np.pi * self.mod_rate * t
        )
        )

        s = self.amplitude * np.exp(1j * phi)
        s += _awgn(N, self.noise_sigma)

        return IQData(s, fs)

    def to_dict(self) -> dict:
        return dict(type="FMWaveform", name=self.name,
                    freq=self.freq, mod_rate=self.mod_rate,
                    freq_deviation=self.freq_deviation, amplitude=self.amplitude,
                    noise_sigma=self.noise_sigma)

    @classmethod
    def _from_dict(cls, d: dict) -> "FMWaveform":
        return cls(d["freq"], d["mod_rate"], d["freq_deviation"],
                   d.get("amplitude", 1.0), d.get("noise_sigma", 0.0), d.get("name", "FM"))


class ChirpWaveform(Waveform):
    """
    Linear frequency sweep (chirp).

        f(t) = freq_start + (freq_end - freq_start) * (t mod period) / period
        s(t) = amplitude * exp(j * 2π * integral(f(t)) dt)

    The chirp repeats every `period` seconds (defaults to full buffer length).

    Parameters
    ----------
    freq_start : float
        Start frequency in Hz.
    freq_end : float
        End frequency in Hz.
    amplitude : float
        Signal amplitude.
    period : float | None
        Chirp repetition period in seconds. None = single sweep across buffer.
    noise_sigma : float
        AWGN noise std-dev.
    """

    def __init__(
        self,
        freq: float = 96e6,
        bw : float = 2e6,
        amplitude: float = 1.0,
        period: Optional[float] = 2,
        noise_sigma: float = 0.0,
        name: str = "Chirp",
    ):
        self.freq = freq
        self.bw = bw
        self.freq_start = self.freq - bw/2
        self.freq_end = self.freq + bw/2
        self.amplitude = amplitude
        self.period = period
        self.noise_sigma = noise_sigma
        self.name = name

    def generate_chunk(self,N: int,fs: float,t0: float = 0.0, bb_freq : float = 0.0) -> IQData:
        T = self.period if (self.period is not None and self.period > 0) else N / fs
        t = t0 + np.arange(N) / fs
        t_mod = np.mod(t, T)
        f0 = (self.freq_start - self.freq)
        k = (self.freq_end - self.freq_start) / T
        phi = 2 * np.pi * ((bb_freq + f0) * t_mod + 0.5 * k * t_mod ** 2)
        s = self.amplitude * np.exp(1j * phi) + _awgn(N, self.noise_sigma)
        return IQData(s, fs)

    def to_dict(self) -> dict:
        return dict(type="ChirpWaveform", name=self.name,
                    freq=self.freq, bw=self.bw,
                    amplitude=self.amplitude, period=self.period,
                    noise_sigma=self.noise_sigma)

    @classmethod
    def _from_dict(cls, d: dict) -> "ChirpWaveform":
        return cls(d["freq"], d["bw"], d.get("amplitude", 1.0),
                   d.get("period"), d.get("noise_sigma", 0.0), d.get("name", "Chirp"))


class AWGNWaveform(Waveform):
    """
    Additive white Gaussian noise source (flat noise floor).

    Useful to simulate a receiver noise floor independently of
    per-component noise_sigma values.

    Parameters
    ----------
    noise_density : float
        Noise power density (sigma of the complex Gaussian).
    freq : float
        Centre frequency (DC by default). Not used in generation —
        AWGN is wideband — but kept for metadata / JSON consistency.
    """

    def __init__(
        self,
        noise_density: float = 0.2,
        freq: float = 0.0,
        name: str = "AWGN",
    ):
        self.noise_density = noise_density
        self.freq = freq
        self.bw = np.inf
        self.name = name

    def generate_chunk(self,N: int,fs: float,t0: float = 0.0, bb_freq : float = 0.0) -> IQData:
        s = _awgn(N, self.noise_density)
        return IQData(s, fs)

    def to_dict(self) -> dict:
        return dict(type="AWGNWaveform", name=self.name,
                    noise_density=self.noise_density, freq=self.freq)

    @classmethod
    def _from_dict(
            cls,
            d
    ):
        return cls(
            freq=d.get(
                "freq",
                0.0
            ),
            noise_density=d.get(
                "noise_density",
                0.2
            ),
            name=d.get(
                "name",
                "AWGN"
            )
        )

class BPSKWaveform(Waveform):
    """
    Binary Phase Shift Keying (BPSK).

    Random or fixed symbol stream, rectangular pulse shaping,
    upconverted to freq.

    Parameters
    ----------
    freq : float
        Carrier frequency in Hz.
    symbol_rate : float
        Symbol rate in symbols/sec (= bandwidth for rectangular pulses).
    amplitude : float
        Signal amplitude.
    symbols : Sequence[int] | None
        If provided, use this fixed +1/-1 sequence (tiled to fill buffer).
        If None, random symbols are generated each call.
    noise_sigma : float
        AWGN noise std-dev.
    """

    def __init__(
        self,
        freq: float = 0.0,
        symbol_rate: float = 2e6,
        amplitude: float = 1.0,
        symbols: Optional[Sequence[int]] = None,
        noise_sigma: float = 0.0,
        name: str = "BPSK",
    ):
        self.freq = freq
        self.symbol_rate = symbol_rate
        self.amplitude = amplitude
        self.symbols = list(symbols) if symbols is not None else None
        self.noise_sigma = noise_sigma
        self.name = name

    def generate_chunk(self,N: int,fs: float,t0: float = 0.0, bb_freq : float = 0.0) -> IQData:
        sps = max(1, int(round(fs / self.symbol_rate)))
        n_syms = int(np.ceil(N / sps))
        if self.symbols is not None:
            reps = int(np.ceil(n_syms / len(self.symbols)))
            raw = (self.symbols * reps)[:n_syms]
        else:
            raw = np.random.choice([-1, 1], size=n_syms)
        baseband = np.repeat(raw, sps)[:N].astype(np.float64)
        t = t0 + np.arange(N) / fs
        s = (self.amplitude * baseband * np.exp(1j * 2 * np.pi * bb_freq * t)
             + _awgn(N, self.noise_sigma))
        return IQData(s, fs)

    def to_dict(self) -> dict:
        return dict(type="BPSKWaveform", name=self.name,
                    freq=self.freq, symbol_rate=self.symbol_rate,
                    amplitude=self.amplitude, symbols=self.symbols,
                    noise_sigma=self.noise_sigma)

    @classmethod
    def _from_dict(cls, d: dict) -> "BPSKWaveform":
        return cls(d["freq"], d["symbol_rate"], d.get("amplitude", 1.0),
                   d.get("symbols"), d.get("noise_sigma", 0.0), d.get("name", "BPSK"))


class QPSKWaveform(Waveform):
    """
    Quadrature Phase Shift Keying (QPSK).

    Constellation: {(1+j), (-1+j), (-1-j), (1-j)} / sqrt(2)

    Parameters
    ----------
    freq : float
        Carrier frequency in Hz.
    symbol_rate : float
        Symbol rate in symbols/sec.
    amplitude : float
        Signal amplitude (peak envelope = amplitude).
    symbols : Sequence[int] | None
        0–3 symbol indices; None = random.
    noise_sigma : float
        AWGN noise std-dev.
    """

    _CONSTELLATION = np.array([1+1j, -1+1j, -1-1j, 1-1j]) / np.sqrt(2)

    def __init__(
        self,
        freq: float = 0.0,
        symbol_rate: float = 2e6,
        amplitude: float = 1.0,
        symbols: Optional[Sequence[int]] = None,
        noise_sigma: float = 0.0,
        name: str = "QPSK",
    ):
        self.freq = freq
        self.symbol_rate = symbol_rate
        self.amplitude = amplitude
        self.symbols = list(symbols) if symbols is not None else None
        self.noise_sigma = noise_sigma
        self.name = name

    def generate_chunk(self,N: int,fs: float,t0: float = 0.0, bb_freq : float = 0.0) -> IQData:
        sps = max(1, int(round(fs / self.symbol_rate)))
        n_syms = int(np.ceil(N / sps))
        if self.symbols is not None:
            reps = int(np.ceil(n_syms / len(self.symbols)))
            idx = (self.symbols * reps)[:n_syms]
        else:
            idx = np.random.randint(0, 4, size=n_syms)
        baseband = np.repeat(self._CONSTELLATION[idx], sps)[:N]
        t = t0 + np.arange(N) / fs
        s = (self.amplitude * baseband * np.exp(1j * 2 * np.pi * bb_freq * t)
             + _awgn(N, self.noise_sigma))
        return IQData(s, fs)

    def to_dict(self) -> dict:
        return dict(type="QPSKWaveform", name=self.name,
                    freq=self.freq, symbol_rate=self.symbol_rate,
                    amplitude=self.amplitude, symbols=self.symbols,
                    noise_sigma=self.noise_sigma)

    @classmethod
    def _from_dict(cls, d: dict) -> "QPSKWaveform":
        return cls(d["freq"], d["symbol_rate"], d.get("amplitude", 1.0),
                   d.get("symbols"), d.get("noise_sigma", 0.0), d.get("name", "QPSK"))


class ScriptWaveform(Waveform):
    """
    User-defined waveform via a Python expression or callable.

    The script string is eval'd with the following locals available:
        N    : int   — number of samples requested
        fs   : float — sample rate in Hz
        t    : ndarray shape (N,) — time vector [0, (N-1)/fs]
        np   : numpy module

    The expression must evaluate to a complex ndarray of shape (N,).

    Example
    -------
    >>> ScriptWaveform(
    ...     script="np.exp(1j * 2 * np.pi * 3e6 * t) * np.hanning(N)",
    ...     name="Windowed CW"
    ... )

    Alternatively, pass a Python callable:
        fn(N: int, fs: float) -> np.ndarray  (complex)

    Parameters
    ----------
    script : str | None
        Python expression string.
    fn : callable | None
        Python callable (takes precedence over script).
    name : str
    noise_sigma : float
    """

    def __init__(
        self,
        script: Optional[str] = None,
        fn=None,
        name: str = "Script",
        noise_sigma: float = 0.0,
    ):
        if script is None and fn is None:
            raise ValueError("Provide either a script string or a callable fn.")
        self.script = script
        self.fn = fn
        self.name = name
        self.noise_sigma = noise_sigma

    def generate_chunk(self,N: int,fs: float,t0: float = 0.0, bb_freq : float = 0.0) -> IQData:
        if self.fn is not None:
            s = self.fn(N, fs)
        else:
            t = t0 + np.arange(N) / fs
            s = eval(self.script, {"np": np, "N": N, "fs": fs, "t": t})
        s = np.asarray(s, dtype=np.complex128)
        s += _awgn(N, self.noise_sigma)
        return IQData(s, fs)

    def to_dict(self) -> dict:
        return dict(type="ScriptWaveform", name=self.name,
                    script=self.script, noise_sigma=self.noise_sigma)

    @classmethod
    def _from_dict(cls, d: dict) -> "ScriptWaveform":
        return cls(script=d.get("script"), name=d.get("name", "Script"),
                   noise_sigma=d.get("noise_sigma", 0.0))
