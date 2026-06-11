import numpy as np


def window(
    samples,
    name: str | None = None
):
    if name is None:
        return samples

    windows = {
        "hann": np.hanning,
        "hamming": np.hamming,
        "blackman": np.blackman,
        "rect": lambda N: np.ones(N),
    }

    if name not in windows:
        raise ValueError(
            f"Unknown window: {name}"
        )

    w = windows[name](len(samples))
    window_power = np.mean(w**2)
    return samples * w, window_power