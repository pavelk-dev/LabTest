from fastapi import APIRouter, WebSocket
from pydantic import BaseModel
from app.rf.session import rf_session
import asyncio

router = APIRouter()

class RFSettings(BaseModel):
    sample_rate: float
    fft_size: int
    vbw: float


@router.post("/rf/settings")
async def update_settings(settings: RFSettings):

    rf_session.synth.sample_rate = settings.sample_rate
    rf_session.synth.N = settings.fft_size
    rf_session.analyzer.vbw_alpha = settings.vbw

    return {"ok": True}

@router.websocket("/rf/stream")
async def rf_stream(websocket: WebSocket):

    await websocket.accept()

    try:

        while True:

            recording = (rf_session.synth.next_chunk())

            rf_session.analyzer.iq = recording.iq.samples
            rf_session.analyzer.fs = recording.iq.sample_rate

            freqs, power_db = (rf_session.analyzer.fft(rf_session.window))
            print("sending")
            await websocket.send_json({"freq_hz":freqs.tolist(), "power_db":power_db.tolist()})

            await asyncio.sleep(len(freqs) / recording.iq.sample_rate)

    except Exception as e:

        print(e)
