import numpy as np
from app.rf.windowing import window
from app.rf.waveform import IQData
class SpectrumAnalyzer:

    def __init__(self, vbw_alpha: float = 0.05):

        self.vbw_alpha = vbw_alpha
        self._avg_psd = None

    def fft(self,iq = IQData, window_name=None):
        x = window(iq.samples, window_name)
        fft = np.fft.fftshift(np.fft.fft(x))
        psd = (np.abs(fft) ** 2) / (iq.sample_rate * len(x))

        if self._avg_psd is None or len(psd) != len(self._avg_psd):
            self._avg_psd = psd.copy()
        else:
            self._avg_psd = (
                    self.vbw_alpha * psd
                    + (1 - self.vbw_alpha)
                    * self._avg_psd
            )


        psd_db = 10 * np.log10(self._avg_psd + 1e-20)

        freqs = np.fft.fftshift(np.fft.fftfreq(len(x),d=1 / iq.sample_rate))

        return freqs, psd_db

    def peak_power_db(self):
        _, p = self.fft()
        return float(np.max(p))

    def peak_frequency_hz(self):
        f, p = self.fft()
        return float(
            f[np.argmax(p)]
        )