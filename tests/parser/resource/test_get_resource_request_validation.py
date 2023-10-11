import pytest

from src.parser.resource.schemas import UserSchema
from src.parser.resource.validators.resource import ResourceObjectGET


@pytest.fixture
def validator():
    return ResourceObjectGET(UserSchema())


def test_body_is_ignored(validator):
    issues = validator.validate_request(body={"schemas": 123, "userName": 123})

    assert not issues
