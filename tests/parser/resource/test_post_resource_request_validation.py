import pytest

from src.parser.resource.schemas import UserSchema
from src.parser.resource.validators.resource import ResourcePOST


@pytest.fixture
def validator():
    return ResourcePOST(UserSchema())


def test_body_is_required(validator):
    errors = validator.validate_request(body=None)

    assert len(errors) == 1
    assert errors[0].code == 15


def test_correct_body_passes_validation(validator):
    errors = validator.validate_request(
        body={
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "userName": "bjensen",
            "externalId": "bjensen",
            "name": {
                "formatted": "Ms. Barbara J Jensen III",
                "familyName": "Jensen",
                "givenName": "Barbara"
            }
        }
    )

    assert errors == []


def test_missing_schemas_key_returns_error(validator):
    errors = validator.validate_request(
        body={
            "userName": "bjensen",
            "externalId": "bjensen",
            "name": {
                "formatted": "Ms. Barbara J Jensen III",
                "familyName": "Jensen",
                "givenName": "Barbara"
            }
        }
    )

    assert len(errors) == 1
    assert errors[0].code == 1
    assert errors[0].location == "request.body.schemas"


def test_many_validation_errors_can_be_returned(validator):
    errors = validator.validate_request(
        body={
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "externalId": "bjensen",
            "name": 123,
        }
    )

    assert len(errors) == 2
    assert errors[0].code == 1
    assert errors[0].location == "request.body.userName"
    assert errors[1].code == 2
    assert errors[1].location == "request.body.name"


def test_external_id_may_be_omitted(validator):
    errors = validator.validate_request(
        body={
             "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
             "userName": "bjensen",
             "name": {
                "formatted": "Ms. Barbara J Jensen III",
                "familyName": "Jensen",
                "givenName": "Barbara"
             }
        }
    )

    assert errors == []
