import pytest

from src.parser.resource.schemas import UserSchema
from src.parser.resource.validators.resource import ResourceGET


@pytest.fixture
def request_body():
    return None


@pytest.fixture
def response_body():
    return {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        "id": "2819c223-7f76-453a-919d-413861904646",
        "externalId": "bjensen",
        "meta": {
            "resourceType": "User",
            "created": "2011-08-01T18:29:49.793Z",
            "lastModified": "2011-08-01T18:29:49.793Z",
            "location":
            "https://example.com/v2/Users/2819c223-7f76-453a-919d-413861904646",
            "version": r"W\/\"f250dd84f0671c3\""
        },
        "name": {
            "formatted": "Ms. Barbara J Jensen III",
            "familyName": "Jensen",
            "givenName": "Barbara"
        },
        "userName": "bjensen",
        "phoneNumbers": [
            {
                "value": "555-555-8377",
                "type": "work"
            }
        ],
        "emails": [
            {
                "value": "bjensen@example.com",
                "type": "work"
            }
        ]
    }


@pytest.fixture
def response_headers():
    return {
        "Location": "https://example.com/v2/Users/2819c223-7f76-453a-919d-413861904646"
    }


@pytest.fixture
def validator():
    return ResourceGET(UserSchema())


def test_body_is_required(validator, request_body):
    errors = validator.validate_response(
        request_body=request_body,
        response_body=None,
        status_code=200,
    )

    assert len(errors) == 1
    assert errors[0].code == 15
    assert errors[0].location == "response.body"


def test_correct_body_passes_validation(validator, request_body, response_body, response_headers):
    errors = validator.validate_response(
        request_body=request_body,
        response_body=response_body,
        response_headers=response_headers,
        status_code=200,
    )

    assert errors == []


def test_missing_schemas_key_returns_error(validator, request_body, response_body, response_headers):
    response_body.pop("schemas")

    errors = validator.validate_response(
        request_body=request_body,
        response_body=response_body,
        response_headers=response_headers,
        status_code=200,
    )

    assert len(errors) == 1
    assert errors[0].code == 1
    assert errors[0].location == "response.body.schemas"


def test_many_validation_errors_can_be_returned(validator, request_body, response_body, response_headers):
    response_body["meta"]["created"] = "123"
    response_body["name"] = 123  # noqa

    errors = validator.validate_response(
        request_body=request_body,
        response_body=response_body,
        response_headers=response_headers,
        status_code=200,
    )

    assert len(errors) == 2
    assert errors[0].code == 4
    assert errors[0].location == "response.body.meta.created"
    assert errors[1].code == 2
    assert errors[1].location == "response.body.name"


def test_location_header_is_not_required(validator, request_body, response_body):
    errors = validator.validate_response(
        request_body=request_body,
        response_body=response_body,
        response_headers=None,
        status_code=200,
    )

    assert errors == []


def test_location_header_if_passed_must_match_meta_location(validator, request_body, response_body, response_headers):
    response_body["meta"]["location"] = "https://example.com/v2/Users/different-id"

    errors = validator.validate_response(
        request_body=request_body,
        response_body=response_body,
        response_headers=response_headers,
        status_code=200,
    )

    assert len(errors) == 2
    assert errors[0].code == 11
    assert errors[0].location == "response.body.meta.location"
    assert errors[1].code == 11
    assert errors[1].location == "response.headers"


def test_status_code_must_be_200(validator, request_body, response_body, response_headers):
    errors = validator.validate_response(
        request_body=request_body,
        response_body=response_body,
        response_headers=response_headers,
        status_code=201,
    )

    assert len(errors) == 1
    assert errors[0].code == 16
    assert errors[0].location == "response.status"


def test_resource_type_must_match(validator, request_body, response_body, response_headers):
    response_body["meta"]["resourceType"] = "BlaBla"
    errors = validator.validate_response(
        request_body=request_body,
        response_body=response_body,
        response_headers=response_headers,
        status_code=200,
    )

    assert len(errors) == 1
    assert errors[0].code == 17
    assert errors[0].location == "response.body.meta.resourceType"
