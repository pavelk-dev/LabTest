import uuid
from datetime import datetime

from sqlalchemy import (
    Enum,
    ForeignKey,
    Text,
    DateTime,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from .base import Base, TimestampMixin
from .enums import JobStatus


class Job(Base, TimestampMixin):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus),
        default=JobStatus.QUEUED,
        nullable=False
    )

    test_definition_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("test_definitions.id"),
        nullable=False
    )
    rf_scene_definition_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rf_scene_definitions.id"),
        nullable=True
    )

    yaml_snapshot: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    worker_id: Mapped[str | None]

    error_message: Mapped[str | None]

    test_definition = relationship(
        "TestDefinition"
    )

    logs = relationship(
        "JobLog",
        back_populates="job",
        cascade="all, delete-orphan"
    )

    results = relationship(
        "Result",
        back_populates="job",
        cascade="all, delete-orphan"
    )