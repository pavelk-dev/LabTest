from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.dependencies import get_db
from app.schemas.rf_scene import (
    RFSceneCreate,
    RFSceneResponse
)
from app.services.rf_scene_service import (
    RFSceneService
)

router = APIRouter()


@router.post(
    "/rf-scenes",
    response_model=RFSceneResponse
)
def create_rf_scene(
    payload: RFSceneCreate,
    db: Session = Depends(get_db)
):
    service = RFSceneService(db)

    return service.create_scene(
        name=payload.name,
        description=payload.description,
        yaml_content=payload.yaml_content
    )


@router.get(
    "/rf-scenes",
    response_model=list[RFSceneResponse]
)
def list_rf_scenes(
    db: Session = Depends(get_db)
):
    service = RFSceneService(db)

    return service.list_scenes()


@router.get(
    "/rf-scenes/{scene_id}",
    response_model=RFSceneResponse
)
def get_rf_scene(
    scene_id: UUID,
    db: Session = Depends(get_db)
):
    service = RFSceneService(db)

    return service.get_scene(scene_id)