from abc import ABC
from dataclasses import dataclass

import numpy as np
from app.rf.waveform import IQData
from app.rf.constellation import *
from app.rf.pulseshaper import *
class Demodulator(ABC):
    def __init__(self):
        pass
    def demodulate(self, data: IQData) -> IQData:
        pass
@dataclass
class DemodResult:
    bits : np.array
    symbols : np.array
    recovered_symbols : np.array
class QAMDemodulator(Demodulator):
    def __init__(self, M: int = 16, symbol_rate : float = 1e6, pulse_shape:PulseShaper   = RootRaisedCosine(),):
        self.M = M
        self.constellation = QAMConstellation(M)
        self.symbol_rate = symbol_rate
        self.pulse_shape = pulse_shape
    def demodulate(self, data: IQData):

        sps = max(
            1,
            int(round(data.sample_rate / self.symbol_rate))
        )

        # matched filter
        taps = self.pulse_shape.taps(sps)

        matched = np.convolve(
            data.samples,
            taps,
            mode="same",
        )

        # perfect timing recovery
        delay = len(taps) // 2

        rx_symbols = matched[
            delay::sps
        ]

        # normalize constellation power
        gain = np.sqrt(np.mean(np.abs(rx_symbols) ** 2))
        rx_symbols = rx_symbols / gain
        bits = []
        symbol_indices = []

        for sample in rx_symbols:

            dist = np.abs(
                sample - self.constellation.symbols
            ) ** 2

            sym = int(np.argmin(dist))

            symbol_indices.append(sym)

            bits.extend(self.constellation.bits[sym])

        return DemodResult(
            bits=np.array(bits, dtype=np.uint8),
            symbols=np.array(symbol_indices, dtype=np.int32),
            recovered_symbols=rx_symbols)

    def to_dict(self) -> dict:
        return {
            "type": "QAMDemodulator",
            "M": self.M,
            "symbol_rate": self.symbol_rate,
        }