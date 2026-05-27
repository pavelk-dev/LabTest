from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.test_definition import TestDefinition


class TestDefinitionService:
    def __init__(self, db: Session):
        self.db = db

    def create_test_definition(
        self,
        name: str,
        description: str | None,
        yaml_content: str
    ) -> TestDefinition:

        td = TestDefinition(
            id=uuid4(),
            name=name,
            description=description,
            yaml_content=yaml_content,
            version=1
        )

        self.db.add(td)
        self.db.commit()
        self.db.refresh(td)

        return td

    def list_test_definitions(self) -> list[TestDefinition]:
        stmt = select(TestDefinition)

        return list(
            self.db.scalars(stmt).all()
        )

    def get_test_definition(self, td_id) -> TestDefinition:
        td = self.db.get(TestDefinition, td_id)

        if not td:
            raise ValueError("Test definition not found")

        return td