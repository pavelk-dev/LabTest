from app.rf.synthesizer import Synthesizer
from app.rf.components import AWGNWaveform
from app.rf.spectrum_analyzer import SpectrumAnalyzer

fs = 20e6
n = 4096
class RFSession:

    def __init__(self):

        self.synth = Synthesizer(sample_rate=fs,N=n)

        self.analyzer = SpectrumAnalyzer(vbw_alpha=0.2)
        self.vbw = 0.2
        self.window = "hann"


rf_session = RFSession()