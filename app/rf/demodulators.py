from abc import ABC
import numpy as np
from app.rf.waveform import IQData
import app.rf.constellation
class Demodulator(ABC):
    def __init__(self):
        pass
    def demodulate(self, data: IQData) -> IQData:
        pass
class DemodResult:
    bits : np.array
    symbols : np.array
class QAMDemodulator(Demodulator):
    def __init__(self, M: int = 16):
        self.M = M
        self.constellation = app.QAMConstellation(M)
    def demodulate(self, data: IQData):

        samples = data.samples

        samples = samples / np.sqrt(
            np.mean(np.abs(samples) ** 2)
        )

        bits = []
        symbols = []

        for sample in samples:
            dist = np.abs(
                sample - self.constellation.points
            ) ** 2

            sym = np.argmin(dist)

            symbols.append(sym)
            bits = self.constellation.symbol_bits[sym]

        return DemodResult(
            bits=np.array(bits, dtype=np.uint8),
            symbols=np.array(symbols, dtype=np.int32)
        )