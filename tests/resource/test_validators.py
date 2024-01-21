from copy import deepcopy
from datetime import datetime

import pytest

from src.attributes.attributes import AttributeName, Missing
from src.attributes_presence import AttributePresenceChecker
from src.filter.filter import Filter
from src.filter.operator import Equal, Present
from src.patch import PatchPath
from src.resource.schemas import ERROR, USER
from src.resource.validators import (
    Error,
    ResourceObjectGET,
    ResourceObjectPUT,
    ResourceTypeGET,
    ResourceTypePOST,
    SearchRequestPOST,
    ServerRootResourceGET,
    dump_resources,
    filter_unknown_fields,
    infer_schema_from_data,
    parse_body,
    parse_operations,
    parse_request_filtering,
    parse_request_sorting,
    parse_requested_attributes,
    validate_dict_type,
    validate_error_status_code,
    validate_error_status_code_consistency,
    validate_existence,
    validate_items_per_page_consistency,
    validate_number_of_resources,
    validate_operation_path,
    validate_pagination_info,
    validate_resource_location_consistency,
    validate_resource_location_in_header,
    validate_resource_type_consistency,
    validate_resources_attribute_presence,
    validate_resources_filtered,
    validate_resources_schemas_field,
    validate_resources_sorted,
    validate_schemas_field,
    validate_start_index_consistency,
    validate_status_code,
)
from src.sorter import Sorter


@pytest.fixture
def user_data_dump():
    return {
        "schemas": [
            "urn:ietf:params:scim:schemas:core:2.0:User",
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
        ],
        "id": "2819c223-7f76-453a-919d-413861904646",
        "externalId": "bjensen",
        "meta": {
            "resourceType": "User",
            "created": datetime(2011, 8, 1, 18, 29, 49),
            "lastModified": datetime(2011, 8, 1, 18, 29, 49),
            "location": "https://example.com/v2/Users/2819c223-7f76-453a-919d-413861904646",
            "version": r"W\/\"f250dd84f0671c3\"",
        },
        "name": {
            "formatted": "Ms. Barbara J Jensen III",
            "familyName": "Jensen",
            "givenName": "Barbara",
        },
        "userName": "bjensen",
        "phoneNumbers": [{"value": "555-555-8377", "type": "work"}],
        "emails": [{"value": "bjensen@example.com", "type": "work"}],
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
    }


@pytest.fixture
def user_data_parse(user_data_dump):
    data = deepcopy(user_data_dump)
    data["meta"]["created"] = user_data_dump["meta"]["created"].isoformat()
    data["meta"]["lastModified"] = user_data_dump["meta"]["lastModified"].isoformat()
    return data


@pytest.fixture
def error_data():
    return {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
        "status": "400",
        "scimType": "tooMany",
        "detail": "you did wrong, bro",
    }


@pytest.fixture
def list_user_data():
    return {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "totalResults": 2,
        "Resources": [
            {
                "schemas": [
                    "urn:ietf:params:scim:schemas:core:2.0:User",
                    "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
                ],
                "id": "2819c223-7f76-453a-919d-413861904646",
                "externalId": "bjensen",
                "meta": {
                    "resourceType": "User",
                    "created": datetime(2011, 8, 1, 18, 29, 49),
                    "lastModified": datetime(2011, 8, 1, 18, 29, 49),
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
                "schemas": [
                    "urn:ietf:params:scim:schemas:core:2.0:User",
                    "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
                ],
                "id": "2819c223-7f76-453a-919d-413861904645",
                "externalId": "bjensen",
                "meta": {
                    "resourceType": "User",
                    "created": datetime(2011, 8, 1, 18, 29, 49),
                    "lastModified": datetime(2011, 8, 1, 18, 29, 49),
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
    ("body", "expected"), (({}, {}), (None, {"_errors": [{"code": 15}]}), ({"a": 1, "b": 2}, {}))
)
def test_validate_body_existence(body, expected):
    issues = validate_existence(body)

    assert issues.to_dict() == expected


@pytest.mark.parametrize(
    ("body", "expected"), (({}, {}), ([], {"_errors": [{"code": 18}]}), ({"a": 1, "b": 2}, {}))
)
def test_validate_body_type(body, expected):
    issues = validate_dict_type(body)

    assert issues.to_dict() == expected


def test_parse_body__succeeds_for_correct_data(user_data_parse):
    body, issues = parse_body(user_data_parse, USER)

    assert issues.to_dict() == {}


def test_parse_body__fails_for_incorrect_data(user_data_parse):
    user_data_parse["userName"] = 123  # noqa
    user_data_parse["name"]["givenName"] = 123  # noqa
    expected = {
        "username": {
            "_errors": [
                {
                    "code": 2,
                }
            ]
        },
        "name": {
            "givenname": {
                "_errors": [
                    {
                        "code": 2,
                    }
                ]
            }
        },
    }

    body, issues = parse_body(user_data_parse, USER)

    assert issues.to_dict() == expected


def test_validate_schemas_field__succeeds_for_correct_data(user_data_dump):
    issues = validate_schemas_field(user_data_dump, USER)

    assert issues.to_dict() == {}


def test_validate_schemas_field__fails_if_non_matching_schema(user_data_dump):
    user_data_dump["schemas"].append("bad:user:schema")
    expected = {"schemas": {"_errors": [{"code": 27}]}}

    issues = validate_schemas_field(user_data_dump, USER)

    assert issues.to_dict() == expected


def test_validate_schemas_field__fails_if_main_schema_is_missing(user_data_dump):
    user_data_dump["schemas"] = ["urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"]
    expected = {"schemas": {"_errors": [{"code": 28}]}}

    issues = validate_schemas_field(user_data_dump, USER)

    assert issues.to_dict() == expected


def test_validate_schemas_field__fails_if_extension_schema_is_missing(user_data_dump):
    user_data_dump["schemas"] = ["urn:ietf:params:scim:schemas:core:2.0:User"]
    expected = {"schemas": {"_errors": [{"code": 29}]}}

    issues = validate_schemas_field(user_data_dump, USER)

    assert issues.to_dict() == expected


def test_validate_schemas_field__multiple_errors(user_data_dump):
    user_data_dump["schemas"] = ["bad:user:schema"]
    expected = {"schemas": {"_errors": [{"code": 27}, {"code": 28}, {"code": 29}]}}

    issues = validate_schemas_field(user_data_dump, USER)

    assert issues.to_dict() == expected


def test_validate_schemas_field__skips_schema_items_with_bad_type(user_data_dump):
    user_data_dump["schemas"].extend([123, "bad:user:schema"])
    expected = {"schemas": {"_errors": [{"code": 27}]}}

    issues = validate_schemas_field(user_data_dump, USER)

    assert issues.to_dict() == expected


@pytest.mark.parametrize(
    ("status_code", "expected"),
    (
        (199, {"response": {"status": {"_errors": [{"code": 12}]}}}),
        (600, {"response": {"status": {"_errors": [{"code": 12}]}}}),
        (404, {}),
    ),
)
def test_validate_error_status_code(status_code, expected):
    issues = validate_error_status_code(status_code)

    assert issues.to_dict() == expected


@pytest.mark.parametrize(
    ("status_code", "expected"),
    (
        (
            404,
            {
                "response": {
                    "status": {"_errors": [{"code": 13}]},
                    "body": {"status": {"_errors": [{"code": 13}]}},
                },
            },
        ),
        (400, {}),
    ),
)
def test_validate_error_status_code_consistency(status_code, expected, error_data):
    issues = validate_error_status_code_consistency(error_data, status_code)

    assert issues.to_dict() == expected


@pytest.mark.parametrize(
    ("headers", "header_required", "expected"),
    (
        ({}, False, {}),
        (None, False, {}),
        ({}, True, {"Location": {"_errors": [{"code": 10}]}}),
        ([1, 2, 3], True, {"Location": {"_errors": [{"code": 10}]}}),
        (
            {"Location": "https://example.com/v2/Users/2819c223-7f76-453a-919d-413861904646"},
            True,
            {},
        ),
    ),
)
def test_validate_resource_location_in_header(headers, header_required, expected):
    issues = validate_resource_location_in_header(headers, header_required)

    assert issues.to_dict() == expected


def test_validate_resource_location_consistency__fails_if_no_consistency(user_data_dump):
    headers = {"Location": "https://example.com/v2/Users/2819c223-7f76-453a-919d-413861904647"}
    expected = {
        "response": {
            "body": {
                "meta": {
                    "location": {
                        "_errors": [
                            {
                                "code": 11,
                            }
                        ]
                    }
                }
            },
            "headers": {
                "Location": {
                    "_errors": [
                        {
                            "code": 11,
                        }
                    ]
                }
            },
        }
    }

    issues = validate_resource_location_consistency(user_data_dump, headers)

    assert issues.to_dict() == expected


def test_validate_resource_location_consistency__succeeds_if_consistency(user_data_dump):
    headers = {"Location": user_data_dump["meta"]["location"]}

    issues = validate_resource_location_consistency(user_data_dump, headers)

    assert issues.to_dict() == {}


@pytest.mark.parametrize(
    ("status_code", "expected"),
    ((200, {"_errors": [{"code": 16}]}), (201, {})),
)
def test_validate_status_code(status_code, expected):
    issues = validate_status_code(201, status_code)

    assert issues.to_dict() == expected


def test_validate_resource_type_consistency__fails_if_no_consistency(user_data_dump):
    user_data_dump["meta"]["resourceType"] = "Group"
    expected = {
        "meta": {
            "resourcetype": {
                "_errors": [
                    {
                        "code": 17,
                    }
                ]
            }
        }
    }

    issues = validate_resource_type_consistency(user_data_dump, USER)

    assert issues.to_dict() == expected


def test_validate_resource_type_consistency__succeeds_if_consistency(user_data_dump):
    issues = validate_resource_type_consistency(user_data_dump, USER)

    assert issues.to_dict() == {}


def test_validate_number_of_resources__fails_if_more_resources_than_total_results(list_user_data):
    list_user_data["totalResults"] = 1
    expected = {
        "totalresults": {"_errors": [{"code": 22}]},
        "resources": {"_errors": [{"code": 22}]},
    }

    issues = validate_number_of_resources(
        count=None,
        total_results=1,
        resources=list_user_data["Resources"],
    )

    assert issues.to_dict() == expected


def test_validate_number_of_resources__fails_if_less_resources_than_total_results_without_count(
    list_user_data,
):
    expected = {"resources": {"_errors": [{"code": 23}]}}

    issues = validate_number_of_resources(
        count=None,
        total_results=3,
        resources=list_user_data["Resources"],
    )

    assert issues.to_dict() == expected


def test_validate_number_of_resources__fails_if_more_resources_than_specified_count(list_user_data):
    expected = {"resources": {"_errors": [{"code": 21}]}}

    issues = validate_number_of_resources(
        count=1,
        total_results=2,
        resources=list_user_data["Resources"],
    )

    assert issues.to_dict() == expected


@pytest.mark.parametrize("count", (2, None))
def test_validate_number_of_resources__succeeds_if_correct_number_of_resources(
    count, list_user_data
):
    issues = validate_number_of_resources(count, list_user_data)

    assert issues.to_dict() == {}


def test_validate_pagination_info__fails_if_start_index_is_missing_when_pagination(list_user_data):
    expected = {
        "startindex": {"_errors": [{"code": 1}]},
    }

    issues = validate_pagination_info(
        count=2,
        total_results=2,
        resources=list_user_data["Resources"][:1],
        start_index=Missing,
        items_per_page=1,
    )

    assert issues.to_dict() == expected


def test_validate_pagination_info__fails_if_items_per_page_is_missing_when_pagination(
    list_user_data,
):
    expected = {
        "itemsperpage": {"_errors": [{"code": 1}]},
    }

    issues = validate_pagination_info(
        count=1,
        total_results=2,
        resources=list_user_data["Resources"][:1],
        start_index=1,
        items_per_page=Missing,
    )

    assert issues.to_dict() == expected


def test_validate_pagination_info__correct_data_when_pagination(list_user_data):
    count = 2
    list_user_data["startIndex"] = 1
    list_user_data["itemsPerPage"] = 1
    list_user_data["Resources"] = list_user_data["Resources"][:1]

    issues = validate_pagination_info(count, list_user_data)

    assert issues.to_dict() == {}


def test_validate_start_index_consistency__fails_if_start_index_bigger_than_requested(
    list_user_data,
):
    start_index = 1
    list_user_data["totalResults"] = 3
    list_user_data["startIndex"] = 2
    list_user_data["itemsPerPage"] = 2
    expected = {
        "startindex": {"_errors": [{"code": 24}]},
    }

    issues = validate_start_index_consistency(start_index, list_user_data)

    assert issues.to_dict() == expected


def test_validate_start_index_consistency__succeeds_if_correct_data(list_user_data):
    start_index = 1
    list_user_data["startIndex"] = 1

    issues = validate_start_index_consistency(start_index, list_user_data)

    assert issues.to_dict() == {}


def test_validate_items_per_page_consistency__fails_if_not_matching_resources(list_user_data):
    expected = {
        "itemsperpage": {"_errors": [{"code": 11}]},
        "resources": {"_errors": [{"code": 11}]},
    }

    issues = validate_items_per_page_consistency(
        resources=list_user_data["Resources"],
        items_per_page=1,
    )

    assert issues.to_dict() == expected


def test_validate_items_per_page_consistency__succeeds_if_correct_data(list_user_data):
    list_user_data["itemsPerPage"] = 2

    issues = validate_items_per_page_consistency(list_user_data)

    assert issues.to_dict() == {}


def test_dump_resources__fails_for_bad_resource_schema(list_user_data):
    list_user_data["Resources"][0]["userName"] = 123  # noqa
    list_user_data["Resources"][1]["userName"] = 123  # noqa
    expected = {
        "resources": {
            "0": {"username": {"_errors": [{"code": 31}]}},
            "1": {"username": {"_errors": [{"code": 31}]}},
        }
    }

    body, issues = dump_resources(list_user_data["Resources"], [USER, USER])

    assert issues.to_dict() == expected


def test_dump_resources__succeeds_for_correct_data(list_user_data):
    body, issues = dump_resources(list_user_data["Resources"], [USER])

    assert issues.to_dict() == {}


def test_dump_resources__resources_with_bad_type_are_reported(list_user_data):
    list_user_data["Resources"][0] = []  # noqa
    list_user_data["Resources"][1]["userName"] = 123  # noqa
    expected = {
        "resources": {
            "0": {"_errors": [{"code": 18}]},
            "1": {"username": {"_errors": [{"code": 31}]}},
        }
    }

    body, issues = dump_resources(list_user_data["Resources"], [USER, USER])

    assert issues.to_dict() == expected


@pytest.mark.parametrize(
    ("query_string", "expected"),
    (
        ({"sortBy": "userName"}, {}),
        ({"sortBy": "bad^attr"}, {"_errors": [{"code": 111}]}),
    ),
)
def test_validate_request_sorting(query_string, expected):
    _, issues = parse_request_sorting(query_string)

    assert issues.to_dict() == expected


@pytest.mark.parametrize(
    ("query_string", "expected"),
    (
        ({"attributes": "userName"}, {}),
        ({"excludeAttributes": "userName"}, {}),
        (
            {"attributes": "userName", "excludeAttributes": "name"},
            {
                "attributes": {"_errors": [{"code": 30}]},
                "excludeAttributes": {"_errors": [{"code": 30}]},
            },
        ),
        ({}, {}),
        (
            {"attributes": ["userName", "bad^attr"]},
            {"attributes": {"bad^attr": {"_errors": [{"code": 111}]}}},
        ),
        (
            {"excludeAttributes": ["userName", "bad^attr"]},
            {"excludeAttributes": {"bad^attr": {"_errors": [{"code": 111}]}}},
        ),
    ),
)
def test_validate_requested_attributes(query_string, expected):
    _, issues = parse_requested_attributes(query_string)

    assert issues.to_dict() == expected


@pytest.mark.parametrize(
    ("query_string", "expected"),
    (
        ({"filter": 'userName eq "bjensen"'}, {}),
        ({}, {}),
        ({"filter": "username hey 10"}, {"_errors": [{"code": 105}]}),
    ),
)
def test_validate_request_filtering(query_string, expected):
    _, issues = parse_request_filtering(query_string)

    assert issues.to_dict() == expected


@pytest.mark.parametrize(
    "filter_exp",
    (
        'emails[value eq "sven@example.com"]',
        'emails eq "sven@example.com"',
        'name.familyName eq "Sven"',
    ),
)
def test_validate_resources_filtered(filter_exp, list_user_data):
    filter_, _ = Filter.parse(filter_exp)
    expected = {
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

    issues = validate_resources_filtered(list_user_data["Resources"], filter_, [USER], False)

    assert issues.to_dict() == expected


def test_validate_resources_filtered__case_sensitivity_matters(list_user_data):
    filter_, _ = Filter.parse('meta.resourcetype eq "user"')  # "user", not "User"
    expected = {
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

    issues = validate_resources_filtered(list_user_data["Resources"], filter_, [USER, USER], False)

    assert issues.to_dict() == expected


def test_validate_resources_filtered__infers_correct_schema_from_data(list_user_data):
    filter_, _ = Filter.parse('meta.resourcetype eq "user"')
    # should figure out 'User' schema, for which 'meta.resourcetype' is case-sensitive
    expected = {
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

    issues = validate_resources_filtered(list_user_data["Resources"], filter_, [USER, ERROR], False)

    assert issues.to_dict() == expected


@pytest.mark.parametrize(
    "attr_name",
    (
        "manager.displayName",
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:manager.displayName",
    ),
)
def test_validate_resources_filtered__fields_from_schema_extensions_are_checked_by_filter(
    attr_name,
    list_user_data,
):
    filter_, _ = Filter.parse(f'{attr_name} eq "John Smith"')
    expected = {
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

    issues = validate_resources_filtered(list_user_data["Resources"], filter_, [USER], False)

    assert issues.to_dict() == expected


@pytest.mark.parametrize(
    "sorter",
    (
        Sorter(AttributeName(attr="name", sub_attr="familyName"), asc=False),
        Sorter(AttributeName(attr="manager", sub_attr="displayName"), asc=False),
        Sorter(
            AttributeName(
                schema="urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
                attr="manager",
                sub_attr="displayName",
            ),
            asc=False,
        ),
    ),
)
def test_validate_resources_sorted__not_sorted(sorter, list_user_data):
    expected = {"resources": {"_errors": [{"code": 26}]}}

    issues = validate_resources_sorted(sorter, list_user_data["Resources"], [USER, USER])

    assert issues.to_dict() == expected


def test_validate_resources_attribute_presence__fails_if_requested_attribute_not_excluded(
    list_user_data,
):
    checker = AttributePresenceChecker(attr_names=[AttributeName(attr="name")], include=False)
    expected = {
        "resources": {
            "0": {
                "name": {
                    "_errors": [
                        {
                            "code": 19,
                        }
                    ]
                }
            },
            "1": {
                "name": {
                    "_errors": [
                        {
                            "code": 19,
                        }
                    ]
                }
            },
        }
    }

    issues = validate_resources_attribute_presence(
        checker, list_user_data["Resources"], [USER, USER]
    )

    assert issues.to_dict() == expected


@pytest.mark.parametrize("invalid_resource", ([1, 2, 3], {1: 2, 3: 4}))
def test_validate_resources_attribute_presence__invalid_resources_are_skipped(
    invalid_resource, list_user_data
):
    checker = AttributePresenceChecker(attr_names=[AttributeName(attr="name")], include=False)
    list_user_data["Resources"][0] = invalid_resource  # noqa
    expected = {
        "resources": {
            "1": {
                "name": {
                    "_errors": [
                        {
                            "code": 19,
                        }
                    ]
                }
            }
        }
    }

    issues = validate_resources_attribute_presence(
        checker, list_user_data["Resources"], [USER, USER]
    )

    assert issues.to_dict() == expected


def test_validate_resources_schemas_field__bad_schemas_is_discovered(list_user_data):
    list_user_data["Resources"][1]["schemas"].append("bad:user:schema")
    expected = {"resources": {"1": {"schemas": {"_errors": [{"code": 27}]}}}}

    issues = validate_resources_schemas_field(list_user_data["Resources"], [USER, USER])

    assert issues.to_dict() == expected


@pytest.mark.parametrize(
    ("data", "expected"),
    (
        (
            {
                "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
                "userName": "bjensen",
            },
            USER,
        ),
        (
            # only "schemas" attribute is used
            {
                "urn:ietf:params:scim:schemas:core:2.0:User:userName": "bjensen",
            },
            None,
        ),
        (
            {
                "userName": "bjensen",
            },
            None,
        ),
        (
            # extensions are ignored
            {
                "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
                    "employeeNumber": "2",
                }
            },
            None,
        ),
    ),
)
def test_infer_schema_from_data(data, expected):
    actual = infer_schema_from_data(data, [USER])

    assert actual == expected


def test_correct_error_response_passes_validation(error_data):
    validator = Error()

    data, issues = validator.dump_response(status_code=400, body=error_data)

    assert issues.to_dict() == {}
    assert data.body is not None


def test_correct_resource_object_get_request_passes_validation():
    validator = ResourceObjectGET(USER)

    data, issues = validator.parse_request(
        body=None, headers=None, query_string={"attributes": "name.familyName"}
    )

    assert issues.to_dict() == {}
    assert data.body is None
    assert data.headers is None
    assert data.query_string["presence_checker"].attr_names == [
        AttributeName(attr="name", sub_attr="familyName")
    ]
    assert data.query_string["presence_checker"].include is True


def test_correct_resource_object_get_response_passes_validation(user_data_dump):
    validator = ResourceObjectGET(USER)
    user_data_dump.pop("name")

    data, issues = validator.dump_response(
        status_code=200,
        body=user_data_dump,
        headers={"Location": user_data_dump["meta"]["location"]},
        presence_checker=AttributePresenceChecker(
            attr_names=[AttributeName(attr="name")], include=False
        ),
    )

    assert issues.to_dict() == {}
    assert data.body is not None
    assert data.headers is not None


def test_correct_resource_type_post_request_passes_validation(user_data_parse):
    validator = ResourceTypePOST(USER)
    user_data_parse.pop("id")
    user_data_parse.pop("meta")

    data, issues = validator.parse_request(
        body=user_data_parse,
        query_string={"attributes": "name.familyName"},
    )

    assert issues.to_dict() == {}
    assert data.body is not None
    assert data.query_string["presence_checker"].attr_names == [
        AttributeName(attr="name", sub_attr="familyName")
    ]
    assert data.query_string["presence_checker"].include is True


def test_correct_resource_object_put_request_passes_validation(user_data_parse):
    validator = ResourceObjectPUT(USER)
    user_data_parse.pop("meta")

    data, issues = validator.parse_request(
        body=user_data_parse,
        query_string={"attributes": "name.familyName"},
    )

    assert issues.to_dict() == {}
    assert data.body is not None
    assert data.query_string["presence_checker"].attr_names == [
        AttributeName(attr="name", sub_attr="familyName")
    ]
    assert data.query_string["presence_checker"].include is True


def test_resource_object_put_request__fails_when_missing_required_field(user_data_parse):
    validator = ResourceObjectPUT(USER)
    user_data_parse.pop("id")  # required
    user_data_parse.pop("meta")
    expected_issues = {"request": {"body": {"id": {"_errors": [{"code": 15}]}}}}

    data, issues = validator.parse_request(body=user_data_parse)

    assert issues.to_dict() == expected_issues
    assert data.body is None


def test_resource_object_put_request__not_required_read_only_fields_are_ignored(user_data_parse):
    # data contains 'meta'
    validator = ResourceObjectPUT(USER)

    data, issues = validator.parse_request(body=user_data_parse)

    assert issues.to_dict() == {}
    assert "meta" not in data.body


def test_correct_resource_object_put_response_passes_validation(user_data_dump):
    validator = ResourceObjectPUT(USER)

    data, issues = validator.dump_response(
        status_code=200,
        body=user_data_dump,
        headers={"Location": user_data_dump["meta"]["location"]},
    )

    assert issues.to_dict() == {}
    assert data.body is not None
    assert data.headers is not None


def test_correct_resource_type_post_response_passes_validation(user_data_dump):
    validator = ResourceTypePOST(USER)

    data, issues = validator.dump_response(
        status_code=201,
        body=user_data_dump,
        headers={"Location": user_data_dump["meta"]["location"]},
    )

    assert issues.to_dict() == {}
    assert data.body is not None
    assert data.headers is not None


@pytest.mark.parametrize(
    "validator", (ResourceTypeGET(USER), ServerRootResourceGET([USER]), SearchRequestPOST([USER]))
)
def test_correct_list_response_passes_validation(validator, list_user_data):
    list_user_data["Resources"][0].pop("name")
    list_user_data["Resources"][1].pop("name")

    data, issues = validator.dump_response(
        status_code=200,
        body=list_user_data,
        start_index=1,
        count=2,
        filter_=Filter(Present(AttributeName(attr="username"))),
        sorter=Sorter(AttributeName(attr="userName"), True),
        presence_checker=AttributePresenceChecker(
            attr_names=[AttributeName(attr="name")], include=False
        ),
    )

    assert issues.to_dict() == {}
    assert data.body is not None


@pytest.mark.parametrize(
    "validator", (ResourceTypeGET(USER), ServerRootResourceGET([USER]), SearchRequestPOST([USER]))
)
def test_attributes_existence_is_validated_in_list_response(validator):
    expected_issues = {
        "response": {
            "body": {
                "schemas": {
                    "_errors": [{"code": 15}],
                },
                "totalresults": {"_errors": [{"code": 15}]},
            }
        }
    }

    data, issues = validator.dump_response(
        status_code=200,
        body={},
    )

    assert issues.to_dict() == expected_issues
    assert data.body is None


@pytest.mark.parametrize(
    "validator", (ResourceTypeGET(USER), ServerRootResourceGET([USER]), SearchRequestPOST([USER]))
)
def test_resources_in_list_response_must_be_list(validator):
    expected_issues = {
        "response": {
            "body": {
                "resources": {
                    "_errors": [{"code": 18}],
                },
            }
        }
    }

    data, issues = validator.dump_response(
        status_code=200,
        body={
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:listresponse"],
            "totalResults": 1,
            "Resources": {},
        },
    )

    assert issues.to_dict() == expected_issues
    assert data.body is None


@pytest.mark.parametrize(
    "validator", (ResourceTypeGET(USER), ServerRootResourceGET([USER]), SearchRequestPOST([USER]))
)
def test_attributes_presence_is_validated_in_resources_in_list_response(validator):
    expected_issues = {
        "response": {
            "body": {
                "resources": {
                    "0": {
                        "id": {"_errors": [{"code": 15}]},
                        "schemas": {"_errors": [{"code": 15}]},
                        "username": {"_errors": [{"code": 15}]},
                    }
                },
            }
        }
    }

    data, issues = validator.dump_response(
        status_code=200,
        body={
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:listresponse"],
            "totalResults": 1,
            "Resources": [{}],
        },
    )

    assert issues.to_dict() == expected_issues
    assert data.body is None


def test_correct_search_request_passes_validation():
    validator = SearchRequestPOST([USER])

    data, issues = validator.parse_request(
        body={
            "attributes": ["userName", "name"],
            "filter": 'userName eq "bjensen"',
            "sortBy": "name.familyName",
            "sortOrder": "descending",
            "startIndex": 2,
            "count": 10,
        }
    )

    assert issues.to_dict() == {}
    assert data.body["presence_checker"].attr_names == [
        AttributeName(attr="userName"),
        AttributeName(attr="name"),
    ]
    assert data.body["presence_checker"].include is True
    assert data.body["filter"].to_dict() == {
        "op": "eq",
        "attr_name": "username",
        "value": "bjensen",
    }
    assert data.body["sorter"].attr_name == AttributeName(attr="name", sub_attr="familyName")
    assert data.body["sorter"].asc is False
    assert data.body["startindex"] == 2
    assert data.body["count"] == 10


def test_search_request_validation_fails_if_attributes_and_exclude_attributes_provided():
    validator = SearchRequestPOST([USER])
    expected_issues = {
        "request": {
            "body": {
                "attributes": {"_errors": [{"code": 30}]},
                "excludeAttributes": {"_errors": [{"code": 30}]},
            }
        }
    }

    data, issues = validator.parse_request(
        body={
            "attributes": ["userName"],
            "excludeAttributes": ["name"],
        }
    )

    assert issues.to_dict() == expected_issues


def test_filter_unknown_fields__complex_multivalued_attribute_value_is_preserved():
    data = {
        "emails": [
            {
                "type": "work",
                "value": "work@example.com",
                "primary": True,
                "redundant": 42,
            },
            {
                "type": "home",
                "value": "home@example.com",
                "mess": True,
            },
        ]
    }

    expected_data = {
        "emails": [
            {
                "type": "work",
                "value": "work@example.com",
                "primary": True,
            },
            {
                "type": "home",
                "value": "home@example.com",
            },
        ]
    }

    data_filtered = filter_unknown_fields(schema=USER, data=data)

    assert data_filtered == expected_data


@pytest.mark.parametrize(
    ("path", "expected_issues"),
    (
        (
            PatchPath(
                attr_name=AttributeName(attr="nonexisting"),
                complex_filter=None,
                complex_filter_attr_name=None,
            ),
            {"_errors": [{"code": 303}]},
        ),
        (
            PatchPath(
                attr_name=AttributeName(attr="non", sub_attr="existing"),
                complex_filter=None,
                complex_filter_attr_name=None,
            ),
            {"_errors": [{"code": 303}]},
        ),
        (
            PatchPath(
                attr_name=AttributeName(attr="emails"),
                complex_filter=Equal(
                    attr_name=AttributeName(attr="emails", sub_attr="nonexisting"), value="whatever"
                ),
                complex_filter_attr_name=None,
            ),
            {"_errors": [{"code": 303}]},
        ),
        (
            PatchPath(
                attr_name=AttributeName(attr="emails"),
                complex_filter=Equal(
                    attr_name=AttributeName(attr="emails", sub_attr="type"), value="whatever"
                ),
                complex_filter_attr_name=AttributeName(attr="emails", sub_attr="nonexisting"),
            ),
            {"_errors": [{"code": 303}]},
        ),
        (
            PatchPath(
                attr_name=AttributeName(attr="emails"),
                complex_filter=Equal(
                    attr_name=AttributeName(attr="emails", sub_attr="type"), value="work"
                ),
                complex_filter_attr_name=AttributeName(attr="emails", sub_attr="value"),
            ),
            {},
        ),
        (
            PatchPath(
                attr_name=AttributeName(attr="emails"),
                complex_filter=Equal(
                    attr_name=AttributeName(attr="emails", sub_attr="type"), value="work"
                ),
                complex_filter_attr_name=None,
            ),
            {},
        ),
        (
            PatchPath(
                attr_name=AttributeName(attr="name", sub_attr="familyName"),
                complex_filter=None,
                complex_filter_attr_name=None,
            ),
            {},
        ),
        (
            PatchPath(
                attr_name=AttributeName(attr="name"),
                complex_filter=None,
                complex_filter_attr_name=None,
            ),
            {},
        ),
    ),
)
def test_validate_operation_path(path, expected_issues):
    issues = validate_operation_path(schema=USER, path=path)

    assert issues.to_dict() == expected_issues


def test_parse_patch_operations__fails_if_path_with_unknown_attribute():
    operations = [
        {
            "op": "add",
            "path": PatchPath(
                attr_name=AttributeName(attr="unknown"),
                complex_filter=None,
                complex_filter_attr_name=None,
            ),
        },
        {
            "op": "add",
            "path": PatchPath(
                attr_name=AttributeName(attr="emails"),
                complex_filter=Equal(
                    attr_name=AttributeName(attr="emails", sub_attr="unknown"),
                    value="whatever",
                ),
                complex_filter_attr_name=None,
            ),
        },
        {
            "op": "add",
            "path": PatchPath(
                attr_name=AttributeName(attr="emails"),
                complex_filter=Equal(
                    attr_name=AttributeName(attr="emails", sub_attr="type"),
                    value="work",
                ),
                complex_filter_attr_name=AttributeName(attr="emails", sub_attr="unknown"),
            ),
        },
    ]
    expected_issues = {
        "0": {"path": {"_errors": [{"code": 303}]}},
        "1": {"path": {"_errors": [{"code": 303}]}},
        "2": {"path": {"_errors": [{"code": 303}]}},
    }

    parsed, issues = parse_operations(schema=USER, data=operations)

    assert parsed is None
    assert issues.to_dict() == expected_issues


def test_parse_add_operation_without_path__succeeds_for_correct_data():
    operations = [
        {
            "op": "add",
            "value": {
                "ignore^me": 42,
                "name": {
                    "formatted": "Ms. Barbara J Jensen III",
                    "ignore^me": 42,
                },
                "userName": "bjensen",
                "emails": [{"value": "bjensen@example.com", "type": "work"}],
                "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
                    "ignore^me": 42,
                    "department": "Tour Operations",
                    "manager": {
                        "displayName": "Jan Kowalski",
                    },
                },
            },
        }
    ]
    expected_value = {
        "name": {
            "formatted": "Ms. Barbara J Jensen III",
        },
        "username": "bjensen",
        "emails": [{"value": "bjensen@example.com", "type": "work"}],
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:user": {
            "department": "Tour Operations",
            "manager": {
                "displayname": "Jan Kowalski",
            },
        },
    }

    parsed, issues = parse_operations(schema=USER, data=operations)

    assert not issues
    assert parsed[0]["value"] == expected_value


def test_parse_add_operation_without_path__fails_for_incorrect_data():
    operations = [
        {
            "op": "add",
            "value": {
                "name": {
                    "formatted": 123,
                },
                "userName": 123,
                "emails": [{"value": "bjensen@example.com", "type": 123}],
                "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
                    "department": 123,
                    "manager": {
                        "displayName": 123,
                    },
                },
            },
        }
    ]
    expected_issues = {
        "0": {
            "value": {
                "name": {"formatted": {"_errors": [{"code": 2}]}},
                "username": {"_errors": [{"code": 2}]},
                "emails": {"0": {"type": {"_errors": [{"code": 2}]}}},
                "urn:ietf:params:scim:schemas:extension:enterprise:2.0:user": {
                    "department": {"_errors": [{"code": 2}]},
                    "manager": {"displayname": {"_errors": [{"code": 2}]}},
                },
            }
        }
    }

    parsed, issues = parse_operations(schema=USER, data=operations)

    assert parsed is None
    assert issues.to_dict() == expected_issues


def test_parse_add_operation_without_path__fails_if_attribute_is_readonly():
    operations = [
        {
            "op": "add",
            "value": {"meta": {"resourceType": "Users"}},
        }
    ]
    expected_issues = {"0": {"value": {"meta": {"_errors": [{"code": 304}]}}}}

    parsed, issues = parse_operations(schema=USER, data=operations)

    assert parsed is None
    assert issues.to_dict() == expected_issues


@pytest.mark.parametrize(
    ("path", "value", "expected_value_issues"),
    (
        (
            PatchPath(
                attr_name=AttributeName(attr="userName"),
                complex_filter=None,
                complex_filter_attr_name=None,
            ),
            123,
            {"_errors": [{"code": 2}]},
        ),
        (
            PatchPath(
                attr_name=AttributeName(attr="name", sub_attr="formatted"),
                complex_filter=None,
                complex_filter_attr_name=None,
            ),
            123,
            {"_errors": [{"code": 2}]},
        ),
        (
            PatchPath(
                attr_name=AttributeName(attr="name"),
                complex_filter=None,
                complex_filter_attr_name=None,
            ),
            {"formatted": 123, "familyName": 123},
            {"formatted": {"_errors": [{"code": 2}]}, "familyname": {"_errors": [{"code": 2}]}},
        ),
        (
            PatchPath(
                attr_name=AttributeName(attr="name"),
                complex_filter=None,
                complex_filter_attr_name=None,
            ),
            123,
            {"_errors": [{"code": 2}]},
        ),
        (
            PatchPath(
                attr_name=AttributeName(attr="emails"),
                complex_filter=None,
                complex_filter_attr_name=None,
            ),
            123,
            {"_errors": [{"code": 18}]},
        ),
        (
            PatchPath(
                attr_name=AttributeName(attr="emails"),
                complex_filter=None,
                complex_filter_attr_name=None,
            ),
            [{"type": 123, "value": 123}],
            {"0": {"type": {"_errors": [{"code": 2}]}, "value": {"_errors": [{"code": 2}]}}},
        ),
        (
            PatchPath(
                attr_name=AttributeName(attr="emails"),
                complex_filter=None,
                complex_filter_attr_name=None,
            ),
            {"type": "home", "value": "home@example.com"},
            {"_errors": [{"code": 18}]},
        ),
        (
            PatchPath(
                attr_name=AttributeName(attr="emails"),
                complex_filter=Equal(
                    attr_name=AttributeName(attr="emails", sub_attr="type"),
                    value="work",
                ),
                complex_filter_attr_name=AttributeName(attr="emails", sub_attr="value"),
            ),
            123,
            {"_errors": [{"code": 2}]},
        ),
    ),
)
def test_parse_add_operation__fails_for_incorrect_data(path, value, expected_value_issues):
    operations = [
        {
            "op": "add",
            "path": path,
            "value": value,
        }
    ]
    expected_issues = {"0": {"value": expected_value_issues}}

    parsed, issues = parse_operations(schema=USER, data=operations)

    assert parsed is None
    assert issues.to_dict() == expected_issues


@pytest.mark.parametrize(
    ("path", "value", "expected_value"),
    (
        (
            PatchPath(
                attr_name=AttributeName(attr="userName"),
                complex_filter=None,
                complex_filter_attr_name=None,
            ),
            "bjensen",
            "bjensen",
        ),
        (
            PatchPath(
                attr_name=AttributeName(attr="name", sub_attr="formatted"),
                complex_filter=None,
                complex_filter_attr_name=None,
            ),
            "Jan Kowalski",
            "Jan Kowalski",
        ),
        (
            PatchPath(
                attr_name=AttributeName(attr="name"),
                complex_filter=None,
                complex_filter_attr_name=None,
            ),
            {"formatted": "Jan Kowalski", "familyName": "Kowalski"},
            {"formatted": "Jan Kowalski", "familyName": "Kowalski"},
        ),
        (
            PatchPath(
                attr_name=AttributeName(attr="emails"),
                complex_filter=None,
                complex_filter_attr_name=None,
            ),
            [{"type": "work", "value": "work@example.com"}],
            [{"type": "work", "value": "work@example.com"}],
        ),
        (
            PatchPath(
                attr_name=AttributeName(attr="emails"),
                complex_filter=Equal(
                    attr_name=AttributeName(attr="emails", sub_attr="type"),
                    value="work",
                ),
                complex_filter_attr_name=AttributeName(attr="emails", sub_attr="value"),
            ),
            "work@example.com",
            "work@example.com",
        ),
    ),
)
def test_parse_add_operation__succeeds_on_correct_data(path, value, expected_value):
    operations = [
        {
            "op": "add",
            "path": path,
            "value": value,
        }
    ]

    parsed, issues = parse_operations(schema=USER, data=operations)

    assert not issues
    assert value == expected_value


@pytest.mark.parametrize(
    ("path", "value"),
    (
        (
            PatchPath(
                attr_name=AttributeName(attr="id"),
                complex_filter=None,
                complex_filter_attr_name=None,
            ),
            "123",
        ),
        (
            PatchPath(
                attr_name=AttributeName(attr="manager", sub_attr="displayName"),
                complex_filter=None,
                complex_filter_attr_name=None,
            ),
            "The Grok",
        ),
        (
            PatchPath(
                attr_name=AttributeName(attr="meta"),
                complex_filter=None,
                complex_filter_attr_name=None,
            ),
            {"resourceType": "Users"},
        ),
        (
            PatchPath(
                attr_name=AttributeName(attr="groups"),
                complex_filter=None,
                complex_filter_attr_name=None,
            ),
            [{"type": "direct", "value": "admins"}],
        ),
        (
            PatchPath(
                attr_name=AttributeName(attr="groups"),
                complex_filter=Equal(
                    attr_name=AttributeName(attr="groups", sub_attr="type"),
                    value="direct",
                ),
                complex_filter_attr_name=AttributeName(attr="groups", sub_attr="value"),
            ),
            "admins",
        ),
    ),
)
def test_parse_add_operation__fails_if_attribute_is_readonly(path, value):
    operations = [
        {
            "op": "add",
            "path": path,
            "value": value,
        }
    ]
    expected_issues = {"0": {"value": {"_errors": [{"code": 304}]}}}

    parsed, issues = parse_operations(schema=USER, data=operations)

    assert parsed is None
    assert issues.to_dict() == expected_issues
