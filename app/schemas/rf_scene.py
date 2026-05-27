import uuid
from pydantic import BaseModel


class RFSceneCreate(BaseModel):
    name: str
    description: str | None = None
    yaml_content: str


class RFSceneResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    yaml_content: str
    version: int

    class Config:
        from_attributes = True