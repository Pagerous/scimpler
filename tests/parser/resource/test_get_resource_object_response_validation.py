import pytest

from src.parser.resource.schemas import UserSchema
from src.parser.resource.validators.resource import ResourceObjectGET


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
    return ResourceObjectGET(UserSchema())


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


def test_many_validation_errors_can_be_returned(
    validator, request_body, response_body, response_headers
):
    response_body["meta"]["created"] = "123"
    response_body["name"] = 123  # noqa
    expected_issues = {
        "response": {
            "body": {
                "meta": {
                    "created": {
                        "_errors": [
                            {
                                "code": 4
                            }
                        ]
                    }
                },
                "name": {
                    "_errors": [
                        {
                            "code": 2
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


def test_location_header_is_not_required(validator, request_body, response_body):
    issues = validator.validate_response(
        request_body=request_body,
        response_body=response_body,
        response_headers=None,
        status_code=200,
    )

    assert not issues


def test_location_header_if_passed_must_match_meta_location(
    validator, request_body, response_body, response_headers
):
    response_body["meta"]["location"] = "https://example.com/v2/Users/different-id"
    expected_issues = {
        "response": {
            "body": {
                "meta": {
                    "location": {
                        "_errors": [
                            {
                                "code": 11
                            }
                        ]
                    }
                }
            },
            "headers": {
                "Location": {
                    "_errors": [
                        {
                            "code": 11
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


def test_resource_type_must_match(validator, request_body, response_body, response_headers):
    response_body["meta"]["resourceType"] = "BlaBla"
    expected_issues = {
        "response": {
            "body": {
                "meta": {
                    "resourceType": {
                        "_errors": [
                            {
                                "code": 17
                            }
                        ]
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
