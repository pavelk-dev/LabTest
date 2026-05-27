from app.rf.components import AWGNWaveform
from app.rf.components import CWTone
from app.rf.components import FMWaveform
from app.rf.components import ChirpWaveform


WAVEFORM_REGISTRY = {
    "AWGNWaveform": AWGNWaveform,
    "CWTone": CWTone,
    "FMWaveform": FMWaveform,
    "ChirpWaveform": ChirpWaveform,
}