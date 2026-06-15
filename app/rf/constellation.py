import numpy as np


@staticmethod
def gray(n: int) -> int:
    return n ^ (n >> 1)

class QAMConstellation:

    def __init__(self, M: int):

        self.M = M

        self.m = int(np.sqrt(M))

        if self.m * self.m != M:
            raise ValueError("M must be square")

        self.bits_per_axis = int(np.log2(self.m))
        self.bits_per_symbol = int(np.log2(M))

        self.points = []
        self.symbol_bits = []
        self.bit_to_symbol = {}

        self._build()

    def _build(self):

        levels = np.arange(-(self.m - 1),self.m,2)

        for q_bin in range(self.m):

            q_gray = self.gray(q_bin)

            for i_bin in range(self.m):

                i_gray = self.gray(i_bin)

                point = (levels[i_bin]+ 1j * levels[q_bin])

                bits = []

                for b in reversed(range(self.bits_per_axis)):
                    bits.append((i_gray >> b) & 1)

                for b in reversed(range(self.bits_per_axis)):
                    bits.append((q_gray >> b) & 1)

                bits = tuple(bits)

                symbol_index = len(self.points)

                self.points.append(point)
                self.symbol_bits.append(bits)

                self.bit_to_symbol[bits] = symbol_index

        self.points = np.asarray(self.points)

        self.points /= np.sqrt(np.mean(np.abs(self.points) ** 2))