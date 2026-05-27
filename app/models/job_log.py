from datetime import datetime

from sqlalchemy import (
    Enum,
    ForeignKey,
    Text,
    DateTime,
    Integer,
    UniqueConstraint,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from .base import Base
from .enums import LogLevel


class JobLog(Base):
    __tablename__ = "job_logs"

    __table_args__ = (
        UniqueConstraint(
            "job_id",
            "seq_num",
            name="uq_joblog_seq_per_job"
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    job_id: Mapped[str] = mapped_column(
        ForeignKey("jobs.id"),
        nullable=False
    )

    seq_num: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )

    level: Mapped[LogLevel] = mapped_column(
        Enum(LogLevel),
        nullable=False
    )

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    job = relationship(
        "Job",
        back_populates="logs"
    )