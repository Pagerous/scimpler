import pytest

from src.parser.resource.schemas import USER
from src.parser.resource.validators.resource import ResourceObjectGET


@pytest.fixture
def validator():
    return ResourceObjectGET(USER)


def test_body_is_ignored(validator):
    issues = validator.validate_request(body={"schemas": 123, "userName": 123})

    assert not issues
