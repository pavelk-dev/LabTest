from fastapi import APIRouter, WebSocket, HTTPException
from pydantic import BaseModel
from starlette.websockets import WebSocketDisconnect
import numpy as np
from app.rf.session import rf_session
from app.rf.waveform_registry import WAVEFORM_REGISTRY
from app.rf.rf_blocks_registry import RF_BLOCK_REGISTRY
from app.rf.demodulators import *
import asyncio
import struct
import json

from app.rf.rf_blocks import apply_chain

router = APIRouter()
fps = 20
frame_delta = 1 / fps
class DemodulatorConfig(BaseModel):
    type: str
    params: dict = {}
class RFSettings(BaseModel):
    center_freq: float
    sample_rate: float
    fft_size: int
    vbw: float
    constellation_mode: str = "raw"
    demodulator_graph : str = "time"

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
@router.get("/rf/demodulator")
async def get_demodulator():

    if rf_session.demodulator is None:
        return None

    return rf_session.demodulator.to_dict()
@router.post("/rf/demodulator")
async def set_demodulator(cfg: DemodulatorConfig):

    if cfg.type == "QAM":
        rf_session.demodulator = QAMDemodulator(
            **cfg.params
        )

    else:
        raise HTTPException(
            400,
            f"Unknown demodulator {cfg.type}"
        )

    return {"ok": True}

@router.patch("/rf/demodulator")
async def patch_demodulator(cfg: DemodulatorConfig):

    old = rf_session.demodulator

    if old is None:
        raise HTTPException(
            404,
            "No active demodulator"
        )

    params = old.to_dict()
    params.pop("type", None)

    params.update(cfg.params)

    rf_session.demodulator = type(old)(
        **params
    )

    return {"ok": True}
@router.delete("/rf/demodulator")
async def remove_demodulator():

    rf_session.demodulator = None

    return {"ok": True}
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
    rf_session.constellation_mode = settings.constellation_mode
    rf_session.demodulator_graph = settings.demodulator_graph

    return {"ok": True}
@router.get("/rf/status")
async def status():
    return { "sample_rate": rf_session.latest_recording.iq.sample_rate,
             "freqs": (rf_session.analyzer.freqs + rf_session.synth.center_freq).tolist(),
             "fft_size": len(rf_session.analyzer.freqs),
             }
@router.websocket("/rf/stream")
async def rf_stream(websocket: WebSocket):
    PACKET_RAW_IQ = 1
    PACKET_DEMOD = 2
    packet_type = PACKET_RAW_IQ
    await websocket.accept()
    try:
        while True:
            recording = rf_session.latest_recording
            enabled_blocks = [
                b["block"]
                for b in rf_session.rf_blocks
                if b["enabled"]]
            recording.iq = apply_chain(enabled_blocks, recording.iq)
            samples = recording.iq.samples

            result = None  # DemodResult, only set in "symbols" mode

            if rf_session.constellation_mode == "raw":
                rms = np.sqrt(np.mean(np.abs(samples) ** 2))
                normalized = samples / rms if rms > 0 else samples
                i_vis = normalized.real
                q_vis = normalized.imag
                packet_type = PACKET_RAW_IQ

            elif rf_session.constellation_mode == "symbols" and rf_session.demodulator is not None:
                result = rf_session.demodulator.demodulate(recording.iq)
                i_vis = result.recovered_symbols.real
                q_vis = result.recovered_symbols.imag
                packet_type = PACKET_DEMOD

            else:
                i_vis = np.empty(0, dtype=np.float32)
                q_vis = np.empty(0, dtype=np.float32)

            if recording is not None:
                power_db = rf_session.analyzer.fft(recording.iq, rf_session.window)
                scalars = {
                    "time_sec": rf_session.synth.time_sec,
                    "packet_type": packet_type,
                }
                if packet_type == PACKET_DEMOD and result is not None:
                    scalars.update({
                        "mean_evm_pct": result.mean_evm,
                        "mean_phase_error_deg": result.mean_phase_error_deg,
                    })
                await websocket.send_text(json.dumps(scalars))

                header = struct.pack("<I", len(i_vis))
                payload = (
                    header
                    + power_db.astype(np.float32).tobytes()
                    + i_vis.astype(np.float32).tobytes()
                    + q_vis.astype(np.float32).tobytes()
                )

                if packet_type == PACKET_DEMOD and result is not None:
                    if rf_session.demodulator_graph == "time":
                        payload += (
                            result.error_vectors.real.astype(np.float32).tobytes()
                            + result.error_vectors.imag.astype(np.float32).tobytes()
                            + result.evm_per_symbol.astype(np.float32).tobytes()
                            + result.phase_errors_deg.astype(np.float32).tobytes()
                        )
                    elif rf_session.demodulator_graph == "freq":
                        error_freqs, error_mag = rf_session.analyzer.spectrum(
                            result.error_vectors,
                            rf_session.demodulator.symbol_rate)
                        payload += (
                            error_freqs.astype(np.float32).tobytes()
                            + error_mag.astype(np.float32).tobytes()
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
        except Exception:
            pass