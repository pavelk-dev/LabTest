from fastapi import APIRouter, WebSocket
from pydantic import BaseModel
from starlette.websockets import WebSocketDisconnect

from app.rf.session import rf_session
from app.rf.waveform_registry import WAVEFORM_REGISTRY
import asyncio
import inspect

router = APIRouter()
fps = 20
frame_delta = 1 / fps

class RFSettings(BaseModel):
    center_freq: float
    sample_rate: float
    fft_size: int
    vbw: float

class ComponentRequest(BaseModel):
    type: str
    params: dict

async def dsp_loop():
    try:
        while True:
            if rf_session.running:
                rf_session.latest_recording = (rf_session.synth.next_chunk())
                await asyncio.sleep(len(rf_session.latest_recording.iq.samples) / rf_session.synth.sample_rate)
            else:
                await asyncio.sleep(0.05)

    except asyncio.CancelledError:

        print("DSP CANCELLED")

        raise
@router.get("/rf/components")
async def list_components():

    out = {}

    for name, cls in WAVEFORM_REGISTRY.items():

        sig = inspect.signature(cls.__init__)

        fields = []

        for pname, p in sig.parameters.items():

            if pname == "self":
                continue

            fields.append({ "name": pname, "default": None
                    if p.default is inspect._empty
                    else p.default
            })

        out[name] = fields

    return out
# @router.get("/rf/components")
# async def list_components():
#
#     out=[]
#
#     for i,c in enumerate(rf_session.synth._components):
#
#         out.append(
#             {
#                 "id":
#                     i,
#                 "enabled":
#                     c["enabled"],
#                 "waveform":
#                     c["waveform"]
#                     .to_dict()
#             }
#         )
#
#     return out
@router.post("/rf/components")
async def add_component(req: ComponentRequest):

    cls = WAVEFORM_REGISTRY[req.type]
    wf = cls(**req.params)

    rf_session.synth.add(wf)

    return {"ok": True}
from pydantic import BaseModel

class RunRequest(BaseModel): running: bool


@router.post( "/rf/run")
async def set_run(req: RunRequest):
    print(rf_session.running)
    rf_session.running = (req.running)
    print(rf_session.running)
    return {"running": rf_session.running}
@router.post("/rf/settings")
async def update_settings(settings: RFSettings):

    rf_session.synth.center_freq = settings.center_freq
    rf_session.synth.sample_rate = settings.sample_rate
    rf_session.synth.N = settings.fft_size
    rf_session.analyzer.vbw_alpha = settings.vbw

    return {"ok": True}

@router.websocket("/rf/stream")
async def rf_stream(websocket: WebSocket):
    await websocket.accept()

    try:

        while True:

            recording = rf_session.latest_recording
            if recording is not None:
                freqs, power_db = (rf_session.analyzer.fft(recording.iq, rf_session.window))
                freqs += rf_session.synth.center_freq
                await websocket.send_json({
                    "freq_hz": freqs.tolist(),
                    "power_db": power_db.tolist(),
                    "sample_rate": recording.iq.sample_rate,
                    "time_sec": rf_session.synth.time_sec
                })

            await asyncio.sleep(frame_delta)

    except WebSocketDisconnect:
        print("client disconnected")

    except asyncio.CancelledError:
        print("stream cancelled")

    except Exception as e:
        print("stream error:", e)

    finally:
        try:
            await websocket.close()
        except:
            pass