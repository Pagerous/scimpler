import pytest

from src.parser.resource.validators.error import ErrorGET, ErrorPOST


@pytest.fixture
def request_body():
    return {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        "userName": "bjensen",
        "externalId": "bjensen",
        "name": {
            "formatted": "Ms. Barbara J Jensen III",
            "familyName": "Jensen",
            "givenName": "Barbara",
        },
    }


@pytest.fixture
def response_headers():
    return {"Location": "https://example.com/v2/Users/2819c223-7f76-453a-919d-413861904646"}


@pytest.fixture
def response_body():
    return {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
        "status": "400",
        "scimType": "uniqueness",
        "detail": "you did wrong, bro",
    }


@pytest.fixture
def validator():
    return ErrorPOST()


def test_correct_error_body_passes_validation(validator, request_body, response_body):
    issues = validator.validate_response(
        request_body=request_body,
        response_body=response_body,
        status_code=400,
    )

    assert not issues


def test_error_status_should_be_equal_to_http_status(validator, request_body, response_body):
    response_body["status"] = "401"
    expected_issues = {
        "response": {
            "body": {"status": {"_errors": [{"code": 13}]}},
            "status": {"_errors": [{"code": 13}]},
        }
    }

    issues = validator.validate_response(
        request_body=request_body,
        response_body=response_body,
        status_code=400,
    )

    assert issues.to_dict() == expected_issues


def test_error_status_must_be_in_valid_range(validator, request_body, response_body):
    response_body["status"] = "600"
    expected_issues = {
        "response": {
            "body": {"status": {"_errors": [{"code": 12}]}},
            "status": {"_errors": [{"code": 12}]},
        }
    }

    issues = validator.validate_response(
        request_body=request_body,
        response_body=response_body,
        status_code=600,
    )

    assert issues.to_dict() == expected_issues
