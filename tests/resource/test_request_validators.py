from copy import deepcopy

import pytest

from src.attributes_presence import AttributePresenceChecker
from src.data.container import AttrRep, Missing, SCIMDataContainer
from src.data.operator import Present
from src.data.path import PatchPath
from src.filter import Filter
from src.resource.request_validators import (
    BulkOperations,
    Error,
    ResourceObjectDELETE,
    ResourceObjectGET,
    ResourceObjectPATCH,
    ResourceObjectPUT,
    ResourceTypeGET,
    ResourceTypePOST,
    SearchRequestPOST,
    ServerRootResourceGET,
    parse_request_filtering,
    parse_request_sorting,
    parse_requested_attributes,
    validate_error_status_code,
    validate_error_status_code_consistency,
    validate_number_of_resources,
    validate_pagination_info,
    validate_resource_location_consistency,
    validate_resource_location_in_header,
    validate_resources_attributes_presence,
    validate_resources_filtered,
    validate_resources_sorted,
    validate_start_index_consistency,
    validate_status_code,
)
from src.resource.schemas import list_response, user
from src.sorter import Sorter
from tests.conftest import SchemaForTests


@pytest.mark.parametrize(
    ("status_code", "expected"),
    (
        (199, {"status": {"_errors": [{"code": 12}]}}),
        (600, {"status": {"_errors": [{"code": 12}]}}),
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
                "status": {"_errors": [{"code": 13}]},
                "body": {"status": {"_errors": [{"code": 13}]}},
            },
        ),
        (400, {}),
    ),
)
def test_validate_error_status_code_consistency(status_code, expected):
    issues = validate_error_status_code_consistency("status", "400", status_code)

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
    headers_location = "https://example.com/v2/Users/2819c223-7f76-453a-919d-413861904647"
    expected_issues = {
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

    issues = validate_resource_location_consistency(
        user_data_dump["meta"]["location"],
        headers_location,
    )

    assert issues.to_dict() == expected_issues


def test_validate_resource_location_consistency__succeeds_if_consistency(user_data_dump):
    issues = validate_resource_location_consistency(
        user_data_dump["meta"]["location"],
        user_data_dump["meta"]["location"],
    )

    assert issues.to_dict() == {}


@pytest.mark.parametrize(
    ("status_code", "expected"),
    ((200, {"_errors": [{"code": 16}]}), (201, {})),
)
def test_validate_status_code(status_code, expected):
    issues = validate_status_code(201, status_code)

    assert issues.to_dict() == expected


def test_validate_number_of_resources__fails_if_more_resources_than_total_results(list_user_data):
    list_user_data["totalResults"] = 1
    expected = {"_errors": [{"code": 22}]}

    issues = validate_number_of_resources(
        count=None,
        total_results=1,
        resources=[SCIMDataContainer(r) for r in list_user_data["Resources"]],
    )

    assert issues.to_dict() == expected


def test_validate_number_of_resources__fails_if_less_resources_than_total_results_without_count(
    list_user_data,
):
    expected = {"_errors": [{"code": 23}]}

    issues = validate_number_of_resources(
        count=None,
        total_results=3,
        resources=[SCIMDataContainer(r) for r in list_user_data["Resources"]],
    )

    assert issues.to_dict() == expected


def test_validate_number_of_resources__fails_if_more_resources_than_specified_count(list_user_data):
    expected = {"_errors": [{"code": 21}]}

    issues = validate_number_of_resources(
        count=1,
        total_results=2,
        resources=[SCIMDataContainer(r) for r in list_user_data["Resources"]],
    )

    assert issues.to_dict() == expected


@pytest.mark.parametrize("count", (2, None))
def test_validate_number_of_resources__succeeds_if_correct_number_of_resources(
    count, list_user_data
):
    issues = validate_number_of_resources(
        count=count,
        total_results=2,
        resources=[SCIMDataContainer(r) for r in list_user_data["Resources"]],
    )

    assert issues.to_dict() == {}


def test_validate_pagination_info__fails_if_start_index_is_missing_when_pagination(list_user_data):
    expected = {
        "startIndex": {"_errors": [{"code": 15}]},
    }

    issues = validate_pagination_info(
        schema=list_response.ListResponse([user.User()]),
        count=2,
        total_results=2,
        resources=[SCIMDataContainer(list_user_data["Resources"][0])],
        start_index=Missing,
        items_per_page=1,
    )

    assert issues.to_dict() == expected


def test_validate_pagination_info__fails_if_items_per_page_is_missing_when_pagination(
    list_user_data,
):
    expected = {
        "itemsPerPage": {"_errors": [{"code": 15}]},
    }

    issues = validate_pagination_info(
        schema=list_response.ListResponse([user.User()]),
        count=1,
        total_results=2,
        resources=[SCIMDataContainer(list_user_data["Resources"][0])],
        start_index=1,
        items_per_page=Missing,
    )

    assert issues.to_dict() == expected


def test_validate_pagination_info__correct_data_when_pagination(list_user_data):
    issues = validate_pagination_info(
        schema=list_response.ListResponse([user.User()]),
        count=2,
        total_results=2,
        resources=[SCIMDataContainer(list_user_data["Resources"][0])],
        start_index=1,
        items_per_page=1,
    )

    assert issues.to_dict() == {}


def test_validate_start_index_consistency__fails_if_start_index_bigger_than_requested():
    expected = {"_errors": [{"code": 24}]}

    issues = validate_start_index_consistency(start_index=1, start_index_body=2)

    assert issues.to_dict() == expected


def test_validate_start_index_consistency__succeeds_if_correct_data():
    issues = validate_start_index_consistency(start_index=1, start_index_body=1)

    assert issues.to_dict() == {}


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
        "0": {
            "_errors": [
                {
                    "code": 25,
                }
            ]
        }
    }

    issues = validate_resources_filtered(
        resources=[SCIMDataContainer(r) for r in list_user_data["Resources"]],
        filter_=filter_,
        resource_schemas=[user.User(), user.User()],
        strict=False,
    )

    assert issues.to_dict() == expected


def test_validate_resources_filtered__case_sensitivity_matters(list_user_data):
    filter_, _ = Filter.parse('meta.resourcetype eq "user"')  # "user", not "User"
    expected = {
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

    issues = validate_resources_filtered(
        resources=[SCIMDataContainer(r) for r in list_user_data["Resources"]],
        filter_=filter_,
        resource_schemas=[user.User(), user.User()],
        strict=False,
    )

    assert issues.to_dict() == expected


def test_validate_resources_filtered__fields_from_schema_extensions_are_checked_by_filter(
    list_user_data,
):
    filter_, _ = Filter.parse(
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:manager.displayName "
        'eq "John Smith"'
    )
    expected = {
        "0": {
            "_errors": [
                {
                    "code": 25,
                }
            ]
        },
    }

    issues = validate_resources_filtered(
        resources=[SCIMDataContainer(r) for r in list_user_data["Resources"]],
        filter_=filter_,
        resource_schemas=[user.User(), user.User()],
        strict=False,
    )

    assert issues.to_dict() == expected


@pytest.mark.parametrize(
    "sorter",
    (
        Sorter(AttrRep(attr="name", sub_attr="familyName"), asc=False),
        Sorter(
            AttrRep(
                schema="urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
                attr="manager",
                sub_attr="displayName",
            ),
            asc=False,
        ),
    ),
)
def test_validate_resources_sorted__not_sorted(sorter, list_user_data):
    expected = {"_errors": [{"code": 26}]}

    issues = validate_resources_sorted(
        sorter=sorter,
        resources=[SCIMDataContainer(r) for r in list_user_data["Resources"]],
        resource_schemas=[user.User(), user.User()],
    )

    assert issues.to_dict() == expected


def test_validate_resources_attribute_presence__fails_if_requested_attribute_not_excluded(
    list_user_data,
):
    checker = AttributePresenceChecker(attr_reps=[AttrRep(attr="name")], include=False)
    expected = {
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

    issues = validate_resources_attributes_presence(
        presence_checker=checker,
        resources=[SCIMDataContainer(r) for r in list_user_data["Resources"]],
        resource_schemas=[user.User(), user.User()],
    )

    assert issues.to_dict() == expected


def test_correct_error_response_passes_validation(error_data):
    validator = Error()

    data, issues = validator.dump_response(status_code=400, body=error_data)

    assert issues.to_dict() == {}
    assert data.body is not None


def test_correct_resource_object_get_request_passes_validation():
    validator = ResourceObjectGET(user.User())

    data, issues = validator.parse_request(
        body=None, headers=None, query_string={"attributes": "name.familyName"}
    )

    assert issues.to_dict() == {}
    assert data.body is None
    assert data.headers is None
    assert data.query_string["presence_checker"].attr_reps == [
        AttrRep(attr="name", sub_attr="familyName")
    ]
    assert data.query_string["presence_checker"].include is True


def test_correct_resource_object_get_response_passes_validation(user_data_dump):
    validator = ResourceObjectGET(user.User())
    user_data_dump.pop("name")

    data, issues = validator.dump_response(
        status_code=200,
        body=user_data_dump,
        headers={"Location": user_data_dump["meta"]["location"]},
        presence_checker=AttributePresenceChecker(attr_reps=[AttrRep(attr="name")], include=False),
    )

    assert issues.to_dict() == {}
    assert data.body is not None
    assert data.headers is not None


def test_correct_resource_type_post_request_passes_validation(user_data_parse):
    validator = ResourceTypePOST(user.User())

    data, issues = validator.parse_request(
        body=user_data_parse,
        query_string={"attributes": "name.familyName"},
    )

    assert issues.to_dict() == {}
    assert data.body is not None
    assert data.query_string["presence_checker"].attr_reps == [
        AttrRep(attr="name", sub_attr="familyName")
    ]
    assert data.query_string["presence_checker"].include is True


def test_resource_type_post_request_parsing_fails_for_incorrect_data_passes_validation(
    user_data_parse,
):
    validator = ResourceTypePOST(user.User())
    user_data_parse["userName"] = 123
    expected_issues = {"body": {"userName": {"_errors": [{"code": 2}]}}}

    data, issues = validator.parse_request(
        body=user_data_parse,
    )

    assert issues.to_dict() == expected_issues
    assert data.body is None


def test_correct_resource_object_put_request_passes_validation(user_data_parse):
    validator = ResourceObjectPUT(user.User())
    user_data_parse["id"] = "anything"

    data, issues = validator.parse_request(
        body=user_data_parse,
        query_string={"attributes": "name.familyName"},
    )

    assert issues.to_dict() == {}
    assert data.body is not None
    assert data.query_string["presence_checker"].attr_reps == [
        AttrRep(attr="name", sub_attr="familyName")
    ]
    assert data.query_string["presence_checker"].include is True


def test_resource_object_put_request__fails_when_missing_required_field(user_data_parse):
    validator = ResourceObjectPUT(user.User())
    # user_data_parse misses 'id' and 'meta'
    expected_issues = {"body": {"id": {"_errors": [{"code": 15}]}}}

    data, issues = validator.parse_request(body=user_data_parse)

    assert issues.to_dict() == expected_issues
    assert data.body is None


def test_resource_object_put_request__not_required_read_only_fields_are_ignored(user_data_parse):
    user_data_parse["id"] = "2819c223-7f76-453a-919d-413861904646"
    user_data_parse["meta"] = {
        "resourceType": "User",
        "created": "2010-01-23T04:56:22Z",
        "lastModified": "2011-05-13T04:42:34Z",
        "version": r'W\/"3694e05e9dff591"',
        "location": "https://example.com/v2/Users/2819c223-7f76-453a-919d-413861904646",
    }
    validator = ResourceObjectPUT(user.User())

    data, issues = validator.parse_request(body=user_data_parse)

    assert issues.to_dict() == {}
    assert "meta" not in data.body.to_dict()


def test_correct_resource_object_put_response_passes_validation(user_data_dump):
    validator = ResourceObjectPUT(user.User())

    data, issues = validator.dump_response(
        status_code=200,
        body=user_data_dump,
        headers={"Location": user_data_dump["meta"]["location"]},
    )

    assert issues.to_dict() == {}
    assert data.body is not None
    assert data.headers is not None


def test_correct_resource_type_post_response_passes_validation(user_data_dump):
    validator = ResourceTypePOST(user.User())

    data, issues = validator.dump_response(
        status_code=201,
        body=user_data_dump,
        headers={"Location": user_data_dump["meta"]["location"]},
    )

    assert issues.to_dict() == {}
    assert data.body is not None
    assert data.headers is not None


@pytest.mark.parametrize(
    "validator",
    (
        ResourceTypeGET(user.User()),
        ServerRootResourceGET([user.User()]),
        SearchRequestPOST([user.User()]),
    ),
)
def test_correct_list_response_passes_validation(validator, list_user_data):
    list_user_data["Resources"][0].pop("name")
    list_user_data["Resources"][1].pop("name")

    data, issues = validator.dump_response(
        status_code=200,
        body=list_user_data,
        start_index=1,
        count=2,
        filter_=Filter(Present(AttrRep(attr="username"))),
        sorter=Sorter(AttrRep(attr="userName"), True),
        presence_checker=AttributePresenceChecker(attr_reps=[AttrRep(attr="name")], include=False),
    )

    assert issues.to_dict() == {}
    assert data.body is not None


@pytest.mark.parametrize(
    "validator",
    (
        ResourceTypeGET(user.User()),
        ServerRootResourceGET([user.User()]),
        SearchRequestPOST([user.User()]),
    ),
)
def test_attributes_existence_is_validated_in_list_response(validator):
    expected_issues = {
        "body": {
            "schemas": {
                "_errors": [{"code": 15}],
            },
            "totalResults": {"_errors": [{"code": 15}]},
        }
    }

    data, issues = validator.dump_response(
        status_code=200,
        body={},
    )

    assert issues.to_dict() == expected_issues
    assert data.body is None


@pytest.mark.parametrize(
    "validator",
    (
        ResourceTypeGET(user.User()),
        ServerRootResourceGET([user.User()]),
        SearchRequestPOST([user.User()]),
    ),
)
def test_attributes_presence_is_validated_in_resources_in_list_response(validator):
    expected_issues = {
        "body": {
            "Resources": {
                "0": {
                    "id": {"_errors": [{"code": 15}]},
                    "schemas": {"_errors": [{"code": 15}]},
                    "userName": {"_errors": [{"code": 15}]},
                }
            },
        }
    }

    data, issues = validator.dump_response(
        status_code=200,
        body={
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
            "totalResults": 1,
            "Resources": [{}],
        },
    )

    assert issues.to_dict() == expected_issues
    assert data.body is None


def test_correct_search_request_passes_validation():
    validator = SearchRequestPOST([user.User()])

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
    assert data.body["presence_checker"].attr_reps == [
        AttrRep(attr="userName"),
        AttrRep(attr="name"),
    ]
    assert data.body["presence_checker"].include is True
    assert data.body["filter"].to_dict() == {
        "op": "eq",
        "attr_rep": "userName",
        "value": "bjensen",
    }
    assert data.body["sorter"].attr_rep == AttrRep(attr="name", sub_attr="familyName")
    assert data.body["sorter"].asc is False
    assert data.body["startindex"] == 2
    assert data.body["count"] == 10


def test_search_request_validation_fails_if_attributes_and_exclude_attributes_provided():
    validator = SearchRequestPOST([user.User()])
    expected_issues = {
        "body": {
            "attributes": {"_errors": [{"code": 30}]},
            "excludeAttributes": {"_errors": [{"code": 30}]},
        }
    }

    data, issues = validator.parse_request(
        body={
            "attributes": ["userName"],
            "excludeAttributes": ["name"],
        }
    )

    assert issues.to_dict() == expected_issues


@pytest.mark.parametrize("op", ("add", "replace"))
def test_required_sub_attrs_are_checked_when_adding_or_replacing_complex_items(op):
    validator = ResourceObjectPATCH(SchemaForTests())
    expected_issues = {
        "body": {
            "Operations": {
                "0": {
                    "value": {
                        "0": {"bool": {"_errors": [{"code": 15}]}},
                        "2": {"bool": {"_errors": [{"code": 2}]}},
                    }
                }
            }
        }
    }

    data, issues = validator.parse_request(
        body={
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "Operations": [
                {
                    "op": op,
                    "path": "c2_mv",
                    "value": [
                        {"str": "abc", "int": 123},
                        {"str": "def", "int": 456, "bool": True},
                        {"str": "egh", "int": 789, "bool": "not-bool"},
                    ],
                }
            ],
        }
    )

    assert data.body is None
    assert issues.to_dict() == expected_issues


@pytest.mark.parametrize("op", ("add", "replace"))
def test_required_sub_attrs_are_checked_when_adding_or_replacing_complex_attr(op):
    validator = ResourceObjectPATCH(SchemaForTests())
    expected_issues = {
        "body": {
            "Operations": {
                "0": {
                    "value": {
                        "c2_mv": {
                            "0": {"bool": {"_errors": [{"code": 15}]}},
                            "2": {"bool": {"_errors": [{"code": 2}]}},
                        }
                    }
                }
            }
        }
    }

    data, issues = validator.parse_request(
        body={
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "Operations": [
                {
                    "op": op,
                    "value": {
                        "c2_mv": [
                            {"str": "abc", "int": 123},
                            {"str": "def", "int": 456, "bool": True},
                            {"str": "egh", "int": 789, "bool": "not-bool"},
                        ],
                    },
                }
            ],
        }
    )

    assert data.body is None
    assert issues.to_dict() == expected_issues


def test_remove_operations_are_parsed():
    validator = ResourceObjectPATCH(SchemaForTests())
    expected_body = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [
            {
                "op": "remove",
                "path": PatchPath.parse("str")[0],
            },
            {
                "op": "remove",
                "path": PatchPath.parse("str_mv[value eq 'abc']")[0],
            },
            {
                "op": "remove",
                "path": PatchPath.parse("c2.int")[0],
            },
            {
                "op": "remove",
                "path": PatchPath.parse("c2_mv[int eq 1]")[0],
            },
            {
                "op": "remove",
                "path": PatchPath.parse("c2_mv[int eq 1].str")[0],
            },
        ],
    }

    data, issues = validator.parse_request(
        body={
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "Operations": [
                {
                    "op": "remove",
                    "path": "str",
                },
                {
                    "op": "remove",
                    "path": "str_mv[value eq 'abc']",
                },
                {
                    "op": "remove",
                    "path": "c2.int",
                },
                {
                    "op": "remove",
                    "path": "c2_mv[int eq 1]",
                },
                {
                    "op": "remove",
                    "path": "c2_mv[int eq 1].str",
                },
            ],
        }
    )

    assert issues.to_dict() == {}
    assert data.body == expected_body


def test_resource_object_patch_dumping_response_fails_if_204_but_attributes_requested():
    validator = ResourceObjectPATCH(user.User())

    data, issues = validator.dump_response(
        status_code=204,
        body=None,
        presence_checker=AttributePresenceChecker(
            attr_reps=[AttrRep(attr="userName")], include=True
        ),
    )

    assert issues.to_dict() == {"status": {"_errors": [{"code": 16}]}}
    assert data.body is None


def test_resource_object_patch_dumping_response_succeeds_if_204_and_no_attributes_requested():
    validator = ResourceObjectPATCH(user.User())

    data, issues = validator.dump_response(
        status_code=204,
        body=None,
        presence_checker=None,
    )

    assert issues.to_dict() == {}
    assert data.body is None


def test_resource_object_patch_dumping_response_succeeds_if_200_and_user_data(user_data_dump):
    validator = ResourceObjectPATCH(user.User())

    data, issues = validator.dump_response(
        status_code=200,
        body=user_data_dump,
        presence_checker=None,
    )

    assert issues.to_dict(msg=True) == {}


def test_resource_object_patch_dumping_response_succeeds_if_200_and_selected_attributes(
    user_data_dump,
):
    validator = ResourceObjectPATCH(user.User())

    data, issues = validator.dump_response(
        status_code=200,
        body={
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "id": "1",
            "userName": "bjensen",
        },
        presence_checker=AttributePresenceChecker(
            attr_reps=[AttrRep(attr="userName")], include=True
        ),
    )

    assert issues.to_dict(msg=True) == {}


def test_resource_object_delete_dumping_response_fails_if_status_different_than_204():
    validator = ResourceObjectDELETE()

    data, issues = validator.dump_response(status_code=200)

    assert issues.to_dict() == {"status": {"_errors": [{"code": 16}]}}


def test_resource_object_delete_dumping_response_succeeds_if_status_204():
    validator = ResourceObjectDELETE()

    data, issues = validator.dump_response(status_code=204)

    assert issues.to_dict(msg=True) == {}


def test_bulk_operations_request_is_parsed_if_correct_data():
    validator = BulkOperations(4, [user.User()])
    data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:BulkRequest"],
        "failOnErrors": 1,
        "Operations": [
            {
                "method": "POST",
                "path": "/Users",
                "bulkId": "qwerty",
                "data": {
                    "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
                    "userName": "Alice",
                },
            },
            {
                "method": "PUT",
                "path": "/Users/b7c14771-226c-4d05-8860-134711653041",
                "version": 'W/"3694e05e9dff591"',
                "data": {
                    "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
                    "id": "b7c14771-226c-4d05-8860-134711653041",
                    "userName": "Bob",
                },
            },
            {
                "method": "PATCH",
                "path": "/Users/5d8d29d3-342c-4b5f-8683-a3cb6763ffcc",
                "version": 'W"edac3253e2c0ef2"',
                "data": {
                    "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
                    "Operations": [
                        {"op": "remove", "path": "nickName"},
                        {"op": "add", "path": "userName", "value": "Dave"},
                    ],
                },
            },
            {
                "method": "DELETE",
                "path": "/Users/e9025315-6bea-44e1-899c-1e07454e468b",
                "version": 'W/"0ee8add0a938e1a"',
            },
        ],
    }
    expected_body: dict = deepcopy(data)
    expected_body["Operations"][1]["data"] = {"userName": "Bob"}
    expected_body["Operations"][2]["data"]["Operations"][0]["path"] = PatchPath(
        attr_rep=AttrRep(attr="nickName"), complex_filter=None, complex_filter_attr_rep=None
    )
    expected_body["Operations"][2]["data"]["Operations"][1]["path"] = PatchPath(
        attr_rep=AttrRep(attr="userName"), complex_filter=None, complex_filter_attr_rep=None
    )

    data, issues = validator.parse_request(body=data)

    assert issues.to_dict(msg=True) == {}
    assert data.body.to_dict() == expected_body


def test_bulk_operations_request_parsing_fails_for_bad_data():
    validator = BulkOperations(2, [user.User()])
    expected_issues = {
        "body": {
            "Operations": {
                "_errors": [{"code": 37}],
                "0": {
                    "data": {
                        "userName": {"_errors": [{"code": 15}]},
                        "nickName": {"_errors": [{"code": 2}]},
                    }
                },
                "1": {
                    "data": {
                        "schemas": {"_errors": [{"code": 15}]},
                        "userName": {"_errors": [{"code": 2}]},
                    }
                },
                "2": {
                    "version": {"_errors": [{"code": 2}]},
                    "data": {
                        "Operations": {
                            "0": {"path": {"_errors": [{"code": 111}]}},
                            "1": {"op": {"_errors": [{"code": 14}]}},
                        }
                    },
                },
            }
        }
    }
    data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:BulkRequest"],
        "failOnErrors": 1,
        "Operations": [
            {
                "method": "POST",
                "path": "/Users",
                "bulkId": "qwerty",
                "data": {
                    "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
                    "nickName": 123,
                },
            },
            {
                "method": "PUT",
                "path": "/Users/b7c14771-226c-4d05-8860-134711653041",
                "version": 'W/"3694e05e9dff591"',
                "data": {
                    "id": "b7c14771-226c-4d05-8860-134711653041",
                    "userName": 123,
                },
            },
            {
                "method": "PATCH",
                "path": "/Users/5d8d29d3-342c-4b5f-8683-a3cb6763ffcc",
                "version": 123,
                "data": {
                    "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
                    "Operations": [
                        {"op": "remove", "path": "bad^attr"},
                        {"op": "kill", "path": "userName", "value": "Dave"},
                    ],
                },
            },
            {
                "method": "DELETE",
                "path": "/Users/e9025315-6bea-44e1-899c-1e07454e468b",
                "version": 'W/"0ee8add0a938e1a"',
            },
        ],
    }

    data, issues = validator.parse_request(body=data)

    assert issues.to_dict() == expected_issues


def test_bulk_operations_response_is_dumped_if_correct_data(user_data_dump):
    validator = BulkOperations(4, [user.User()])

    user_1 = deepcopy(user_data_dump)
    user_1["id"] = "92b725cd-9465-4e7d-8c16-01f8e146b87a"
    user_1["meta"]["location"] = "https://example.com/v2/Users/92b725cd-9465-4e7d-8c16-01f8e146b87a"
    user_1["meta"]["version"] = 'W/"oY4m4wn58tkVjJxK"'

    user_2 = deepcopy(user_data_dump)
    user_2["id"] = "b7c14771-226c-4d05-8860-134711653041"
    user_2["meta"]["location"] = "https://example.com/v2/Users/b7c14771-226c-4d05-8860-134711653041"
    user_2["meta"]["version"] = 'W/"huJj29dMNgu3WXPD"'

    user_3 = deepcopy(user_data_dump)
    user_3["id"] = "5d8d29d3-342c-4b5f-8683-a3cb6763ffcc"
    user_3["meta"]["location"] = "https://example.com/v2/Users/5d8d29d3-342c-4b5f-8683-a3cb6763ffcc"
    user_3["meta"]["version"] = 'W/"huJj29dMNgu3WXPD"'

    data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:BulkResponse"],
        "Operations": [
            {
                "location": "https://example.com/v2/Users/92b725cd-9465-4e7d-8c16-01f8e146b87a",
                "method": "POST",
                "bulkId": "qwerty",
                "version": 'W/"oY4m4wn58tkVjJxK"',
                "response": user_1,
                "status": "201",
            },
            {
                "location": "https://example.com/v2/Users/b7c14771-226c-4d05-8860-134711653041",
                "method": "PUT",
                "version": 'W/"huJj29dMNgu3WXPD"',
                "response": user_2,
                "status": "200",
            },
            {
                "location": "https://example.com/v2/Users/5d8d29d3-342c-4b5f-8683-a3cb6763ffcc",
                "method": "PATCH",
                "version": 'W/"huJj29dMNgu3WXPD"',
                "response": user_3,
                "status": "200",
            },
            {
                "location": "https://example.com/v2/Users/e9025315-6bea-44e1-899c-1e07454e468b",
                "method": "DELETE",
                "status": "204",
            },
        ],
    }
    expected_body: dict = deepcopy(data)
    expected_body["Operations"][0]["response"]["meta"]["created"] = str(
        expected_body["Operations"][0]["response"]["meta"]["created"].isoformat()
    )
    expected_body["Operations"][0]["response"]["meta"]["lastModified"] = str(
        expected_body["Operations"][0]["response"]["meta"]["lastModified"].isoformat()
    )
    expected_body["Operations"][1]["response"]["meta"]["created"] = str(
        expected_body["Operations"][1]["response"]["meta"]["created"].isoformat()
    )
    expected_body["Operations"][1]["response"]["meta"]["lastModified"] = str(
        expected_body["Operations"][1]["response"]["meta"]["lastModified"].isoformat()
    )
    expected_body["Operations"][2]["response"]["meta"]["created"] = str(
        expected_body["Operations"][2]["response"]["meta"]["created"].isoformat()
    )
    expected_body["Operations"][2]["response"]["meta"]["lastModified"] = str(
        expected_body["Operations"][2]["response"]["meta"]["lastModified"].isoformat()
    )

    data, issues = validator.dump_response(body=data, status_code=200)

    assert issues.to_dict(msg=True) == {}
    assert data.body.to_dict() == expected_body


def test_bulk_operations_response_dumping_fails_for_incorrect_data(user_data_dump):
    validator = BulkOperations(4, [user.User()])

    user_1 = deepcopy(user_data_dump)
    user_1["id"] = "92b725cd-9465-4e7d-8c16-01f8e146b87a"
    user_1["meta"]["location"] = "https://example.com/v2/Users/92b725cd-9465-4e7d-8c16-01f8e146b87a"
    user_1["meta"]["version"] = 'W/"oY4m4wn58tkVjJxK"'
    user_1["userName"] = 123
    user_1.pop("id")

    user_2 = deepcopy(user_data_dump)
    user_2["id"] = "b7c14771-226c-4d05-8860-134711653041"
    user_2["meta"]["location"] = "https://example.com/v2/Users/b7c14771-226c-4d05-8860-134711653041"
    user_2["meta"]["version"] = 'W/"huJj29dMNgu3WXPD"'

    expected_issues = {
        "body": {
            "Operations": {
                "0": {
                    "location": {"_errors": [{"code": 11}]},
                    "response": {
                        "id": {"_errors": [{"code": 15}]},
                        "meta": {"location": {"_errors": [{"code": 11}]}},
                        "userName": {"_errors": [{"code": 2}]},
                    },
                },
                "1": {
                    "version": {"_errors": [{"code": 11}]},
                    "response": {"meta": {"version": {"_errors": [{"code": 11}]}}},
                },
                "2": {
                    "method": {"_errors": [{"code": 14}]},
                },
                "3": {"location": {"_errors": [{"code": 36}]}},
            }
        }
    }

    data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:BulkResponse"],
        "Operations": [
            {
                "location": "https://example.com/v2/Users/82b725cd-9465-4e7d-8c16-01f8e146b87b",
                "method": "POST",
                "bulkId": "qwerty",
                "version": 'W/"oY4m4wn58tkVjJxK"',
                "response": user_1,
                "status": "201",
            },
            {
                "location": "https://example.com/v2/Users/b7c14771-226c-4d05-8860-134711653041",
                "method": "PUT",
                "version": 'W/"LuJj29dMNgu3WXPD"',
                "response": user_2,
                "status": "200",
            },
            {
                "location": "https://example.com/v2/Users/5d8d29d3-342c-4b5f-8683-a3cb6763ffcc",
                "method": "GO_TO_HELL",
                "version": 'W/"huJj29dMNgu3WXPD"',
                "status": "666",
            },
            {
                "location": "https://example.com/v2/Unknown/e9025315-6bea-44e1-899c-1e07454e468b",
                "method": "DELETE",
                "status": "204",
            },
        ],
    }
    expected_body: dict = deepcopy(data)
    expected_body["Operations"][0]["response"]["meta"]["created"] = str(
        expected_body["Operations"][0]["response"]["meta"]["created"].isoformat()
    )
    expected_body["Operations"][0]["response"]["meta"]["lastModified"] = str(
        expected_body["Operations"][0]["response"]["meta"]["lastModified"].isoformat()
    )
    expected_body["Operations"][1]["response"]["meta"]["created"] = str(
        expected_body["Operations"][1]["response"]["meta"]["created"].isoformat()
    )
    expected_body["Operations"][1]["response"]["meta"]["lastModified"] = str(
        expected_body["Operations"][1]["response"]["meta"]["lastModified"].isoformat()
    )

    data, issues = validator.dump_response(body=data, status_code=200, fail_on_errors=2)

    assert issues.to_dict() == expected_issues
    assert data.body is None


def test_bulk_operations_response_dumping_fails_if_too_many_failed_operations(user_data_dump):
    validator = BulkOperations(4, [user.User()])

    expected_issues = {"body": {"Operations": {"_errors": [{"code": 38}]}}}

    data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:BulkResponse"],
        "Operations": [
            {
                "method": "POST",
                "bulkId": "qwerty",
                "status": "400",
                "response": {
                    "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
                    "scimType": "invalidSyntax",
                    "detail": "Request is unparsable, syntactically incorrect, or violates schema.",
                    "status": "400",
                },
            },
            {
                "location": "https://example.com/v2/Users/b7c14771-226c-4d05-8860-134711653041",
                "method": "PUT",
                "status": "412",
                "response": {
                    "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
                    "detail": "Failed to update.  Resource changed on the server.",
                    "status": "412",
                },
            },
        ],
    }

    data, issues = validator.dump_response(body=data, status_code=200, fail_on_errors=1)

    assert issues.to_dict() == expected_issues
    assert data.body is None
