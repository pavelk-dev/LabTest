from abc import ABC
import numpy as np
class PulseShaper(ABC):
    def shape(self, symbols : np.ndarray, sps: int) -> np.ndarray:
        pass

class RectangularPulse(PulseShaper):
    def shape(self, symbols, sps):
        return np.repeat(symbols, sps)

class RootRaisedCosine(PulseShaper):

    def __init__(
        self,
        beta: float = 0.35,
        span: int = 8,
    ):
        self.beta = beta
        self.span = span
        self._cache = {}

    def _get_taps(self, sps):

        if sps in self._cache:
            return self._cache[sps]

        beta = self.beta
        span = self.span

        t = np.arange(
            -span * sps / 2,
            span * sps / 2 + 1
        ) / sps

        h = np.zeros_like(t, dtype=float)

        for i, ti in enumerate(t):

            if abs(ti) < 1e-12:
                h[i] = (
                        1
                        + beta * (4 / np.pi - 1)
                )

            elif beta > 0 and abs(abs(ti) - 1 / (4 * beta)) < 1e-12:
                h[i] = (
                               beta / np.sqrt(2)
                       ) * (
                               (1 + 2 / np.pi)
                               * np.sin(np.pi / (4 * beta))
                               +
                               (1 - 2 / np.pi)
                               * np.cos(np.pi / (4 * beta))
                       )

            else:
                num = (np.sin(np.pi * ti * (1 - beta)) + 4 * beta * ti * np.cos(np.pi * ti * (1 + beta)))

                den = (np.pi * ti * (1 - (4 * beta * ti) ** 2))

                h[i] = num / den

        h /= np.sqrt(np.sum(h ** 2))
        self._cache[sps] = h
        return h

    def taps(self, sps):
        return self._get_taps(sps)

    def shape(self, symbols, sps):

        taps = self._get_taps(sps)

        up = np.zeros(
            len(symbols) * sps,
            dtype=complex
        )

        up[::sps] = symbols

        return np.convolve(
            up,
            taps,
            mode="same",
        )