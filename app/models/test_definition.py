import uuid

from sqlalchemy import Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class TestDefinition(Base, TimestampMixin):
    __tablename__ = "test_definitions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    name: Mapped[str]

    description: Mapped[str | None]

    yaml_content: Mapped[str] = mapped_column(Text)

    version: Mapped[int] = mapped_column(
        Integer,
        default=1
    )