from datetime import datetime
from pydantic import BaseModel


class SpectrumFrameResponse(
    BaseModel
):
    frame_index: int
    timestamp: datetime
    freq_hz: list[float]
    power_db: list[float]