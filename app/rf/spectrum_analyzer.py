import numpy as np
from app.rf.windowing import window
from app.rf.waveform import IQData
class SpectrumAnalyzer:

    def __init__(self, IQ : IQData, vbw_alpha: float = 0.05):

        self.iq = IQ.samples
        self.fs = IQ.sample_rate
        self.n = len(self.iq)
        self.vbw_alpha = vbw_alpha
        self._avg_psd = None

    def fft(self,window_name=None):
        x = window(self.iq, window_name)

        fft = np.fft.fftshift(np.fft.fft(x))
        psd = (np.abs(fft) ** 2) / (self.fs * len(x))

        if self._avg_psd is None:

            self._avg_psd = psd

            a = self.vbw_alpha

            self._avg_psd = (a * psd + (1 - a) * self._avg_psd)

        psd_db = 10 * np.log10(self._avg_psd + 1e-20)

        freqs = np.fft.fftshift(np.fft.fftfreq(len(x),d=1 / self.fs))

        return freqs, psd_db

    def peak_power_db(self):
        _, p = self.fft()
        return float(np.max(p))

    def peak_frequency_hz(self):
        f, p = self.fft()
        return float(
            f[np.argmax(p)]
        )