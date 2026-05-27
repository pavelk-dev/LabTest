from fastapi import APIRouter, Depends, WebSocket
from sqlalchemy.orm import Session
from typing import List

from db.dependencies import get_db
from app.schemas.job import (
    JobCreate,
    JobResponse,
    JobDetailResponse
)
from app.services.job_service import JobService
from uuid import UUID

router = APIRouter()


@router.post("/jobs", response_model=JobResponse)
def create_job(
    payload: JobCreate,
    db: Session = Depends(get_db)
):
    service = JobService(db)

    return service.create_job(
        test_definition_id=payload.test_definition_id,
        rf_scene_definition_id=payload.rf_scene_definition_id,
        yaml_snapshot=payload.yaml_snapshot
    )

@router.get("/jobs/{job_id}", response_model=JobDetailResponse)
def get_job(
    job_id: UUID,
    db: Session = Depends(get_db)
):
    service = JobService(db)

    return service.get_job(job_id)
@router.post("/jobs/{job_id}/run", response_model=JobResponse)
def run_job(
    job_id: UUID,
    db: Session = Depends(get_db)
):
    service = JobService(db)

    job = service.run_job(job_id)

    return job
@router.get("/jobs/{job_id}/spectrum")
def get_spectrum(
    job_id: UUID,
    db: Session = Depends(get_db)
):
    service = JobService(db)

    return service.get_spectrum(job_id)

@router.websocket(
    "/jobs/{job_id}/stream"
)
async def stream_job(
    websocket: WebSocket,
    job_id: UUID,
    db: Session = Depends(get_db)
):

    fs = float(
        websocket.query_params.get(
            "fs",
            20e6
        )
    )

    fft = int(
        websocket.query_params.get(
            "fft",
            4096
        )
    )

    vbw = float(
        websocket.query_params.get(
            "vbw",
            0.2
        )
    )

    service = JobService(
        db
    )

    await service.stream_job(
        websocket,
        job_id,
        fs,
        fft,
        vbw
    )
@router.get("/jobs", response_model=list[JobResponse])
def list_jobs(
    db: Session = Depends(get_db)
):
    service = JobService(db)

    return service.list_jobs()