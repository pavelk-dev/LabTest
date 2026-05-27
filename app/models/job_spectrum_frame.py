import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    Text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import (
    Mapped,
    mapped_column
)

from .base import (
    Base,
    TimestampMixin
)


class JobSpectrumFrame(
    Base,
    TimestampMixin
):
    __tablename__ = (
        "job_spectrum_frames"
    )

    id: Mapped[uuid.UUID] = (
        mapped_column(
            UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4
        )
    )

    job_id: Mapped[uuid.UUID] = (
        mapped_column(
            ForeignKey("jobs.id")
        )
    )

    frame_index: Mapped[int] = (
        mapped_column(Integer)
    )

    timestamp: Mapped[datetime] = (
        mapped_column(
            DateTime(
                timezone=True
            )
        )
    )

    spectrum_json: Mapped[str] = (
        mapped_column(Text)
    )