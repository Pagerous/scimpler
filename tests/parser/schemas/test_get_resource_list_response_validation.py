import pytest


@pytest.fixture
def request_body():
    return None


@pytest.fixture
def response_body():
    return {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "totalResults": 2,
        "Resources": [
            {
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
            },
            {
                "id": "2819c223-7f76-453a-919d-413861904647",
                "externalId": "hehe",
                "meta": {
                    "resourceType": "User",
                    "created": "2011-08-01T18:29:49.793Z",
                    "lastModified": "2011-08-01T18:29:49.793Z",
                    "location":
                        "https://example.com/v2/Users/2819c223-7f76-453a-919d-413861904647",
                    "version": r"W\/\"f250dd84f0671c3\""
                },
                "name": {
                    "formatted": "Ms. Barbara J Jensen III",
                    "familyName": "Jensen",
                    "givenName": "Barbara"
                },
                "userName": "hehe",
            }
        ]
    }


@pytest.fixture
def response_headers():
    return None


def test_body_is_required(validator, request_body):
    errors = validator.validate_response(
        http_method="GET",
        request_body=request_body,
        response_body=None,
        status_code=200,
        resource_type="User",
    )

    assert len(errors) == 1
    assert errors[0].code == 15
    assert errors[0].location == "response.body"


def test_correct_body_passes_validation(validator, request_body, response_body, response_headers):
    errors = validator.validate_response(
        http_method="GET",
        request_body=request_body,
        response_body=response_body,
        response_headers=response_headers,
        status_code=200,
        resource_type="User",
    )

    assert errors == []


def test_missing_schemas_key_returns_error(validator, request_body, response_body, response_headers):
    response_body.pop("schemas")

    errors = validator.validate_response(
        http_method="GET",
        request_body=request_body,
        response_body=response_body,
        response_headers=response_headers,
        status_code=200,
        resource_type="User",
    )

    assert len(errors) == 1
    assert errors[0].code == 1
    assert errors[0].location == "response.body.schemas"


def test_validation_errors_for_resources_attribute_can_be_returned_if_known_resource_type(
    validator, request_body, response_body, response_headers
):
    response_body["Resources"][0]["userName"] = 123
    response_body["Resources"][1]["userName"] = 123

    errors = validator.validate_response(
        http_method="GET",
        request_body=request_body,
        response_body=response_body,
        response_headers=response_headers,
        status_code=200,
        resource_type="User",
    )

    assert len(errors) == 2
    assert errors[0].code == 2
    assert errors[0].location == "response.body.Resources.0.userName"
    assert errors[1].code == 2
    assert errors[1].location == "response.body.Resources.1.userName"


def test_validation_errors_for_resources_attribute_are_not_returned_if_unknown_resource_type(
    validator, request_body, response_body, response_headers
):
    response_body["Resources"][0]["userName"] = 123
    response_body["Resources"][1]["userName"] = 123

    errors = validator.validate_response(
        http_method="GET",
        request_body=request_body,
        response_body=response_body,
        response_headers=response_headers,
        status_code=200,  # missing 'resource_type' parameter
    )

    assert errors == []


def test_status_code_must_be_200(validator, request_body, response_body, response_headers):
    errors = validator.validate_response(
        http_method="GET",
        request_body=request_body,
        response_body=response_body,
        response_headers=response_headers,
        status_code=201,
    )

    assert len(errors) == 1
    assert errors[0].code == 16
    assert errors[0].location == "response.status"
