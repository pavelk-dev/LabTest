import numpy as np
from abc import ABC
class Constellation(ABC):
    def __init__(self):
        pass
class QAMConstellation(Constellation):
    def __init__(self, order: int):
        self.order = order

        m = int(np.sqrt(order))
        if m * m != order:
            raise ValueError("QAM order must be square")

        bits_per_axis = int(np.log2(m))

        levels = np.arange(-(m - 1), m, 2)

        self.symbols = []
        self.bits = []

        for i in range(m):
            for q in range(m):
                gray_i = i ^ (i >> 1)
                gray_q = q ^ (q >> 1)

                bits = (
                        format(gray_i, f"0{bits_per_axis}b")
                        + format(gray_q, f"0{bits_per_axis}b")
                )

                sym = levels[i] + 1j * levels[q]

                self.symbols.append(sym)
                self.bits.append(bits)

        self.symbols = np.array(self.symbols)

        # normalize average power = 1
        self.symbols /= np.sqrt(np.mean(np.abs(self.symbols) ** 2))

        self.bits_to_symbol = {
            b: s for b, s in zip(self.bits, self.symbols)
        }

        self.symbol_to_bits = {
            i: b for i, b in enumerate(self.bits)
        }