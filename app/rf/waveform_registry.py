from app.rf.components import AWGNWaveform, QAMWaveform
from app.rf.components import CWTone
from app.rf.components import FMWaveform
from app.rf.components import ChirpWaveform
from app.rf.components import QPSKWaveform
from app.rf.components import BPSKWaveform
from app.rf.components import AMWaveform
from app.rf.components import QAMWaveform

WAVEFORM_REGISTRY = {
    "AWGNWaveform": AWGNWaveform,
    "CWTone": CWTone,
    "FMWaveform": FMWaveform,
    "ChirpWaveform": ChirpWaveform,
    "AMWaveform": AMWaveform,
    "QPSKWaveform": QPSKWaveform,
    "BPSKWaveform": BPSKWaveform,
    "QAMWaveform": QAMWaveform,

}