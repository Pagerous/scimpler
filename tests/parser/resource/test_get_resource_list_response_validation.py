import pytest

from src.parser.resource.schemas import UserSchema
from src.parser.resource.validators.list_response import ListResponseResourceTypeGET


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
            },
            {
                "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
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


@pytest.fixture
def validator():
    return ListResponseResourceTypeGET(UserSchema())


def test_body_is_required(validator, request_body):
    expected_issues = {
        "response": {
            "body": {
                "_errors": [
                    {
                        "code": 15
                    }
                ]
            }
        }
    }

    issues = validator.validate_response(
        request_body=request_body,
        response_body=None,
        status_code=200,
    )

    assert issues.to_dict() == expected_issues


def test_correct_body_passes_validation(validator, request_body, response_body, response_headers):
    issues = validator.validate_response(
        request_body=request_body,
        response_body=response_body,
        response_headers=response_headers,
        status_code=200,
    )

    assert not issues


def test_missing_schemas_key_returns_error(
    validator, request_body, response_body, response_headers
):
    response_body.pop("schemas")
    expected_issues = {
        "response": {
            "body": {
                "schemas": {
                    "_errors": [
                        {
                            "code": 1
                        }
                    ]
                }
            }
        }
    }

    issues = validator.validate_response(
        request_body=request_body,
        response_body=response_body,
        response_headers=response_headers,
        status_code=200,
    )

    assert issues.to_dict() == expected_issues


def test_validation_errors_for_resources_attribute_can_be_returned_if_known_resource_type(
    validator, request_body, response_body, response_headers
):
    response_body["Resources"][0]["userName"] = 123  # noqa
    response_body["Resources"][1]["userName"] = 123  # noqa
    expected_issues = {
        "response": {
            "body": {
                "Resources": {
                    "0": {
                        "userName": {
                            "_errors": [
                                {
                                    "code": 2
                                }
                            ]
                        }
                    },
                    "1": {
                        "userName": {
                            "_errors": [
                                {
                                    "code": 2
                                }
                            ]
                        }
                    }
                }
            }
        }
    }

    issues = validator.validate_response(
        request_body=request_body,
        response_body=response_body,
        response_headers=response_headers,
        status_code=200,
    )

    assert issues.to_dict() == expected_issues


def test_status_code_must_be_200(validator, request_body, response_body, response_headers):
    expected_issues = {
        "response": {
            "status": {
                "_errors": [
                    {
                        "code": 16
                    }
                ]
            }
        }
    }
    issues = validator.validate_response(
        request_body=request_body,
        response_body=response_body,
        response_headers=response_headers,
        status_code=201,
    )

    assert issues.to_dict() == expected_issues
