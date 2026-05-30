"""
synthesizer.py — Spectrum synthesizer.

SpectrumSynthesizer manages a list of Waveform objects, sums their IQ
output, and computes the FFT spectrum.

Usage
-----
    synth = SpectrumSynthesizer(sample_rate=20e6, N=4096)
    synth.add(CWTone(freq_offset=3e6, amplitude=1.0))
    synth.add(FMWaveform(freq_offset=-5e6, mod_rate=500e3, freq_deviation=1e6))
    synth.add(AWGNWaveform(noise_density=0.05))

    result = synth.synthesize()           # → SpectrumResult
    result.plot()
    result.save_iq("composite.bin")
"""

from __future__ import annotations
import numpy as np
from scipy.signal import butter, sosfiltfilt
from typing import List, Generator
import json
import threading
from app.rf.components import AWGNWaveform

from .waveform import Waveform, IQData


class IQRecording:
    """
    Holds the output of a single synthesize() call.

    Attributes
    ----------
    freqs : ndarray
        Frequency axis in Hz, length N (fftshifted, DC centred).
    power_dB : ndarray
        Power spectral density in dBFS, length N (fftshifted).
    iq : IQData
        The summed composite IQ samples used to produce this spectrum.
    sample_rate : float
        Sample rate in Hz.
    N : int
        FFT length (= number of IQ samples).
    window : str
        Window function name used.
    component_names : list[str]
        Names of the active components included.
    """

    def __init__(
        self,
        iq: IQData,
        component_names: List[str],
    ):

        self.iq = iq
        self.component_names = component_names

    # ── Convenience properties ─────────────────────────────────────────────

    def save_iq(self, path: str):
        """Save composite IQ to raw complex64 binary."""
        self.iq.save(path)


class Synthesizer:

    def __init__(
        self,
        time_sec=0,
        sample_rate=20e6,
        N=4096,
        center_freq = 0
    ):
        self.center_freq = center_freq
        self.sample_rate = sample_rate
        self.time_sec = time_sec
        self.N = N
        self._components = []
        self._lock = threading.Lock()

    # ── Component management ───────────────────────────────────────────────

    def add(self, waveform: Waveform, enabled: bool = True) -> "Synthesizer":
        """Add a waveform component. Returns self for chaining."""
        with self._lock:
            self._components.append({"waveform": waveform,"enabled": enabled})
        return self

    def remove(self, index: int):
        """Remove component by index."""
        with self._lock:
            self._components.pop(index)


    def enable(self, index: int):
        with self._lock:
            self._components[index]["enabled"] = True


    def disable(self, index: int):
        with self._lock:
            self._components[index]["enabled"] = False

    @property
    def components(self) -> List[Waveform]:
        return [c["waveform"] for c in self._components]

    def __repr__(self) -> str:
        lines = [f"SpectrumSynthesizer(fs={self.sample_rate/1e6:.1f} MHz, N={self.N})"]
        for i, c in enumerate(self._components):
            state = "✓" if c["enabled"] else "✗"
            lines.append(f"  [{i}] {state} {c['waveform'].name}  ({c['waveform'].to_dict()['type']})")
        return "\n".join(lines)

    # ── Synthesis ──────────────────────────────────────────────────────────

    def synthesize(self) -> IQRecording:
        """
        Sum all enabled waveforms and compute the FFT spectrum.

        Returns
        -------
        SpectrumResult
            Contains the frequency axis, power spectrum (dBFS),
            composite IQ samples, and measurement helpers.
        """
        fs = self.sample_rate
        time_sec = self.time_sec
        N = self.N

        # Sum IQ from all enabled components
        composite = np.zeros(N, dtype=np.complex128)
        active_names = []
        for c in self._components:
            if not c["enabled"]:
                continue
            iq = c["waveform"].generate_chunk(N, fs, t0=time_sec)
            composite += iq.samples
            active_names.append(c["waveform"].name)



        return IQRecording(iq=IQData(composite, fs), N=N, component_names=active_names,)

    def stream(self,chunk_size: int = 4096) -> Generator[IQRecording, None, None]:

        fs = self.sample_rate
        t0 = 0.0

        while True:

            composite = np.zeros(chunk_size,dtype=np.complex128)

            active_names = []

            for c in self._components:

                if not c["enabled"]:
                    continue

                wf = c["waveform"]

                iq = wf.generate_chunk(chunk_size,fs,t0)

                composite += iq.samples
                active_names.append(wf.name)

            yield IQRecording(iq=IQData(composite,fs),component_names=active_names)

            t0 += (chunk_size/ fs)

    def next_chunk(
            self,
            N=None,
            fs=None
    ):
        visible_min = (self.center_freq - self.sample_rate / 2)

        visible_max = (self.center_freq + self.sample_rate / 2)


        N = N or self.N
        fs = fs or self.sample_rate

        t0 = self.time_sec

        composite = np.zeros(N,dtype=np.complex128)
        awgn = AWGNWaveform(freq = self.center_freq)
        composite += awgn.generate_chunk(N, fs, 0).samples

        active_names = []

        components = list(self._components)
        for c in components:

            if not c["enabled"]:
                continue

            wf = c["waveform"]
            wf_max = wf.freq + wf.bw/2
            wf_min = wf.freq - wf.bw/2
            bb_freq = wf.freq - self.center_freq
            if  wf_min > visible_max or wf_max < visible_min:
                continue
            elif wf_min >= visible_min and wf_max <= visible_max:

                iq = (wf.generate_chunk(N,fs,t0,bb_freq=bb_freq)).samples
            else:
                max_edge = max(abs(bb_freq + wf.bw / 2),abs(bb_freq - wf.bw / 2))
                k = max(2,int(np.ceil(2 * max_edge / fs)))

                fs_hi = k * fs
                N_hi = k * N


                iq = wf.generate_chunk(N_hi, fs_hi, t0, bb_freq=bb_freq)

                cutoff = 0.9 * fs / 2

                sos = butter(6, cutoff, btype="low", fs=fs_hi, output="sos")
                filtered = sosfiltfilt(sos, iq.samples)

                iq = filtered[::k][:N]

            composite += iq
            active_names.append(c["waveform"].name)

        self.time_sec += (N / fs)

        return IQRecording(
            iq=IQData(
                composite,
                fs
            ),
            component_names=active_names
        )
    # ── Serialisation ──────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "sample_rate": self.sample_rate,
            "N": self.N,
            "components": [
                {"waveform": c["waveform"].to_dict(), "enabled": c["enabled"]}
                for c in self._components
            ],
        }

    def save_json(self, path: str):
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def from_dict(cls, d: dict) -> "Synthesizer":
        synth = cls(
            sample_rate=d["sample_rate"],
            N=d["N"],
        )
        for c in d.get("components", []):
            wf = Waveform.from_dict(c["waveform"])
            synth.add(wf, enabled=c.get("enabled", True))
        return synth

    @classmethod
    def load_json(cls, path: str) -> "Synthesizer":
        with open(path) as f:
            return cls.from_dict(json.load(f))
