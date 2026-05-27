from uuid import UUID
from pydantic import BaseModel


class TestDefinitionCreate(BaseModel):
    name: str
    description: str | None = None
    yaml_content: str


class TestDefinitionResponse(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    yaml_content: str
    version: int