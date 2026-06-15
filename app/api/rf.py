from fastapi import APIRouter, WebSocket
from pydantic import BaseModel
from starlette.websockets import WebSocketDisconnect
import numpy as np
from app.rf.session import rf_session
from app.rf.waveform_registry import WAVEFORM_REGISTRY
from app.rf.rf_blocks_registry import RF_BLOCK_REGISTRY
import asyncio
import struct

from app.rf.rf_blocks import apply_chain

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

class ComponentPatch(BaseModel):
    enabled: bool | None = None
    params: dict | None = None

class RFBlockRequest(BaseModel):
    type: str
    params: dict

class RFBlockPatch(BaseModel):
    enabled: bool | None = None
    params: dict | None = None

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



@router.patch("/rf/components/{id}")
async def patch_component(id:int, req:ComponentPatch):

    c= rf_session.synth._components[id]
    if(req.enabled is not None):
        c["enabled"]=req.enabled
    if req.params:
        old_component = c["waveform"]
        params = old_component.to_dict()
        params.pop("type", None)
        params.update(req.params)
        print(req.params)
        c["waveform"] = type(old_component)(**params)
    return {"ok":True}

@router.delete("/rf/components/{id}")
async def delete_component(id:int):

    del(rf_session.synth._components[id])

    return {"ok":True}
@router.get("/rf/component_types")
async def list_components():

    return {
        name: cls.PARAMS
        for name, cls in WAVEFORM_REGISTRY.items()}

@router.get("/rf/block_types")
async def list_block_types():
    return {
        name: cls.PARAMS
        for name, cls in RF_BLOCK_REGISTRY.items()
    }
@router.get("/rf/blocks")
async def list_blocks():

    out = []

    for i, b in enumerate(rf_session.rf_blocks):

        out.append({
            "id": i,
            "enabled": b["enabled"],
            "block": b["block"].to_dict()
        })

    return out

@router.post("/rf/blocks")
async def add_block(req: RFBlockRequest):

    cls = RF_BLOCK_REGISTRY[req.type]

    block = cls(**req.params)

    rf_session.rf_blocks.append({
        "id": rf_session.rf_block_id_count,
        "enabled": True,
        "block": block
    })
    rf_session.rf_block_id_count += 1

    return {"ok": True}

@router.patch("/rf/blocks/{id}")
async def patch_block(id: int, req: RFBlockPatch):

    block = rf_session.rf_blocks[id]
    print(req.model_dump())
    if req.enabled is not None:
        block["enabled"] = req.enabled

    if req.params:
        old_rf_block = block["block"]
        params = old_rf_block.to_dict()
        params.pop("type", None)
        params.update(req.params)
        block["block"] = type(old_rf_block)(**params)
    return {"ok": True}

@router.delete("/rf/blocks/{id}")
async def delete_block(id: int):

    del rf_session.rf_blocks[id]

    return {"ok": True}
@router.get("/rf/components")
async def list_components():

    out=[]

    for i,c in enumerate(rf_session.synth._components):

        out.append(
            {
                "id": i,
                "enabled": c["enabled"],
                "waveform": c["waveform"].to_dict()
            }
        )

    return out
@router.post("/rf/components")
async def add_component(req: ComponentRequest):

    cls = WAVEFORM_REGISTRY[req.type]
    wf = cls(**req.params)

    rf_session.synth.add(wf)

    return {"ok": True}
from pydantic import BaseModel

class RunRequest(BaseModel): running: bool


@router.post("/rf/run")
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
@router.get("/rf/status")
async def status():
    return { "sample_rate": rf_session.latest_recording.iq.sample_rate,
             "freqs": (rf_session.analyzer.freqs + rf_session.synth.center_freq).tolist(),
             "fft_size": len(rf_session.analyzer.freqs),
             }
@router.websocket("/rf/stream")
async def rf_stream(websocket: WebSocket):
    await websocket.accept()

    try:

        while True:

            recording = rf_session.latest_recording
            enabled_blocks = [
                b["block"]
                for b in rf_session.rf_blocks
                if b["enabled"]]
            recording.iq = apply_chain(enabled_blocks, recording.iq)
            i_vis = recording.iq.samples.real
            q_vis = recording.iq.samples.imag
            if recording is not None:
                power_db = (rf_session.analyzer.fft(recording.iq, rf_session.window))
                header = struct.pack("<d", rf_session.synth.time_sec)
                payload = (
                        header
                        + power_db.astype(np.float32).tobytes()
                        + i_vis.astype(np.float32).tobytes()
                        + q_vis.astype(np.float32).tobytes()
                )
                await websocket.send_bytes(payload)

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