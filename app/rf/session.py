from app.rf.synthesizer import Synthesizer
from app.rf.spectrum_analyzer import SpectrumAnalyzer
from app.rf.rf_blocks import RFAmplifier

fs = 20e6
n = 4096
class RFSession:

    def __init__(self):

        self.synth = Synthesizer(sample_rate=fs,N=n)
        self.latest_recording = None
        self.running = True
        self.analyzer = SpectrumAnalyzer(vbw_alpha=0.2)
        self.vbw = 0.2
        self.window = "hann"
        self.rf_blocks = [{
            "id": 0,
            "block": RFAmplifier(),
            "enabled": False,
            }]
        self.rf_block_id_count = 1
        self.constellation_mode = "raw"
        self.demodulator = None

rf_session = RFSession()