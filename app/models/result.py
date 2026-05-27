from datetime import datetime

from sqlalchemy import (
    ForeignKey,
    Text,
    Float,
    DateTime,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from .base import Base


class Result(Base):
    __tablename__ = "results"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    job_id: Mapped[str] = mapped_column(
        ForeignKey("jobs.id"),
        nullable=False
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )

    metric: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    numeric_value: Mapped[float | None] = mapped_column(
        Float
    )

    text_value: Mapped[str | None] = mapped_column(
        Text
    )

    unit: Mapped[str | None]

    job = relationship(
        "Job",
        back_populates="results"
    )