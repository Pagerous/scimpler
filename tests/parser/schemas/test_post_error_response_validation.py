import pytest


@pytest.fixture
def request_body():
    return {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        "userName": "bjensen",
        "externalId": "bjensen",
        "name": {
            "formatted": "Ms. Barbara J Jensen III",
            "familyName": "Jensen",
            "givenName": "Barbara"
        }
    }


@pytest.fixture
def response_headers():
    return {
        "Location": "https://example.com/v2/Users/2819c223-7f76-453a-919d-413861904646"
    }


@pytest.fixture
def response_body():
    return {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
        "status": "400",
        "scimType": "uniqueness",
        "detail": "you did wrong, bro",
    }


def test_correct_error_body_passes_validation(validator, request_body, response_body):
    errors = validator.validate_response(
        http_method="POST",
        request_body=request_body,
        response_body=response_body,
        status_code=400,
    )

    assert errors == []


def test_error_status_should_be_equal_to_http_status(validator, request_body, response_body):
    response_body["status"] = "401"
    errors = validator.validate_response(
        http_method="POST",
        request_body=request_body,
        response_body=response_body,
        status_code=400,
    )

    assert len(errors) == 2
    assert errors[0].code == 13
    assert errors[0].location == "response.body.status"
    assert errors[1].code == 13
    assert errors[1].location == "response.status"


def test_error_status_must_be_in_valid_range(validator, request_body, response_body):
    response_body["status"] = "600"
    errors = validator.validate_response(
        http_method="POST",
        request_body=request_body,
        response_body=response_body,
        status_code=600,
    )

    assert len(errors) == 2
    assert errors[0].code == 12
    assert errors[0].location == "response.body.status"
    assert errors[1].code == 12
    assert errors[1].location == "response.status"
