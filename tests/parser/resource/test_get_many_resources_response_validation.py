import pytest

from src.parser.resource.schemas import USER
from src.parser.resource.validators.resource import (
    ResourceTypeGET,
    ServerRootResourceGET,
)


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
                    "location": "https://example.com/v2/Users/2819c223-7f76-453a-919d-413861904646",
                    "version": r"W\/\"f250dd84f0671c3\"",
                },
                "name": {
                    "formatted": "Ms. Barbara J Jensen III",
                    "familyName": "Jensen",
                    "givenName": "Barbara",
                },
                "userName": "bjensen",
                "emails": [
                    {
                        "value": "bjensen@example.com",
                        "type": "work",
                        "primary": True,
                    },
                    {
                        "value": "babs@jensen.org",
                        "type": "home",
                    },
                ],
                "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
                    "employeeNumber": "1",
                    "costCenter": "4130",
                    "organization": "Universal Studios",
                    "division": "Theme Park",
                    "department": "Tour Operations",
                    "manager": {
                        "value": "26118915-6090-4610-87e4-49d8ca9f808d",
                        "$ref": "../Users/26118915-6090-4610-87e4-49d8ca9f808d",
                        "displayName": "Jan Kowalski",
                    },
                },
            },
            {
                "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
                "id": "2819c223-7f76-453a-919d-413861904645",
                "externalId": "bjensen",
                "meta": {
                    "resourceType": "User",
                    "created": "2011-08-01T18:29:49.793Z",
                    "lastModified": "2011-08-01T18:29:49.793Z",
                    "location": "https://example.com/v2/Users/2819c223-7f76-453a-919d-413861904646",
                    "version": r"W\/\"f250dd84f0671c3\"",
                },
                "name": {
                    "formatted": "Ms. Barbara J Sven III",
                    "familyName": "Sven",
                    "givenName": "Barbara",
                },
                "userName": "sven",
                "emails": [
                    {
                        "value": "sven@example.com",
                        "type": "work",
                        "primary": True,
                    },
                    {
                        "value": "babs@sven.org",
                        "type": "home",
                    },
                ],
                "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
                    "employeeNumber": "2",
                    "costCenter": "4130",
                    "organization": "Universal Studios",
                    "division": "Theme Park",
                    "department": "Tour Operations",
                    "manager": {
                        "value": "26118915-6090-4610-87e4-49d8ca9f808d",
                        "$ref": "../Users/26118915-6090-4610-87e4-49d8ca9f808d",
                        "displayName": "John Smith",
                    },
                },
            },
        ],
    }


@pytest.mark.parametrize(
    "validator",
    (
        ResourceTypeGET(USER),
        ServerRootResourceGET([USER]),
    ),
)
def test_body_is_required(validator):
    expected_issues = {"response": {"body": {"_errors": [{"code": 15}]}}}

    issues = validator.validate_response(
        request_body=None,
        response_body=None,
        status_code=200,
    )

    assert issues.to_dict() == expected_issues


@pytest.mark.parametrize(
    "validator",
    (
        ResourceTypeGET(USER),
        ServerRootResourceGET([USER]),
    ),
)
def test_correct_body_passes_validation(validator, response_body):
    issues = validator.validate_response(
        request_body=None,
        response_body=response_body,
        response_headers=None,
        status_code=200,
    )

    assert not issues


@pytest.mark.parametrize(
    "validator",
    (
        ResourceTypeGET(USER),
        ServerRootResourceGET([USER]),
    ),
)
def test_missing_schemas_key_returns_error(validator, response_body):
    response_body.pop("schemas")
    expected_issues = {"response": {"body": {"schemas": {"_errors": [{"code": 1}]}}}}

    issues = validator.validate_response(
        request_body=None,
        response_body=response_body,
        response_headers=None,
        status_code=200,
    )

    assert issues.to_dict() == expected_issues


def test_validation_errors_for_resources_attribute_can_be_returned(response_body):
    validator = ResourceTypeGET(USER)
    response_body["Resources"][0]["userName"] = 123  # noqa
    response_body["Resources"][1]["userName"] = 123  # noqa
    expected_issues = {
        "response": {
            "body": {
                "resources": {
                    "0": {"username": {"_errors": [{"code": 2}]}},
                    "1": {"username": {"_errors": [{"code": 2}]}},
                }
            }
        }
    }

    issues = validator.validate_response(
        request_body=None,
        response_body=response_body,
        response_headers=None,
        status_code=200,
    )

    assert issues.to_dict() == expected_issues


@pytest.mark.parametrize(
    "validator",
    (
        ResourceTypeGET(USER),
        ServerRootResourceGET([USER]),
    ),
)
def test_status_code_must_be_200(validator, response_body):
    expected_issues = {"response": {"status": {"_errors": [{"code": 16}]}}}

    issues = validator.validate_response(
        request_body=None,
        response_body=response_body,
        response_headers=None,
        status_code=201,
    )

    assert issues.to_dict() == expected_issues


@pytest.mark.parametrize(
    "validator",
    (
        ResourceTypeGET(USER),
        ServerRootResourceGET([USER]),
    ),
)
def test_fails_if_more_resources_than_total_results(validator, response_body):
    response_body["totalResults"] = 1
    expected_issues = {
        "response": {
            "body": {
                "totalresults": {"_errors": [{"code": 22}]},
                "resources": {"_errors": [{"code": 22}]},
            }
        }
    }

    issues = validator.validate_response(
        request_body=None,
        response_body=response_body,
        response_headers=None,
        status_code=200,
    )

    assert issues.to_dict() == expected_issues


@pytest.mark.parametrize(
    "validator",
    (
        ResourceTypeGET(USER),
        ServerRootResourceGET([USER]),
    ),
)
def test_fails_if_less_resources_than_total_results_with_count_unspecified(
    validator,
    response_body,
):
    response_body["Resources"] = []
    expected_issues = {"response": {"body": {"resources": {"_errors": [{"code": 23}]}}}}

    issues = validator.validate_response(
        request_body=None,
        response_body=response_body,
        response_headers=None,
        status_code=200,
    )

    assert issues.to_dict() == expected_issues


@pytest.mark.parametrize(
    "validator",
    (
        ResourceTypeGET(USER),
        ServerRootResourceGET([USER]),
    ),
)
def test_fails_if_more_resources_than_specified_count(validator, response_body):
    expected_issues = {"response": {"body": {"resources": {"_errors": [{"code": 21}]}}}}

    issues = validator.validate_response(
        request_query_string={"count": 1},
        request_body=None,
        response_body=response_body,
        response_headers=None,
        status_code=200,
    )

    assert issues.to_dict() == expected_issues


@pytest.mark.parametrize(
    "validator",
    (
        ResourceTypeGET(USER),
        ServerRootResourceGET([USER]),
    ),
)
def test_fails_if_start_index_and_items_per_page_are_missing_when_pagination(
    validator,
    response_body,
):
    response_body["Resources"] = response_body["Resources"][:1]
    expected_issues = {
        "response": {
            "body": {
                "startindex": {"_errors": [{"code": 1}]},
                "itemsperpage": {"_errors": [{"code": 1}]},
            }
        }
    }

    issues = validator.validate_response(
        request_query_string={"count": 2},
        request_body=None,
        response_body=response_body,
        response_headers=None,
        status_code=200,
    )

    assert issues.to_dict() == expected_issues


@pytest.mark.parametrize(
    "validator",
    (
        ResourceTypeGET(USER),
        ServerRootResourceGET([USER]),
    ),
)
def test_fails_if_start_index_bigger_than_requested(validator, response_body):
    response_body["totalResults"] = 3
    response_body["startIndex"] = 2
    response_body["itemsPerPage"] = 2
    expected_issues = {
        "response": {
            "body": {
                "startindex": {"_errors": [{"code": 24}]},
            }
        }
    }

    issues = validator.validate_response(
        request_query_string={"count": 2, "startIndex": 1},
        request_body=None,
        response_body=response_body,
        response_headers=None,
        status_code=200,
    )

    assert issues.to_dict() == expected_issues


@pytest.mark.parametrize(
    "validator",
    (
        ResourceTypeGET(USER),
        ServerRootResourceGET([USER]),
    ),
)
def test_fails_if_items_per_page_do_not_match_resources(validator, response_body):
    response_body["totalResults"] = 3
    response_body["startIndex"] = 1
    response_body["itemsPerPage"] = 1
    expected_issues = {
        "response": {
            "body": {
                "itemsperpage": {"_errors": [{"code": 11}]},
                "resources": {"_errors": [{"code": 11}]},
            }
        }
    }

    issues = validator.validate_response(
        request_query_string={"count": 2, "startIndex": 1},
        request_body=None,
        response_body=response_body,
        response_headers=None,
        status_code=200,
    )

    assert issues.to_dict() == expected_issues


@pytest.mark.parametrize(
    "filter_exp",
    (
        'emails[value eq "sven@example.com"]',
        'emails eq "sven@example.com"',
        'name.familyName eq "Sven"',
    ),
)
def test_fails_if_output_resources_does_not_match_provided_filter(filter_exp, response_body):
    validator = ResourceTypeGET(USER)
    expected_issues = {
        "response": {
            "body": {
                "resources": {
                    "0": {
                        "_errors": [
                            {
                                "code": 25,
                            }
                        ]
                    }
                }
            }
        }
    }

    issues = validator.validate_response(
        request_query_string={"filter": filter_exp},
        response_body=response_body,
        status_code=200,
    )

    assert issues.to_dict() == expected_issues


def test_case_sensitive_attributes_are_validated_for_resource_type_endpoints(
    response_body,
):
    validator = ResourceTypeGET(USER)
    expected_issues = {
        "response": {
            "body": {
                "resources": {
                    "0": {
                        "_errors": [
                            {
                                "code": 25,
                            }
                        ]
                    },
                    "1": {
                        "_errors": [
                            {
                                "code": 25,
                            }
                        ]
                    },
                }
            }
        }
    }

    issues = validator.validate_response(
        request_query_string={"filter": 'meta.resourceType eq "user"'},
        response_body=response_body,
        status_code=200,
    )

    assert issues.to_dict() == expected_issues


@pytest.mark.parametrize(
    "filter_exp",
    (
        'meta.resourceType eq "Group"',
        'not name.givenName sw "B"',
    ),
)
def test_fails_if_output_resources_does_not_match_provided_filter_for_root_endpoint(
    filter_exp, response_body
):
    validator = ServerRootResourceGET([USER])
    expected_issues = {
        "response": {
            "body": {
                "resources": {
                    "0": {
                        "_errors": [
                            {
                                "code": 25,
                            }
                        ]
                    },
                    "1": {
                        "_errors": [
                            {
                                "code": 25,
                            }
                        ]
                    },
                }
            }
        }
    }

    issues = validator.validate_response(
        request_query_string={"filter": filter_exp},
        response_body=response_body,
        status_code=200,
    )

    assert issues.to_dict() == expected_issues


def test_case_sensitive_attributes_are_not_validated_for_server_root_endpoint(
    response_body,
):
    validator = ServerRootResourceGET([USER])

    issues = validator.validate_response(
        request_query_string={"filter": 'meta.resourceType eq "user"'},
        response_body=response_body,
        status_code=200,
    )

    assert not issues


@pytest.mark.parametrize(
    "attr_name",
    (
        "manager.displayName",
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:manager.displayName",
    ),
)
def test_fields_from_schema_extensions_are_checked_by_filter(
    attr_name,
    response_body,
):
    validator = ResourceTypeGET(USER)
    expected_issues = {
        "response": {
            "body": {
                "resources": {
                    "0": {
                        "_errors": [
                            {
                                "code": 25,
                            }
                        ]
                    },
                }
            }
        }
    }

    issues = validator.validate_response(
        request_query_string={"filter": f'{attr_name} eq "John Smith"'},
        response_body=response_body,
        status_code=200,
    )

    assert issues.to_dict() == expected_issues


@pytest.mark.parametrize(
    "validator",
    (
        ResourceTypeGET(USER),
        ServerRootResourceGET([USER]),
    ),
)
def test_fails_if_resources_are_not_sorted(validator, response_body):
    expected = {"response": {"body": {"resources": {"_errors": [{"code": 26}]}}}}

    issues = validator.validate_response(
        request_query_string={"sortBy": "name.familyName", "sortOrder": "descending"},
        response_body=response_body,
        status_code=200,
    )

    assert issues.to_dict() == expected


def test_sorting_is_not_checked_if_issues_for_related_values(response_body):
    validator = ResourceTypeGET(USER)
    response_body["Resources"][1]["name"]["familyName"] = 123  # noqa, bad type
    expected = {
        "response": {
            "body": {"resources": {"1": {"name": {"familyname": {"_errors": [{"code": 2}]}}}}}
        }
    }

    issues = validator.validate_response(
        request_query_string={"sortBy": "name.familyName", "sortOrder": "descending"},
        response_body=response_body,
        status_code=200,
    )

    assert issues.to_dict() == expected


def test_sorting_is_checked_if_issues_for_not_related_resource_values(response_body):
    validator = ResourceTypeGET(USER)
    response_body["Resources"][1]["name"]["givenName"] = 123  # noqa, bad type
    expected = {
        "response": {
            "body": {
                "resources": {
                    "_errors": [
                        {"code": 26},
                    ],
                    "1": {"name": {"givenname": {"_errors": [{"code": 2}]}}},
                }
            }
        }
    }

    issues = validator.validate_response(
        request_query_string={"sortBy": "name.familyName", "sortOrder": "descending"},
        response_body=response_body,
        status_code=200,
    )

    assert issues.to_dict() == expected


@pytest.mark.parametrize(
    "attr_name",
    (
        "manager.displayName",
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:manager.displayName",
    ),
)
def test_sorting_is_checked_on_attributes_from_schema_extensions(
    attr_name,
    response_body,
):
    validator = ResourceTypeGET(USER)
    expected = {"response": {"body": {"resources": {"_errors": [{"code": 26}]}}}}

    issues = validator.validate_response(
        request_query_string={"sortBy": attr_name, "sortOrder": "descending"},
        response_body=response_body,
        status_code=200,
    )

    assert issues.to_dict() == expected


def test_bad_schema_in_resources_is_discovered(response_body):
    validator = ResourceTypeGET(USER)
    response_body["Resources"][1]["schemas"] = ["bad:user:schema"]
    expected_issues = {
        "response": {"body": {"resources": {"1": {"schemas": {"_errors": [{"code": 20}]}}}}}
    }

    issues = validator.validate_response(
        response_body=response_body,
        status_code=200,
    )

    assert issues.to_dict() == expected_issues


def test_unknown_schema_in_resources_root_endpoint_is_discovered(response_body):
    validator = ServerRootResourceGET([USER])
    response_body["Resources"][1]["schemas"] = ["bad:user:schema"]
    expected_issues = {
        "response": {"body": {"resources": {"1": {"schemas": {"_errors": [{"code": 27}]}}}}}
    }

    issues = validator.validate_response(
        response_body=response_body,
        status_code=200,
    )

    assert issues.to_dict() == expected_issues
