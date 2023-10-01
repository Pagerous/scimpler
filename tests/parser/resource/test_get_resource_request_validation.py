import pytest

from src.parser.resource.schemas import UserSchema
from src.parser.resource.validators.resource import ResourceGET


@pytest.fixture
def validator():
    return ResourceGET(UserSchema())


def test_body_is_ignored(validator):
    errors = validator.validate_request(body={"schemas": 123, "userName": 123})

    assert errors == []
