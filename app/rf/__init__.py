"""
spectrum_synth — IQ-based spectrum synthesis toolkit.

Quick start
-----------
    from spectrum_synth import SpectrumSynthesizer, CWTone, FMWaveform, AWGNWaveform

    synth = SpectrumSynthesizer(sample_rate=20e6, N=4096, window="hann")
    synth.add(CWTone(freq_offset=3e6, amplitude=1.0))
    synth.add(FMWaveform(freq_offset=-5e6, mod_rate=500e3, freq_deviation=1e6))
    synth.add(AWGNWaveform(noise_density=0.05))

    result = synth.synthesize()
    result.plot()
"""

from .waveform import Waveform, IQData, IQWaveform
from .components import (
    CWTone,
    AMWaveform,
    FMWaveform,
    ChirpWaveform,
    AWGNWaveform,
    BPSKWaveform,
    QPSKWaveform,
    ScriptWaveform,
)
from .synthesizer import Synthesizer, IQRecording

__all__ = [
    "Waveform",
    "IQData",
    "IQWaveform",
    "CWTone",
    "AMWaveform",
    "FMWaveform",
    "ChirpWaveform",
    "AWGNWaveform",
    "BPSKWaveform",
    "QPSKWaveform",
    "ScriptWaveform",
    "Synthesizer",
    "IQRecording",
]

__version__ = "0.1.0"
