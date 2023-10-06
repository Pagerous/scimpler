import pytest

from src.parser.resource.schemas import UserSchema
from src.parser.resource.validators.list_response import ListResponseResourceObjectGET, \
    ListResponseResourceTypeGET, ListResponseServerRootGET


@pytest.fixture
def request_body():
    return None


@pytest.fixture
def response_body():
    return {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "totalResults": 1,
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
        ]
    }


@pytest.fixture
def response_headers():
    return None


@pytest.mark.parametrize(
    "validator",
    (
        ListResponseResourceObjectGET(UserSchema()),
        ListResponseResourceTypeGET(UserSchema()),
        ListResponseServerRootGET([UserSchema()]),
    )
)
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


@pytest.mark.parametrize(
    "validator",
    (
        ListResponseResourceObjectGET(UserSchema()),
        ListResponseResourceTypeGET(UserSchema()),
        ListResponseServerRootGET([UserSchema()]),
    )
)
def test_correct_body_passes_validation(validator, request_body, response_body, response_headers):
    issues = validator.validate_response(
        request_body=request_body,
        response_body=response_body,
        response_headers=response_headers,
        status_code=200,
    )

    assert not issues


@pytest.mark.parametrize(
    "validator",
    (
        ListResponseResourceObjectGET(UserSchema()),
        ListResponseResourceTypeGET(UserSchema()),
        ListResponseServerRootGET([UserSchema()]),
    )
)
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


@pytest.mark.parametrize(
    "validator",
    (
        ListResponseResourceObjectGET(UserSchema()),
        ListResponseResourceTypeGET(UserSchema()),
    )
)
def test_validation_errors_for_resources_attribute_can_be_returned(
    validator, request_body, response_body, response_headers
):
    response_body["Resources"][0]["userName"] = 123  # noqa
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


@pytest.mark.parametrize(
    "validator",
    (
        ListResponseResourceObjectGET(UserSchema()),
        ListResponseResourceTypeGET(UserSchema()),
        ListResponseServerRootGET([UserSchema()]),
    )
)
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


@pytest.mark.parametrize(
    "validator",
    (
        ListResponseResourceObjectGET(UserSchema()),
        ListResponseResourceTypeGET(UserSchema()),
        ListResponseServerRootGET([UserSchema()]),
    )
)
def test_fails_if_more_resources_than_total_results(
    validator, request_body, response_body, response_headers
):
    response_body["totalResults"] = 0
    expected_issues = {
        "response": {
            "body": {
                "totalResults": {
                    "_errors": [
                        {
                            "code": 22
                        }
                    ]
                },
                "Resources": {
                    "_errors": [
                        {
                            "code": 22
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


@pytest.mark.parametrize(
    "validator",
    (
        ListResponseResourceObjectGET(UserSchema()),
        ListResponseResourceTypeGET(UserSchema()),
        ListResponseServerRootGET([UserSchema()]),
    )
)
def test_fails_if_less_resources_than_total_results_with_count_unspecified(
    validator, request_body, response_body, response_headers
):
    response_body["Resources"] = []
    expected_issues = {
        "response": {
            "body": {
                "Resources": {
                    "_errors": [
                        {
                            "code": 23
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


@pytest.mark.parametrize(
    "validator",
    (
        ListResponseResourceObjectGET(UserSchema()),
        ListResponseResourceTypeGET(UserSchema()),
        ListResponseServerRootGET([UserSchema()]),
    )
)
def test_fails_if_more_resources_than_specified_count(
    validator, request_body, response_body, response_headers
):
    expected_issues = {
        "response": {
            "body": {
                "Resources": {
                    "_errors": [
                        {
                            "code": 21
                        }
                    ]
                }
            }
        }
    }

    issues = validator.validate_response(
        request_query_string={"count": 0},
        request_body=request_body,
        response_body=response_body,
        response_headers=response_headers,
        status_code=200,
    )

    assert issues.to_dict() == expected_issues


@pytest.mark.parametrize(
    "validator",
    (
        ListResponseResourceObjectGET(UserSchema()),
        ListResponseResourceTypeGET(UserSchema()),
        ListResponseServerRootGET([UserSchema()]),
    )
)
def test_fails_if_start_index_and_items_per_page_are_missing_when_pagination(
    validator, request_body, response_body, response_headers
):
    response_body["Resources"] = []
    expected_issues = {
        "response": {
            "body": {
                "startIndex": {
                    "_errors": [
                        {
                            "code": 1
                        }
                    ]
                },
                "itemsPerPage": {
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
        request_query_string={"count": 1},
        request_body=request_body,
        response_body=response_body,
        response_headers=response_headers,
        status_code=200,
    )

    assert issues.to_dict() == expected_issues


@pytest.mark.parametrize(
    "validator",
    (
        ListResponseResourceTypeGET(UserSchema()),
        ListResponseServerRootGET([UserSchema()]),
    )
)
def test_fails_if_start_index_bigger_than_requested(
    validator, request_body, response_body, response_headers
):
    response_body["totalResults"] = 2
    response_body["startIndex"] = 2
    response_body["itemsPerPage"] = 1
    expected_issues = {
        "response": {
            "body": {
                "startIndex": {
                    "_errors": [
                        {
                            "code": 24
                        }
                    ]
                },
            }
        }
    }

    issues = validator.validate_response(
        request_query_string={"count": 1, "startIndex": 1},
        request_body=request_body,
        response_body=response_body,
        response_headers=response_headers,
        status_code=200,
    )

    assert issues.to_dict() == expected_issues


@pytest.mark.parametrize(
    "validator",
    (
        ListResponseResourceTypeGET(UserSchema()),
        ListResponseServerRootGET([UserSchema()]),
    )
)
def test_fails_if_items_per_page_do_not_match_resources(
    validator, request_body, response_body, response_headers
):
    response_body["totalResults"] = 2
    response_body["startIndex"] = 1
    response_body["itemsPerPage"] = 1
    response_body["Resources"].append(response_body["Resources"][0].copy())
    expected_issues = {
        "response": {
            "body": {
                "itemsPerPage": {
                    "_errors": [
                        {
                            "code": 11
                        }
                    ]
                },
                "Resources": {
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
        request_query_string={"count": 2, "startIndex": 1},
        request_body=request_body,
        response_body=response_body,
        response_headers=response_headers,
        status_code=200,
    )

    assert issues.to_dict() == expected_issues


def test_fails_if_more_than_one_result_for_resource_object(
    request_body, response_body, response_headers
):
    validator = ListResponseResourceObjectGET(UserSchema())
    response_body["totalResults"] = 2
    response_body["Resources"].append(response_body["Resources"][0].copy())
    expected_issues = {
        "response": {
            "body": {
                "Resources": {
                    "_errors": [
                        {
                            "code": 21
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
