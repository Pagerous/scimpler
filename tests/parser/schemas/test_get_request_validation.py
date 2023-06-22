import pytest

from src.parser.schemas.validators import SchemaValidator
from src.parser.schemas.schemas import UserSchema, ErrorSchema


@pytest.fixture
def validator():
    return SchemaValidator(
        {
            ("urn:ietf:params:scim:api:messages:2.0:Error", ): ErrorSchema(),
            ("urn:ietf:params:scim:schemas:core:2.0:User", ): UserSchema(),
        }
    )


def test_body_is_ignored(validator):
    errors = validator.validate_request(http_method="GET", body={"schemas": 123, "userName": 123})

    assert errors == []
