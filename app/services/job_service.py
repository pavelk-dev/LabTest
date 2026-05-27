from uuid import uuid4
import json
import asyncio
from sqlalchemy.orm import Session
from datetime import datetime, UTC
from app.models.job import Job, JobStatus
from app.models.job_log import JobLog, LogLevel
from app.models.result import Result
from app.models.rf_scene_definition import RFSceneDefinition
from starlette.websockets import WebSocketDisconnect
from app.models.job_spectrum_frame import JobSpectrumFrame
from app.rf.spectrum_analyzer import SpectrumAnalyzer


from app.rf.scene_renderer import (
    RFSceneRenderer
)
from sqlalchemy import select

class JobService:
    def __init__(self, db: Session):
        self.db = db

    def create_job(
        self,
        test_definition_id,
        rf_scene_definition_id,
        yaml_snapshot: str
    ) -> Job:

        job = Job(
            id=uuid4(),
            status=JobStatus.QUEUED,
            test_definition_id=test_definition_id,
            rf_scene_definition_id=rf_scene_definition_id,
            yaml_snapshot=yaml_snapshot
        )

        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)

        return job

    async def stream_job(
            self,
            websocket,
            job_id,
            fs,
            fft,
            vbw
    ):
        await websocket.accept()

        job = self.db.get(
            Job,
            job_id
        )

        scene = self.db.get(
            RFSceneDefinition,
            job.rf_scene_definition_id
        )

        synth = RFSceneRenderer.render(
            scene.yaml_content
        )

        try:

            for recording in synth.stream(
                    chunk_size=fft
            ):
                analyzer = SpectrumAnalyzer(
                    recording.iq,
                    vbw_alpha=vbw
                )

                freqs, power_db = analyzer.fft()

                await websocket.send_json(
                    {
                        "freq_hz": freqs.tolist(),
                        "power_db": power_db.tolist()
                    }
                )

                await asyncio.sleep(
                    fft / fs
                )

        except WebSocketDisconnect:
            print(
                "stream disconnected"
            )

        except Exception as e:
            print(
                "stream error:",
                e
            )

        finally:
            try:
                await websocket.close()
            except:
                pass

    def run_job(self, job_id) -> Job:
        job = self.db.get(Job, job_id)

        if not job:
            raise ValueError("Job not found")

        scene = self.db.get(
            RFSceneDefinition,
            job.rf_scene_definition_id
        )

        if not scene:
            raise ValueError(
                "RF scene not found"
            )

        synth = RFSceneRenderer.render(scene.yaml_content)
        analyzer = SpectrumAnalyzer(recording.iq)
        freqs, power_db = analyzer.fft()
        print(power_db)
        self.db.add(
            JobSpectrumFrame(
                job_id=job.id,
                frame_index=0,
                timestamp=datetime.now(UTC),
                spectrum_json=json.dumps(
                    {
                        "freq_hz": freqs.tolist(),
                        "power_db": power_db.tolist()
                    }
                )
            )
        )

        self.db.add(
            JobLog(
                job_id=job.id,
                seq_num=1,
                timestamp=datetime.now(UTC),
                level=LogLevel.INFO,
                message="Spectrum synthesized"
            )
        )


        job.status = JobStatus.PASSED

        self.db.commit()
        self.db.refresh(job)

        return job

    def get_job(self, job_id) -> Job:
        job = self.db.get(Job, job_id)

        if not job:
            raise ValueError("Job not found")

        return job

    def list_jobs(self) -> list[Job]:
        stmt = select(Job)

        return list(
            self.db.scalars(stmt).all()
        )

    def get_spectrum(self,job_id):
        stmt = (
            select(JobSpectrumFrame)
            .where(JobSpectrumFrame.job_id == job_id)
            .order_by(JobSpectrumFrame.frame_index))

        frames = list(self.db.scalars(stmt).all())

        if not frames:
            raise ValueError(
                "No spectrum frames"
            )

        return json.loads(
            frames[-1].spectrum_json
        )
