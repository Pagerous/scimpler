import pytest

from src.parser.schemas.validators import SchemaValidator
from src.parser.schemas.schemas import UserSchema, ErrorSchema, ListResponseSchema


@pytest.fixture
def validator():
    user_schema = UserSchema()
    return SchemaValidator(
        {
            ("urn:ietf:params:scim:api:messages:2.0:Error", ): ErrorSchema(),
            ("urn:ietf:params:scim:schemas:core:2.0:User", ): user_schema,
            ("urn:ietf:params:scim:api:messages:2.0:ListResponse", ): ListResponseSchema(),
        },
        {
            "User": user_schema
        }
    )
