import pytest

from src.parser.resource.schemas import USER
from src.parser.resource.validators.resource import ResourceTypePOST


@pytest.fixture
def validator():
    return ResourceTypePOST(USER)


def test_body_is_required(validator):
    expected_issues = {"request": {"body": {"_errors": [{"code": 15}]}}}

    issues = validator.validate_request(body=None)

    assert issues.to_dict() == expected_issues


def test_correct_body_passes_validation(validator):
    issues = validator.validate_request(
        body={
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "userName": "bjensen",
            "externalId": "bjensen",
            "name": {
                "formatted": "Ms. Barbara J Jensen III",
                "familyName": "Jensen",
                "givenName": "Barbara",
            },
        }
    )

    assert not issues


def test_bad_schema_is_discovered(validator):
    expected_issues = {"request": {"body": {"schemas": {"_errors": [{"code": 20}]}}}}

    issues = validator.validate_request(
        body={
            "schemas": ["bad:user:schema"],
            "userName": "bjensen",
            "externalId": "bjensen",
            "name": {
                "formatted": "Ms. Barbara J Jensen III",
                "familyName": "Jensen",
                "givenName": "Barbara",
            },
        }
    )

    assert issues.to_dict() == expected_issues


def test_many_validation_errors_can_be_returned(validator):
    expected_issues = {
        "request": {
            "body": {
                "username": {"_errors": [{"code": 1}]},
                "name": {"_errors": [{"code": 2}]},
            }
        }
    }

    errors = validator.validate_request(
        body={
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "externalId": "bjensen",
            "name": 123,
        }
    )

    assert errors.to_dict() == expected_issues


def test_external_id_may_be_omitted(validator):
    issues = validator.validate_request(
        body={
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "userName": "bjensen",
            "name": {
                "formatted": "Ms. Barbara J Jensen III",
                "familyName": "Jensen",
                "givenName": "Barbara",
            },
        }
    )

    assert not issues
