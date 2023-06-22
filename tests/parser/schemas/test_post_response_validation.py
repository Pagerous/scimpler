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
def response_body():
    return {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        "id": "2819c223-7f76-453a-919d-413861904646",
        "externalId": "bjensen",
        "meta": {
            "resourceType": "User",
            "created": "2011-08-01T21:32:44.882Z",
            "lastModified": "2011-08-01T21:32:44.882Z",
            "location":
            "https://example.com/v2/Users/2819c223-7f76-453a-919d-413861904646",
            "version": "W/\"e180ee84f0671b1\"",
        },
        "name": {
            "formatted": "Ms. Barbara J Jensen III",
            "familyName": "Jensen",
            "givenName": "Barbara",
        },
        "userName": "bjensen",
    }


@pytest.fixture
def response_headers():
    return {
        "Location": "https://example.com/v2/Users/2819c223-7f76-453a-919d-413861904646"
    }


@pytest.fixture
def response_error_body():
    return {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
        "status": "400",
        "scimType": "uniqueness",
        "detail": "you did wrong, bro",
    }


def test_body_is_not_required(validator, request_body):
    errors = validator.validate_response(
        http_method="POST",
        request_body=request_body,
        response_body=None,
        status_code=201
    )

    assert errors == []


def test_correct_body_passes_validation(validator, request_body, response_body, response_headers):
    errors = validator.validate_response(
        http_method="POST",
        request_body=request_body,
        response_body=response_body,
        response_headers=response_headers,
        status_code=201,
    )

    assert errors == []


def test_missing_schemas_key_returns_error(validator, request_body, response_body, response_headers):
    response_body.pop("schemas")

    errors = validator.validate_response(
        http_method="POST",
        request_body=request_body,
        response_body=response_body,
        response_headers=response_headers,
        status_code=201,
    )

    assert len(errors) == 1
    assert errors[0].code == 1
    assert errors[0].location == "response.body.schemas"


def test_many_validation_errors_can_be_returned(validator, request_body, response_body, response_headers):
    response_body["meta"]["created"] = "123"
    response_body["name"] = 123  # noqa

    errors = validator.validate_response(
        http_method="POST",
        request_body=request_body,
        response_body=response_body,
        response_headers=response_headers,
        status_code=201,
    )

    assert len(errors) == 2
    assert errors[0].code == 4
    assert errors[0].location == "response.body.meta.created"
    assert errors[1].code == 2
    assert errors[1].location == "response.body.name"


def test_location_header_is_required(validator, request_body, response_body):
    errors = validator.validate_response(
        http_method="POST",
        request_body=request_body,
        response_body=response_body,
        response_headers=None,
        status_code=201,
    )

    assert len(errors) == 1
    assert errors[0].code == 10
    assert errors[0].location == "response.headers"


def test_location_header_must_match_meta_location(validator, request_body, response_body, response_headers):
    response_body["meta"]["location"] = "https://example.com/v2/Users/different-id"

    errors = validator.validate_response(
        http_method="POST",
        request_body=request_body,
        response_body=response_body,
        response_headers=response_headers,
        status_code=201,
    )

    assert len(errors) == 2
    assert errors[0].code == 11
    assert errors[0].location == "response.body.meta.location"
    assert errors[1].code == 11
    assert errors[1].location == "response.headers"


def test_status_code_must_be_201(validator, request_body, response_body, response_headers):
    errors = validator.validate_response(
        http_method="POST",
        request_body=request_body,
        response_body=response_body,
        response_headers=response_headers,
        status_code=200,
    )

    assert len(errors) == 1
    assert errors[0].code == 16
    assert errors[0].location == "response.status"


def test_correct_error_body_passes_validation(validator, request_body, response_error_body):
    errors = validator.validate_response(
        http_method="POST",
        request_body=request_body,
        response_body=response_error_body,
        status_code=400,
    )

    assert errors == []


def test_error_status_should_be_equal_to_http_status(validator, request_body, response_error_body):
    response_error_body["status"] = "401"
    errors = validator.validate_response(
        http_method="POST",
        request_body=request_body,
        response_body=response_error_body,
        status_code=400,
    )

    assert len(errors) == 2
    assert errors[0].code == 13
    assert errors[0].location == "response.body.status"
    assert errors[1].code == 13
    assert errors[1].location == "response.status"


def test_error_status_must_be_in_valid_range(validator, request_body, response_error_body):
    response_error_body["status"] = "600"
    errors = validator.validate_response(
        http_method="POST",
        request_body=request_body,
        response_body=response_error_body,
        status_code=600,
    )

    assert len(errors) == 2
    assert errors[0].code == 12
    assert errors[0].location == "response.status"
    assert errors[1].code == 12
    assert errors[1].location == "response.body.status"


def test_resource_type_must_match(validator, request_body, response_body, response_headers):
    response_body["meta"]["resourceType"] = "BlaBla"
    errors = validator.validate_response(
        http_method="POST",
        request_body=request_body,
        response_body=response_body,
        response_headers=response_headers,
        status_code=201,
    )

    assert len(errors) == 1
    assert errors[0].code == 17
    assert errors[0].location == "response.body.meta.resourceType"
