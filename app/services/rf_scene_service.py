from uuid import UUID, uuid4
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.rf_scene_definition import (
    RFSceneDefinition
)


class RFSceneService:
    def __init__(self, db: Session):
        self.db = db

    def create_scene(
        self,
        name: str,
        description: str | None,
        yaml_content: str
    ) -> RFSceneDefinition:

        scene = RFSceneDefinition(
            id=uuid4(),
            name=name,
            description=description,
            yaml_content=yaml_content,
            version=1
        )

        self.db.add(scene)
        self.db.commit()
        self.db.refresh(scene)

        return scene

    def list_scenes(
        self
    ) -> list[RFSceneDefinition]:

        stmt = select(
            RFSceneDefinition
        )

        return list(
            self.db.scalars(stmt).all()
        )

    def get_scene(
        self,
        scene_id: UUID
    ) -> RFSceneDefinition:

        scene = self.db.get(
            RFSceneDefinition,
            scene_id
        )

        if not scene:
            raise ValueError(
                "RF scene not found"
            )

        return scene