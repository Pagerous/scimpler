from copy import deepcopy

import pytest

from src.assets.config import create_service_provider_config
from src.assets.schemas import group, list_response, service_provider_config, user
from src.assets.schemas.resource_type import ResourceType
from src.assets.schemas.schema import Schema
from src.attributes_presence import AttributePresenceChecker
from src.data.container import AttrRep, BoundedAttrRep, Missing, SCIMDataContainer
from src.data.operator import Present
from src.data.path import PatchPath
from src.filter import Filter
from src.request_validator import (
    BulkOperations,
    Error,
    ResourceObjectDELETE,
    ResourceObjectGET,
    ResourceObjectPATCH,
    ResourceObjectPUT,
    ResourcesGET,
    ResourcesPOST,
    ResourceTypesGET,
    SchemasGET,
    SearchRequestPOST,
    ServerRootResourcesGET,
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
from src.sorter import Sorter
from tests.conftest import CONFIG, SchemaForTests


@pytest.mark.parametrize(
    ("status_code", "expected"),
    (
        (199, {"status": {"_errors": [{"code": 1}]}}),
        (600, {"status": {"_errors": [{"code": 1}]}}),
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
        ({}, True, {"Location": {"_errors": [{"code": 15}]}}),
        ([1, 2, 3], True, {"Location": {"_errors": [{"code": 15}]}}),
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


def test_validate_resource_location_consistency__fails_if_no_consistency(user_data_server):
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
        user_data_server["meta"]["location"],
        headers_location,
    )

    assert issues.to_dict() == expected_issues


def test_validate_resource_location_consistency__succeeds_if_consistency(user_data_server):
    issues = validate_resource_location_consistency(
        user_data_server["meta"]["location"],
        user_data_server["meta"]["location"],
    )

    assert issues.to_dict(msg=True) == {}


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

    assert issues.to_dict(msg=True) == {}


def test_validate_pagination_info__fails_if_start_index_is_missing_when_pagination(list_user_data):
    expected = {
        "startIndex": {"_errors": [{"code": 15}]},
    }

    issues = validate_pagination_info(
        schema=list_response.ListResponse([user.User]),
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
        schema=list_response.ListResponse([user.User]),
        count=1,
        total_results=2,
        resources=[SCIMDataContainer(list_user_data["Resources"][0])],
        start_index=1,
        items_per_page=Missing,
    )

    assert issues.to_dict() == expected


def test_validate_pagination_info__correct_data_when_pagination(list_user_data):
    issues = validate_pagination_info(
        schema=list_response.ListResponse([user.User]),
        count=2,
        total_results=2,
        resources=[SCIMDataContainer(list_user_data["Resources"][0])],
        start_index=1,
        items_per_page=1,
    )

    assert issues.to_dict(msg=True) == {}


def test_validate_start_index_consistency__fails_if_start_index_bigger_than_requested():
    expected = {"_errors": [{"code": 24}]}

    issues = validate_start_index_consistency(start_index=1, start_index_body=2)

    assert issues.to_dict() == expected


def test_validate_start_index_consistency__succeeds_if_correct_data():
    issues = validate_start_index_consistency(start_index=1, start_index_body=1)

    assert issues.to_dict(msg=True) == {}


@pytest.mark.parametrize(
    "filter_exp",
    (
        'emails[value eq "sven@example.com"]',
        'emails eq "sven@example.com"',
        'name.familyName eq "Sven"',
    ),
)
def test_validate_resources_filtered(filter_exp, list_user_data):
    filter_ = Filter.deserialize(filter_exp)
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
        resource_schemas=[user.User, user.User],
        strict=False,
    )

    assert issues.to_dict() == expected


def test_validate_resources_filtered__case_sensitivity_matters(list_user_data):
    filter_ = Filter.deserialize('meta.resourcetype eq "user"')  # "user", not "User"
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
        resource_schemas=[user.User, user.User],
        strict=False,
    )

    assert issues.to_dict() == expected


def test_validate_resources_filtered__fields_from_schema_extensions_are_checked_by_filter(
    list_user_data,
):
    filter_ = Filter.deserialize(
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
        resource_schemas=[user.User, user.User],
        strict=False,
    )

    assert issues.to_dict() == expected


@pytest.mark.parametrize(
    "sorter",
    (
        Sorter(BoundedAttrRep(attr="name", sub_attr="familyName"), asc=False),
        Sorter(
            BoundedAttrRep(
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
        resource_schemas=[user.User, user.User],
    )

    assert issues.to_dict() == expected


def test_validate_resources_attribute_presence__fails_if_requested_attribute_not_excluded(
    list_user_data,
):
    checker = AttributePresenceChecker(attr_reps=[BoundedAttrRep(attr="name")], include=False)
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
        resource_schemas=[user.User, user.User],
    )

    assert issues.to_dict() == expected


def test_correct_error_response_passes_validation(error_data):
    validator = Error(CONFIG)

    issues = validator.validate_response(status_code=400, body=error_data)

    assert issues.to_dict(msg=True) == {}


def test_correct_resource_object_get_request_passes_validation():
    validator = ResourceObjectGET(CONFIG, resource_schema=user.User)

    issues = validator.validate_request(body=None, query_string={"attributes": ["name.familyName"]})

    assert issues.to_dict(msg=True) == {}


def test_correct_resource_object_get_response_passes_validation(user_data_server):
    validator = ResourceObjectGET(CONFIG, resource_schema=user.User)
    user_data_server.pop("name")

    issues = validator.validate_response(
        status_code=200,
        body=user_data_server,
        headers={
            "Location": user_data_server["meta"]["location"],
            "ETag": user_data_server["meta"]["version"],
        },
        presence_checker=AttributePresenceChecker(
            attr_reps=[BoundedAttrRep(attr="name")], include=False
        ),
    )

    assert issues.to_dict(msg=True) == {}


def test_validation_failure_on_missing_etag_header_when_etag_supported(user_data_server):
    validator = ResourceObjectGET(CONFIG, resource_schema=user.User)
    expected_issues = {"headers": {"ETag": {"_errors": [{"code": 15}]}}}

    issues = validator.validate_response(
        status_code=200,
        body=user_data_server,
        headers={
            "Location": user_data_server["meta"]["location"],
        },
    )

    assert issues.to_dict() == expected_issues


def test_validation_failure_on_missing_meta_version_when_etag_supported(user_data_server):
    validator = ResourceObjectGET(CONFIG, resource_schema=user.User)
    user_data_server["meta"].pop("version")
    expected_issues = {"body": {"meta": {"version": {"_errors": [{"code": 15}]}}}}

    issues = validator.validate_response(
        status_code=200,
        body=user_data_server,
        headers={
            "Location": user_data_server["meta"]["location"],
            "ETag": 'W/"3694e05e9dff591"',
        },
    )

    assert issues.to_dict() == expected_issues


def test_validation_failure_on_etag_and_meta_version_mismatch_when_etag_supported(user_data_server):
    validator = ResourceObjectGET(CONFIG, resource_schema=user.User)
    expected_issues = {
        "body": {"meta": {"version": {"_errors": [{"code": 11}]}}},
        "headers": {"ETag": {"_errors": [{"code": 11}]}},
    }

    issues = validator.validate_response(
        status_code=200,
        body=user_data_server,
        headers={
            "Location": user_data_server["meta"]["location"],
            "ETag": 'W/"3694e05e9dff592"',
        },
    )

    assert issues.to_dict() == expected_issues


def test_validation_failure_on_etag_and_meta_version_mismatch_when_etag_not_supported(
    user_data_server,
):
    config = deepcopy(CONFIG)
    config.etag.supported = False
    validator = ResourceObjectGET(config, resource_schema=user.User)
    expected_issues = {
        "body": {"meta": {"version": {"_errors": [{"code": 11}]}}},
        "headers": {"ETag": {"_errors": [{"code": 11}]}},
    }

    issues = validator.validate_response(
        status_code=200,
        body=user_data_server,
        headers={
            "Location": user_data_server["meta"]["location"],
            "ETag": 'W/"3694e05e9dff592"',
        },
    )

    assert issues.to_dict() == expected_issues


def test_response_is_validated_without_tag_and_version_if_etag_not_supported(user_data_server):
    config = deepcopy(CONFIG)
    config.etag.supported = False
    validator = ResourceObjectGET(config, resource_schema=user.User)
    user_data_server["meta"].pop("version")

    issues = validator.validate_response(
        status_code=200,
        body=user_data_server,
        headers={
            "Location": user_data_server["meta"]["location"],
        },
    )

    assert issues.to_dict(msg=True) == {}


def test_etag_and_version_are_not_compared_if_bad_version_value(user_data_server):
    validator = ResourceObjectGET(CONFIG, resource_schema=user.User)
    user_data_server["meta"]["version"] = 123
    expected_issues = {"body": {"meta": {"version": {"_errors": [{"code": 2}]}}}}

    issues = validator.validate_response(
        status_code=200,
        body=user_data_server,
        headers={
            "Location": user_data_server["meta"]["location"],
            "ETag": 'W/"3694e05e9dff591"',
        },
    )

    assert issues.to_dict() == expected_issues


def test_validation_warning_for_missing_response_body_for_resources_post():
    validator = ResourcesPOST(CONFIG, resource_schema=user.User)
    expected_issues = {"body": {"_warnings": [{"code": 4}]}}

    issues = validator.validate_response(
        status_code=201,
        body=None,
    )

    assert issues.to_dict() == expected_issues


def test_correct_resource_type_post_request_passes_validation(user_data_client):
    validator = ResourcesPOST(CONFIG, resource_schema=user.User)

    issues = validator.validate_request(
        body=user_data_client,
        query_string={"attributes": ["name.familyName"]},
    )

    assert issues.to_dict(msg=True) == {}


def test_resource_type_post_request_parsing_fails_for_incorrect_data_passes_validation(
    user_data_client,
):
    validator = ResourcesPOST(CONFIG, resource_schema=user.User)
    user_data_client["userName"] = 123
    expected_issues = {"body": {"userName": {"_errors": [{"code": 2}]}}}

    issues = validator.validate_request(
        body=user_data_client,
    )

    assert issues.to_dict() == expected_issues


def test_resources_post_response_validation_fails_if_different_created_and_last_modified(
    user_data_server,
):
    validator = ResourcesPOST(CONFIG, resource_schema=user.User)
    user_data_server["meta"]["lastModified"] = "2011-05-13T04:42:34Z"
    expected_issues = {"body": {"meta": {"lastModified": {"_errors": [{"code": 11}]}}}}

    issues = validator.validate_response(
        body=user_data_server,
        status_code=201,
        headers={
            "Location": user_data_server["meta"]["location"],
            "ETag": user_data_server["meta"]["version"],
        },
    )

    assert issues.to_dict() == expected_issues


def test_correct_resource_object_put_request_passes_validation(user_data_client):
    validator = ResourceObjectPUT(CONFIG, resource_schema=user.User)
    user_data_client["id"] = "anything"

    issues = validator.validate_request(
        body=user_data_client,
        query_string={"attributes": ["name.familyName"]},
    )

    assert issues.to_dict(msg=True) == {}


def test_resource_object_put_request__fails_when_missing_required_field(user_data_client):
    validator = ResourceObjectPUT(CONFIG, resource_schema=user.User)
    # user_data_client misses 'id' and 'meta'
    expected_issues = {"body": {"id": {"_errors": [{"code": 15}]}}}

    issues = validator.validate_request(body=user_data_client)

    assert issues.to_dict() == expected_issues


def test_correct_resource_object_put_response_passes_validation(user_data_server):
    validator = ResourceObjectPUT(CONFIG, resource_schema=user.User)

    issues = validator.validate_response(
        status_code=200,
        body=user_data_server,
        headers={
            "Location": user_data_server["meta"]["location"],
            "ETag": user_data_server["meta"]["version"],
        },
    )

    assert issues.to_dict(msg=True) == {}


def test_correct_resource_type_post_response_passes_validation(user_data_server):
    validator = ResourcesPOST(CONFIG, resource_schema=user.User)

    issues = validator.validate_response(
        status_code=201,
        body=user_data_server,
        headers={
            "Location": user_data_server["meta"]["location"],
            "ETag": user_data_server["meta"]["version"],
        },
    )

    assert issues.to_dict(msg=True) == {}


@pytest.mark.parametrize(
    "validator",
    (
        ResourcesGET(CONFIG, resource_schema=user.User),
        ServerRootResourcesGET(CONFIG, resource_schemas=[user.User]),
        SearchRequestPOST(CONFIG, resource_schemas=[user.User]),
    ),
)
def test_correct_list_response_passes_validation(validator, list_user_data):
    list_user_data["Resources"][0].pop("name")
    list_user_data["Resources"][1].pop("name")

    issues = validator.validate_response(
        status_code=200,
        body=list_user_data,
        start_index=1,
        count=2,
        filter_=Filter(Present(AttrRep(attr="username"))),
        sorter=Sorter(BoundedAttrRep(attr="userName"), True),
        presence_checker=AttributePresenceChecker(
            attr_reps=[BoundedAttrRep(attr="name")], include=False
        ),
    )

    assert issues.to_dict(msg=True) == {}


@pytest.mark.parametrize(
    "validator",
    (
        ResourcesGET(CONFIG, resource_schema=user.User),
        ServerRootResourcesGET(CONFIG, resource_schemas=[user.User]),
        SearchRequestPOST(CONFIG, resource_schemas=[user.User]),
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

    issues = validator.validate_response(
        status_code=200,
        body={},
    )

    assert issues.to_dict() == expected_issues


@pytest.mark.parametrize(
    "validator",
    (
        ResourcesGET(CONFIG, resource_schema=user.User),
        ServerRootResourcesGET(CONFIG, resource_schemas=[user.User]),
        SearchRequestPOST(CONFIG, resource_schemas=[user.User]),
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

    issues = validator.validate_response(
        status_code=200,
        body={
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
            "totalResults": 1,
            "Resources": [{}],
        },
    )

    assert issues.to_dict() == expected_issues


def test_correct_search_request_passes_validation():
    validator = SearchRequestPOST(CONFIG, resource_schemas=[user.User])

    issues = validator.validate_request(
        body={
            "attributes": ["userName", "name"],
            "filter": 'userName eq "bjensen"',
            "sortBy": "name.familyName",
            "sortOrder": "descending",
            "startIndex": 2,
            "count": 10,
        }
    )

    assert issues.to_dict(msg=True) == {}


def test_search_request_validation_fails_if_attributes_and_exclude_attributes_provided():
    validator = SearchRequestPOST(CONFIG, resource_schemas=[user.User])
    expected_issues = {
        "body": {
            "attributes": {"_errors": [{"code": 30}]},
            "excludeAttributes": {"_errors": [{"code": 30}]},
        }
    }

    issues = validator.validate_request(
        body={
            "attributes": ["userName"],
            "excludeAttributes": ["name"],
        }
    )

    assert issues.to_dict() == expected_issues


@pytest.mark.parametrize("op", ("add", "replace"))
def test_required_sub_attrs_are_checked_when_adding_or_replacing_complex_items(op):
    validator = ResourceObjectPATCH(CONFIG, resource_schema=SchemaForTests)
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

    issues = validator.validate_request(
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

    assert issues.to_dict() == expected_issues


@pytest.mark.parametrize("op", ("add", "replace"))
def test_required_sub_attrs_are_checked_when_adding_or_replacing_complex_attr(op):
    validator = ResourceObjectPATCH(CONFIG, resource_schema=SchemaForTests)
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

    issues = validator.validate_request(
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

    assert issues.to_dict() == expected_issues


def test_correct_remove_operations_pass_validation():
    validator = ResourceObjectPATCH(CONFIG, resource_schema=SchemaForTests)
    issues = validator.validate_request(
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

    assert issues.to_dict(msg=True) == {}


def test_resource_object_patch_response_validation_fails_if_204_but_attributes_requested():
    validator = ResourceObjectPATCH(CONFIG, resource_schema=user.User)

    issues = validator.validate_response(
        status_code=204,
        body=None,
        presence_checker=AttributePresenceChecker(
            attr_reps=[AttrRep(attr="userName")], include=True
        ),
    )

    assert issues.to_dict() == {"status": {"_errors": [{"code": 16}]}}


def test_resource_object_patch_response_validation_succeeds_if_204_and_no_attributes_requested():
    validator = ResourceObjectPATCH(CONFIG, resource_schema=user.User)

    issues = validator.validate_response(
        status_code=204,
        body=None,
        presence_checker=None,
    )

    assert issues.to_dict(msg=True) == {}


def test_resource_object_patch_response_validation_succeeds_if_200_and_user_data(user_data_server):
    validator = ResourceObjectPATCH(CONFIG, resource_schema=user.User)

    issues = validator.validate_response(
        status_code=200,
        body=user_data_server,
        presence_checker=None,
        headers={"ETag": user_data_server["meta"]["version"]},
    )

    assert issues.to_dict(msg=True) == {}


def test_resource_object_patch_response_validation_succeeds_if_200_and_selected_attributes(
    user_data_server,
):
    validator = ResourceObjectPATCH(CONFIG, resource_schema=user.User)

    issues = validator.validate_response(
        status_code=200,
        body={
            "schemas": [
                "urn:ietf:params:scim:schemas:core:2.0:User",
                "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
            ],
            "id": "1",
            "userName": "bjensen",
        },
        presence_checker=AttributePresenceChecker(
            attr_reps=[BoundedAttrRep(attr="userName")], include=True
        ),
        headers={"ETag": 'W/"3694e05e9dff591"'},
    )

    assert issues.to_dict(msg=True) == {}


def test_resource_object_delete_response_validation_fails_if_status_different_than_204():
    validator = ResourceObjectDELETE(CONFIG)

    issues = validator.validate_response(status_code=200)

    assert issues.to_dict() == {"status": {"_errors": [{"code": 16}]}}


def test_resource_object_delete_response_validation_succeeds_if_status_204():
    validator = ResourceObjectDELETE(CONFIG)

    issues = validator.validate_response(status_code=204)

    assert issues.to_dict(msg=True) == {}


def test_bulk_operations_request_is_valid_if_correct_data():
    validator = BulkOperations(CONFIG, resource_schemas=[user.User])
    data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:BulkRequest"],
        "failOnErrors": 1,
        "Operations": [
            {
                "method": "POST",
                "path": "/Users",
                "bulkId": "qwerty",
                "data": {
                    "schemas": [
                        "urn:ietf:params:scim:schemas:core:2.0:User",
                        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
                    ],
                    "userName": "Alice",
                },
            },
            {
                "method": "PUT",
                "path": "/Users/b7c14771-226c-4d05-8860-134711653041",
                "version": 'W/"3694e05e9dff591"',
                "data": {
                    "schemas": [
                        "urn:ietf:params:scim:schemas:core:2.0:User",
                        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
                    ],
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
        attr_rep=BoundedAttrRep(attr="nickName"), filter=None, filter_sub_attr_rep=None
    )
    expected_body["Operations"][2]["data"]["Operations"][1]["path"] = PatchPath(
        attr_rep=BoundedAttrRep(attr="userName"), filter=None, filter_sub_attr_rep=None
    )

    issues = validator.validate_request(body=data)

    assert issues.to_dict(msg=True) == {}


def test_bulk_operations_request_validation_fails_for_bad_data():
    validator = BulkOperations(
        config=create_service_provider_config(
            bulk={"max_operations": 2, "max_payload_size": 1024, "supported": True}
        ),
        resource_schemas=[user.User],
    )
    expected_issues = {
        "body": {
            "Operations": {
                "_errors": [{"code": 37}],
                "0": {
                    "data": {
                        "userName": {"_errors": [{"code": 15}]},
                        "nickName": {"_errors": [{"code": 2}]},
                        "schemas": {"_errors": [{"code": 29}]},
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

    issues = validator.validate_request(body=data)

    assert issues.to_dict() == expected_issues


def test_bulk_operations_response_is_valid_if_correct_data(user_data_server):
    validator = BulkOperations(CONFIG, resource_schemas=[user.User])

    user_1 = deepcopy(user_data_server)
    user_1["id"] = "92b725cd-9465-4e7d-8c16-01f8e146b87a"
    user_1["meta"]["location"] = "https://example.com/v2/Users/92b725cd-9465-4e7d-8c16-01f8e146b87a"
    user_1["meta"]["version"] = 'W/"oY4m4wn58tkVjJxK"'

    user_2 = deepcopy(user_data_server)
    user_2["id"] = "b7c14771-226c-4d05-8860-134711653041"
    user_2["meta"]["location"] = "https://example.com/v2/Users/b7c14771-226c-4d05-8860-134711653041"
    user_2["meta"]["version"] = 'W/"huJj29dMNgu3WXPD"'

    user_3 = deepcopy(user_data_server)
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

    issues = validator.validate_response(body=data, status_code=200)

    assert issues.to_dict(msg=True) == {}


def test_bulk_operations_response_validation_fails_for_incorrect_data(user_data_server):
    validator = BulkOperations(CONFIG, resource_schemas=[user.User])

    user_1 = deepcopy(user_data_server)
    user_1["id"] = "92b725cd-9465-4e7d-8c16-01f8e146b87a"
    user_1["meta"]["location"] = "https://example.com/v2/Users/92b725cd-9465-4e7d-8c16-01f8e146b87a"
    user_1["meta"]["version"] = 'W/"oY4m4wn58tkVjJxK"'
    user_1["userName"] = 123
    user_1.pop("id")

    user_2 = deepcopy(user_data_server)
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

    issues = validator.validate_response(body=data, status_code=200, fail_on_errors=2)

    assert issues.to_dict() == expected_issues


def test_bulk_operations_response_validation_fails_if_too_many_failed_operations(user_data_server):
    validator = BulkOperations(CONFIG, resource_schemas=[user.User])

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

    issues = validator.validate_response(body=data, status_code=200, fail_on_errors=1)

    assert issues.to_dict() == expected_issues


def test_service_provider_configuration_is_validated():
    validator = ResourceObjectGET(
        CONFIG, resource_schema=service_provider_config.ServiceProviderConfig
    )
    input_ = {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig"],
        "documentationUri": "https://example.com/help/scim.html",
        "patch": {"supported": True},
        "bulk": {"supported": True, "maxOperations": 1000, "maxPayloadSize": 1048576},
        "filter": {"supported": True, "maxResults": 200},
        "changePassword": {"supported": True},
        "sort": {"supported": True},
        "etag": {"supported": True},
        "authenticationSchemes": [
            {
                "name": "OAuth Bearer Token",
                "description": "Authentication scheme using the OAuth Bearer Token Standard",
                "specUri": "https://www.rfc-editor.org/info/rfc6750",
                "documentationUri": "https://example.com/help/oauth.html",
                "type": "oauthbearertoken",
                "primary": True,
            },
            {
                "name": "HTTP Basic",
                "description": "Authentication scheme using the HTTP Basic Standard",
                "specUri": "https://www.rfc-editor.org/info/rfc2617",
                "documentationUri": "https://example.com/help/httpBasic.html",
                "type": "httpbasic",
            },
        ],
        "meta": {
            "location": "https://example.com/v2/ServiceProviderConfig",
            "resourceType": "ServiceProviderConfig",
            "created": "2010-01-23T04:56:22Z",
            "lastModified": "2011-05-13T04:42:34Z",
            "version": 'W/"3694e05e9dff594"',
        },
    }

    issues = validator.validate_response(
        status_code=200,
        body=input_,
        headers={
            "Location": input_["meta"]["location"],
            "ETag": input_["meta"]["version"],
        },
    )

    assert issues.to_dict(msg=True) == {}


def test_group_output_is_validated_correctly():
    validator = ResourceObjectGET(CONFIG, resource_schema=group.Group)
    input_ = {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"],
        "id": "e9e30dba-f08f-4109-8486-d5c6a331660a",
        "displayName": "Tour Guides",
        "members": [
            {
                "value": "2819c223-7f76-453a-919d-413861904646",
                "$ref": "https://example.com/v2/Users/2819c223-7f76-453a-919d-413861904646",
                "display": "Babs Jensen",
            },
            {
                "value": "902c246b-6245-4190-8e05-00816be7344a",
                "$ref": "https://example.com/v2/Users/902c246b-6245-4190-8e05-00816be7344a",
                "display": "Mandy Pepperidge",
            },
        ],
        "meta": {
            "location": "https://example.com/v2/Groups/e9e30dba-f08f-4109-8486-d5c6a331660a",
            "resourceType": "Group",
            "created": "2011-05-13T04:42:34Z",
            "lastModified": "2011-05-13T04:42:34Z",
            "version": 'W/"3694e05e9dff594"',
        },
    }

    issues = validator.validate_response(
        status_code=200,
        body=input_,
        headers={
            "Location": input_["meta"]["location"],
            "ETag": input_["meta"]["version"],
        },
    )

    assert issues.to_dict(msg=True) == {}


def test_schemas_output_can_be_validated():
    validator = SchemasGET(CONFIG)
    body = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "totalResults": 2,
        "itemsPerPage": 2,
        "startIndex": 1,
        "Resources": [Schema.get_repr(user.User), Schema.get_repr(group.Group)],
    }

    issues = validator.validate_response(status_code=200, body=body)

    assert issues.to_dict(msg=True) == {}


@pytest.mark.parametrize("validator", [SchemasGET(CONFIG), ResourceTypesGET(CONFIG)])
def test_service_config_request_parsing_fails_if_requested_filtering(validator):
    expected_issues = {"query_string": {"filter": {"_errors": [{"code": 39}]}}}

    issues = validator.validate_request(query_string={"filter": 'description sw "Hello, World!"'})

    assert issues.to_dict() == expected_issues


def test_schema_response_can_be_validated():
    validator = ResourceObjectGET(CONFIG, resource_schema=Schema)

    issues = validator.validate_response(
        status_code=200,
        body=Schema.get_repr(user.User, version='W/"3694e05e9dff591"'),
        headers={
            "ETag": 'W/"3694e05e9dff591"',
        },
    )

    assert issues.to_dict(msg=True) == {}


def test_resource_type_response_can_be_validated():
    validator = ResourceObjectGET(CONFIG, resource_schema=ResourceType)
    body = {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ResourceType"],
        "id": "User",
        "name": "User",
        "endpoint": "/Users",
        "description": "User Account",
        "schema": "urn:ietf:params:scim:schemas:core:2.0:User",
        "schemaExtensions": [
            {
                "schema": "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
                "required": True,
            }
        ],
        "meta": {
            "location": "https://example.com/v2/ResourceTypes/User",
            "resourceType": "ResourceType",
            "version": 'W/"3694e05e9dff591"',
        },
    }

    issues = validator.validate_response(
        status_code=200,
        body=body,
        headers={
            "ETag": 'W/"3694e05e9dff591"',
        },
    )

    assert issues.to_dict(msg=True) == {}


def test_resource_types_response_can_be_validated():
    validator = ResourceTypesGET(CONFIG)
    body = {
        "totalResults": 2,
        "itemsPerPage": 2,
        "startIndex": 1,
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "Resources": [
            {
                "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ResourceType"],
                "id": "User",
                "name": "User",
                "endpoint": "/Users",
                "description": "User Account",
                "schema": "urn:ietf:params:scim:schemas:core:2.0:User",
                "schemaExtensions": [
                    {
                        "schema": "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
                        "required": True,
                    }
                ],
                "meta": {
                    "location": "https://example.com/v2/ResourceTypes/User",
                    "resourceType": "ResourceType",
                },
            },
            {
                "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ResourceType"],
                "id": "Group",
                "name": "Group",
                "endpoint": "/Groups",
                "description": "Group",
                "schema": "urn:ietf:params:scim:schemas:core:2.0:Group",
                "meta": {
                    "location": "https://example.com/v2/ResourceTypes/Group",
                    "resourceType": "ResourceType",
                },
            },
        ],
    }

    issues = validator.validate_response(status_code=200, body=body)

    assert issues.to_dict(msg=True) == {}
