from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.dependencies import get_db
from app.schemas.test_definition import (
    TestDefinitionCreate,
    TestDefinitionResponse
)
from app.services.test_definition_service import (
    TestDefinitionService
)

router = APIRouter()


@router.post(
    "/test-definitions",
    response_model=TestDefinitionResponse
)
def create_test_definition(
    payload: TestDefinitionCreate,
    db: Session = Depends(get_db)
):
    service = TestDefinitionService(db)

    return service.create_test_definition(
        name=payload.name,
        description=payload.description,
        yaml_content=payload.yaml_content
    )


@router.get(
    "/test-definitions",
    response_model=list[TestDefinitionResponse]
)
def list_test_definitions(
    db: Session = Depends(get_db)
):
    service = TestDefinitionService(db)

    return service.list_test_definitions()


@router.get(
    "/test-definitions/{td_id}",
    response_model=TestDefinitionResponse
)
def get_test_definition(
    td_id: UUID,
    db: Session = Depends(get_db)
):
    service = TestDefinitionService(db)

    return service.get_test_definition(td_id)