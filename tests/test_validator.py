from copy import deepcopy
from datetime import datetime

import pytest

from scimpler.config import ServiceProviderConfig
from scimpler.data import ScimData
from scimpler.data.attr_value_presence import AttrValuePresenceConfig
from scimpler.data.attrs import DateTime
from scimpler.data.filter import Filter
from scimpler.data.identifiers import AttrRep, BoundedAttrRep
from scimpler.data.operator import Present
from scimpler.data.patch_path import PatchPath
from scimpler.data.scim_data import Missing
from scimpler.data.sorter import Sorter
from scimpler.schemas import service_provider_config
from scimpler.schemas.resource_type import ResourceTypeSchema
from scimpler.schemas.schema import SchemaDefinitionSchema
from scimpler.validator import (
    BulkOperations,
    Error,
    ResourceObjectDelete,
    ResourceObjectGet,
    ResourceObjectPatch,
    ResourceObjectPut,
    ResourcesPost,
    ResourcesQuery,
    SearchRequestPost,
    can_validate_filtering,
    can_validate_sorting,
)
from tests.conftest import CONFIG


@pytest.mark.parametrize(
    ("status_code", "expected"),
    (
        (
            404,
            {
                "status": {"_errors": [{"code": 8}]},
                "body": {"status": {"_errors": [{"code": 8}]}},
            },
        ),
        (400, {}),
    ),
)
def test_validate_error_status_code_consistency(status_code, expected):
    validator = Error()

    issues = validator.validate_response(
        status_code=status_code,
        body={"schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"], "status": "400"},
    )

    assert issues.to_dict() == expected


def test_validate_error_status_code_value():
    validator = Error()
    expected_issues = {
        "body": {"status": {"_errors": [{"code": 4}]}},
        "status": {"_errors": [{"code": 4}]},
    }

    issues = validator.validate_response(
        status_code=601,
        body={"schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"], "status": "601"},
    )

    assert issues.to_dict() == expected_issues


def test_resource_location_consistency_validation_fails_if_no_consistency(
    user_data_server, user_schema
):
    validator = ResourcesPost(CONFIG, resource_schema=user_schema)

    expected_issues = {
        "body": {
            "meta": {
                "location": {
                    "_errors": [
                        {
                            "code": 8,
                        }
                    ]
                }
            }
        },
        "headers": {
            "Location": {
                "_errors": [
                    {
                        "code": 8,
                    }
                ]
            }
        },
    }

    issues = validator.validate_response(
        status_code=201,
        body=user_data_server,
        headers={
            "Location": "https://example.com/v2/Users/2819c223-7f76-453a-919d-413861904647",
            "ETag": r'W/"3694e05e9dff591"',
        },
    )
    assert issues.to_dict() == expected_issues


def test_resource_location_consistency_validation_is_not_checked_if_meta_location_excluded(
    user_data_server, user_schema
):
    validator = ResourcesPost(CONFIG, resource_schema=user_schema)
    user_data_server["meta"].pop("location")

    issues = validator.validate_response(
        status_code=201,
        body=user_data_server,
        headers={
            "Location": "https://example.com/v2/Users/2819c223-7f76-453a-919d-413861904647",
            "ETag": r'W/"3694e05e9dff591"',
        },
        presence_config=AttrValuePresenceConfig("RESPONSE", ["meta.location"], include=False),
    )

    assert issues.to_dict(msg=True) == {}


def test_resource_output_validation_fails_if_attr_value_presence_config_for_request(
    user_data_server, user_schema
):
    validator = ResourcesPost(CONFIG, resource_schema=user_schema)

    with pytest.raises(
        ValueError, match="bad direction in attribute presence config for response validation"
    ):
        validator.validate_response(
            status_code=201,
            body=user_data_server,
            headers={
                "Location": "https://example.com/v2/Users/2819c223-7f76-453a-919d-413861904647",
                "ETag": r'W/"3694e05e9dff591"',
            },
            presence_config=AttrValuePresenceConfig("REQUEST", ["meta.location"], include=False),
        )


def test_validate_resource_location_consistency__succeeds_if_consistency(
    user_data_server, user_schema
):
    validator = ResourcesPost(CONFIG, resource_schema=user_schema)

    issues = validator.validate_response(
        status_code=201,
        body=user_data_server,
        headers={
            "Location": user_data_server["meta"]["location"],
            "ETag": r'W/"3694e05e9dff591"',
        },
    )
    assert issues.to_dict(msg=True) == {}


def test_number_of_resources_validation_fails_if_more_resources_than_total_results(
    list_user_data, user_schema
):
    list_user_data["totalResults"] = 1
    validator = ResourcesQuery(CONFIG, resource_schema=user_schema)
    expected = {"body": {"Resources": {"_errors": [{"code": 20}]}}}

    issues = validator.validate_response(
        status_code=200,
        body=list_user_data,
        count=None,
    )

    assert issues.to_dict() == expected


def test_number_of_resources_validation_fails_if_less_resources_than_total_results_without_count(
    list_user_data, user_schema
):
    list_user_data["totalResults"] = 3
    validator = ResourcesQuery(CONFIG, resource_schema=user_schema)
    expected = {"body": {"Resources": {"_errors": [{"code": 20}]}}}

    issues = validator.validate_response(
        status_code=200,
        body=list_user_data,
        count=None,
    )

    assert issues.to_dict() == expected


def test_number_of_resources_validation_fails_if_more_resources_than_specified_count(
    list_user_data, user_schema
):
    validator = ResourcesQuery(CONFIG, resource_schema=user_schema)
    expected = {"body": {"Resources": {"_errors": [{"code": 20}]}}}

    issues = validator.validate_response(
        status_code=200,
        body=list_user_data,
        count=1,
    )

    assert issues.to_dict() == expected


@pytest.mark.parametrize("count", (2, None))
def test_number_of_resources_validation_succeeds_if_correct_number_of_resources(
    count, list_user_data, user_schema
):
    validator = ResourcesQuery(CONFIG, resource_schema=user_schema)

    issues = validator.validate_response(
        status_code=200,
        body=list_user_data,
        count=count,
    )

    assert issues.to_dict(msg=True) == {}


def test_pagination_info_validation_fails_if_start_index_is_missing_when_pagination(
    list_user_data, user_schema
):
    validator = ResourcesQuery(CONFIG, resource_schema=user_schema)
    list_user_data["Resources"] = list_user_data["Resources"][:1]
    list_user_data["itemsPerPage"] = 1
    list_user_data.pop("startIndex")
    expected = {"body": {"startIndex": {"_errors": [{"code": 5}]}}}

    issues = validator.validate_response(
        status_code=200,
        body=list_user_data,
        count=2,
    )

    assert issues.to_dict() == expected


def test_resources_get_response_validation_fails_if_mismatch_in_start_index(
    list_user_data, user_schema
):
    validator = ResourcesQuery(CONFIG, resource_schema=user_schema)
    list_user_data["startIndex"] = 3
    expected = {"body": {"startIndex": {"_errors": [{"code": 4}]}}}

    issues = validator.validate_response(
        status_code=200,
        body=list_user_data,
        start_index=2,
    )

    assert issues.to_dict() == expected


def test_pagination_info_validation_fails_if_items_per_page_is_missing_when_pagination(
    list_user_data, user_schema
):
    validator = ResourcesQuery(CONFIG, resource_schema=user_schema)
    list_user_data["Resources"] = list_user_data["Resources"][:1]
    list_user_data.pop("itemsPerPage")
    expected = {"body": {"itemsPerPage": {"_errors": [{"code": 5}]}}}

    issues = validator.validate_response(
        status_code=200,
        body=list_user_data,
        count=1,
    )

    assert issues.to_dict() == expected


def test_validate_pagination_info_validation_succeeds_when_if_data_for_pagination(
    list_user_data, user_schema
):
    validator = ResourcesQuery(CONFIG, resource_schema=user_schema)
    list_user_data["Resources"] = list_user_data["Resources"][:1]
    list_user_data["itemsPerPage"] = 1

    issues = validator.validate_response(
        status_code=200,
        body=list_user_data,
        count=2,
    )

    assert issues.to_dict(msg=True) == {}


@pytest.mark.parametrize(
    "filter_exp",
    (
        'emails[value eq "sven@example.com"]',
        'emails eq "sven@example.com"',
        'name.familyName eq "Sven"',
    ),
)
def test_validate_resources_filtered(filter_exp, list_user_data, user_schema):
    filter_ = Filter.deserialize(filter_exp)
    expected = {
        "body": {
            "Resources": {
                "0": {
                    "_errors": [
                        {
                            "code": 21,
                        }
                    ]
                }
            }
        }
    }
    validator = ResourcesQuery(CONFIG, resource_schema=user_schema)

    issues = validator.validate_response(
        status_code=200,
        body=list_user_data,
        filter=filter_,
    )

    assert issues.to_dict() == expected


@pytest.mark.parametrize(
    ("filter_exp", "presence_config"),
    (
        (
            'emails[value eq "sven@example.com"]',
            AttrValuePresenceConfig("RESPONSE", attr_reps=["emails.value"], include=False),
        ),
        (
            'emails eq "sven@example.com"',
            AttrValuePresenceConfig("RESPONSE", attr_reps=["emails.value"], include=False),
        ),
        (
            'name.familyName eq "Sven"',
            AttrValuePresenceConfig("RESPONSE", attr_reps=["name.familyName"], include=False),
        ),
    ),
)
def test_resources_are_not_validated_for_filtering_if_attrs_not_requested(
    filter_exp, list_user_data, user_schema, presence_config
):
    list_user_data = ScimData(list_user_data)
    for resource in list_user_data["Resources"]:
        resource.pop(presence_config.attr_reps[0])

    filter_ = Filter.deserialize(filter_exp)
    validator = ResourcesQuery(CONFIG, resource_schema=user_schema)

    issues = validator.validate_response(
        status_code=200,
        body=list_user_data,
        filter=filter_,
        presence_config=presence_config,
    )

    assert issues.to_dict() == {}


def test_resources_are_not_validated_according_to_filter_and_sorter_if_bad_schema(
    list_user_data, user_schema, group_schema
):
    list_user_data["Resources"].append({"schemas": ["complete:unknown:schema"]})
    list_user_data["totalResults"] = 3
    list_user_data["itemsPerPage"] = 3
    expected = {
        "body": {
            "Resources": {
                "2": {
                    "_errors": [
                        {
                            "code": 14,
                        }
                    ]
                }
            }
        }
    }
    validator = ResourcesQuery(CONFIG, resource_schema=[user_schema, group_schema])

    issues = validator.validate_response(
        status_code=200,
        body=list_user_data,
        filter=Filter.deserialize('name.familyName eq "Sven"'),
    )

    assert issues.to_dict() == expected


def test_validate_resources_filtered__case_sensitivity_matters(list_user_data, user_schema):
    filter_ = Filter.deserialize('meta.resourcetype eq "user"')  # "user", not "User"
    expected = {
        "body": {
            "Resources": {
                "0": {
                    "_errors": [
                        {
                            "code": 21,
                        }
                    ]
                },
                "1": {
                    "_errors": [
                        {
                            "code": 21,
                        }
                    ]
                },
            }
        }
    }
    validator = ResourcesQuery(CONFIG, resource_schema=user_schema)

    issues = validator.validate_response(
        status_code=200,
        body=list_user_data,
        filter=filter_,
    )

    assert issues.to_dict() == expected


def test_validate_resources_filtered__fields_from_schema_extensions_are_checked_by_filter(
    list_user_data, user_schema
):
    filter_ = Filter.deserialize(
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:manager.displayName "
        'eq "John Smith"'
    )
    expected = {
        "body": {
            "Resources": {
                "0": {
                    "_errors": [
                        {
                            "code": 21,
                        }
                    ]
                },
            }
        }
    }
    validator = ResourcesQuery(CONFIG, resource_schema=user_schema)

    issues = validator.validate_response(
        status_code=200,
        body=list_user_data,
        filter=filter_,
    )

    assert issues.to_dict() == expected


def test_validate_resources_sorted__not_sorted(list_user_data, user_schema):
    sorter = Sorter(AttrRep(attr="name", sub_attr="familyName"), asc=False)
    expected = {"body": {"Resources": {"_errors": [{"code": 22}]}}}

    validator = ResourcesQuery(CONFIG, resource_schema=user_schema)
    issues = validator.validate_response(
        status_code=200,
        sorter=sorter,
        body=list_user_data,
    )

    assert issues.to_dict() == expected


def test_validate_resources_sorting_not_validated_if_attr_excluded(list_user_data, user_schema):
    attr_rep = AttrRep(attr="name", sub_attr="familyName")
    list_user_data = ScimData(list_user_data)
    for resource in list_user_data["Resources"]:
        resource.pop(attr_rep)
    sorter = Sorter(attr_rep, asc=False)

    validator = ResourcesQuery(CONFIG, resource_schema=user_schema)
    issues = validator.validate_response(
        status_code=200,
        sorter=sorter,
        body=list_user_data,
        presence_config=AttrValuePresenceConfig("RESPONSE", attr_reps=[attr_rep], include=False),
    )

    assert issues.to_dict(msg=True) == {}


def test_validate_resources_sorted__not_sorted_by_extended_attr(list_user_data, user_schema):
    sorter = Sorter(
        BoundedAttrRep(
            schema="urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
            attr="manager",
            sub_attr="displayName",
        ),
        asc=False,
    )
    expected = {"body": {"Resources": {"_errors": [{"code": 22}]}}}

    validator = ResourcesQuery(CONFIG, resource_schema=user_schema)
    issues = validator.validate_response(
        status_code=200,
        sorter=sorter,
        body=list_user_data,
    )

    assert issues.to_dict() == expected


def test_correct_error_response_passes_validation(error_data):
    validator = Error()

    issues = validator.validate_response(status_code=400, body=error_data)

    assert issues.to_dict(msg=True) == {}


def test_error_status_consistency_is_not_validated_if_bad_status(error_data):
    validator = Error()
    error_data["status"] = "abc"
    expected_issues = {"body": {"status": {"_errors": [{"code": 1}]}}}

    issues = validator.validate_response(status_code=400, body=error_data)

    assert issues.to_dict() == expected_issues


def test_request_schema_in_error_validator_is_not_implemented():
    validator = Error()

    with pytest.raises(NotImplementedError):
        print(validator.request_schema)


def test_request_validation_in_error_validator_is_not_implemented():
    validator = Error()

    with pytest.raises(NotImplementedError):
        validator.validate_request()


def test_error_data_can_be_serialized(error_data):
    validator = Error()

    assert validator.response_schema.serialize(error_data) == error_data


def test_correct_resource_object_get_response_passes_validation(user_data_server, user_schema):
    validator = ResourceObjectGet(CONFIG, resource_schema=user_schema)
    user_data_server.pop("name")

    issues = validator.validate_response(
        status_code=200,
        body=user_data_server,
        headers={
            "Location": user_data_server["meta"]["location"],
            "ETag": user_data_server["meta"]["version"],
        },
        presence_config=AttrValuePresenceConfig(
            direction="RESPONSE",
            attr_reps=[AttrRep(attr="name")],
            include=False,
        ),
    )

    assert issues.to_dict(msg=True) == {}


def test_validation_failure_on_missing_etag_header_when_etag_supported(
    user_data_server, user_schema
):
    validator = ResourceObjectGet(CONFIG, resource_schema=user_schema)
    expected_issues = {"headers": {"ETag": {"_errors": [{"code": 5}]}}}

    issues = validator.validate_response(
        status_code=200,
        body=user_data_server,
        headers={
            "Location": user_data_server["meta"]["location"],
        },
    )

    assert issues.to_dict() == expected_issues


def test_validation_failure_on_missing_meta_version_when_etag_supported(
    user_data_server, user_schema
):
    validator = ResourceObjectGet(CONFIG, resource_schema=user_schema)
    user_data_server["meta"].pop("version")
    expected_issues = {"body": {"meta": {"version": {"_errors": [{"code": 5}]}}}}

    issues = validator.validate_response(
        status_code=200,
        body=user_data_server,
        headers={
            "Location": user_data_server["meta"]["location"],
            "ETag": 'W/"3694e05e9dff591"',
        },
    )

    assert issues.to_dict() == expected_issues


@pytest.mark.parametrize("etag_supported", (True, False))
def test_validation_failure_on_etag_and_meta_version_mismatch(
    etag_supported, user_data_server, user_schema
):
    config = deepcopy(CONFIG)
    config.etag.supported = etag_supported

    validator = ResourceObjectGet(config, resource_schema=user_schema)
    expected_issues = {
        "body": {"meta": {"version": {"_errors": [{"code": 8}]}}},
        "headers": {"ETag": {"_errors": [{"code": 8}]}},
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


def test_response_is_validated_without_tag_and_version_if_etag_not_supported(
    user_data_server, user_schema
):
    config = deepcopy(CONFIG)
    config.etag.supported = False
    validator = ResourceObjectGet(config, resource_schema=user_schema)
    user_data_server["meta"].pop("version")

    issues = validator.validate_response(
        status_code=200,
        body=user_data_server,
        headers={
            "Location": user_data_server["meta"]["location"],
        },
    )

    assert issues.to_dict(msg=True) == {}


def test_etag_and_version_are_not_compared_if_bad_version_value(user_data_server, user_schema):
    validator = ResourceObjectGet(CONFIG, resource_schema=user_schema)
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


def test_request_schema_in_resource_object_get_request_data_is_not_supported(user_schema):
    validator = ResourceObjectGet(CONFIG, resource_schema=user_schema)

    with pytest.raises(NotImplementedError):
        print(validator.request_schema)


def test_data_for_resource_object_get_response_can_be_serialized(user_data_server, user_schema):
    user_data_server["password"] = "1234"
    validator = ResourceObjectGet(CONFIG, resource_schema=user_schema)

    data = validator.response_schema.serialize(user_data_server)

    assert "password" not in data  # password has "return" attribute set to "NEVER"


def test_service_object_resource_get_request_is_not_validated():
    validator = ResourceObjectGet(CONFIG, resource_schema=ResourceTypeSchema())

    issues = validator.validate_request(body={"some": "weird_stuff"})

    assert issues.to_dict(msg=True) == {}


def test_validation_warning_for_missing_response_body_for_resources_post(user_schema):
    validator = ResourcesPost(CONFIG, resource_schema=user_schema)
    expected_issues = {"body": {"_warnings": [{"code": 4}]}}

    issues = validator.validate_response(
        status_code=201,
        body=None,
    )

    assert issues.to_dict() == expected_issues


def test_correct_resource_type_post_request_passes_validation(user_data_client, user_schema):
    validator = ResourcesPost(CONFIG, resource_schema=user_schema)

    issues = validator.validate_request(
        body=user_data_client,
    )

    assert issues.to_dict(msg=True) == {}


def test_resource_type_post_request_parsing_fails_for_incorrect_data_passes_validation(
    user_data_client, user_schema
):
    validator = ResourcesPost(CONFIG, resource_schema=user_schema)
    user_data_client["userName"] = 123
    expected_issues = {"body": {"userName": {"_errors": [{"code": 2}]}}}

    issues = validator.validate_request(
        body=user_data_client,
    )

    assert issues.to_dict() == expected_issues


def test_resources_post_response_validation_fails_if_different_created_and_last_modified(
    user_data_server, user_schema
):
    validator = ResourcesPost(CONFIG, resource_schema=user_schema)
    user_data_server["meta"]["lastModified"] = "2011-05-13T04:42:34Z"
    expected_issues = {"body": {"meta": {"lastModified": {"_errors": [{"code": 8}]}}}}

    issues = validator.validate_response(
        body=user_data_server,
        status_code=201,
        headers={
            "Location": user_data_server["meta"]["location"],
            "ETag": user_data_server["meta"]["version"],
        },
    )

    assert issues.to_dict() == expected_issues


def test_resources_post_response_validation_fails_if_missing_location_header(
    user_data_server, user_schema
):
    validator = ResourcesPost(CONFIG, resource_schema=user_schema)
    expected_issues = {"headers": {"Location": {"_errors": [{"code": 5}]}}}

    issues = validator.validate_response(
        body=user_data_server,
        status_code=201,
        headers={
            "ETag": user_data_server["meta"]["version"],
        },
    )

    assert issues.to_dict() == expected_issues


def test_correct_resource_object_put_request_passes_validation(user_data_client, user_schema):
    validator = ResourceObjectPut(CONFIG, resource_schema=user_schema)
    user_data_client["id"] = "anything"

    issues = validator.validate_request(
        body=user_data_client,
    )

    assert issues.to_dict(msg=True) == {}


def test_resource_object_put_request__fails_when_missing_required_field(
    user_data_client, user_schema
):
    validator = ResourceObjectPut(CONFIG, resource_schema=user_schema)
    # user_data_client misses 'id' and 'meta'
    expected_issues = {"body": {"id": {"_errors": [{"code": 5}]}}}

    issues = validator.validate_request(body=user_data_client)

    assert issues.to_dict() == expected_issues


def test_correct_resource_object_put_response_passes_validation(user_data_server, user_schema):
    validator = ResourceObjectPut(CONFIG, resource_schema=user_schema)

    issues = validator.validate_response(
        status_code=200,
        body=user_data_server,
        headers={
            "Location": user_data_server["meta"]["location"],
            "ETag": user_data_server["meta"]["version"],
        },
    )

    assert issues.to_dict(msg=True) == {}


def test_data_for_resource_object_put_request_can_be_deserialized(user_data_client, user_schema):
    validator = ResourceObjectPut(CONFIG, resource_schema=user_schema)

    data = validator.request_schema.deserialize(user_data_client)

    assert data.get("password") is not Missing
    assert data.get("groups") is Missing  # 'groups' are read-only, so ignored


def test_data_for_resource_object_put_response_can_be_serialized(user_data_server, user_schema):
    validator = ResourceObjectPut(CONFIG, resource_schema=user_schema)

    data = validator.response_schema.serialize(user_data_server)

    assert "password" not in data
    assert "groups" in data


def test_correct_resource_type_post_response_passes_validation(user_data_server, user_schema):
    validator = ResourcesPost(CONFIG, resource_schema=user_schema)

    issues = validator.validate_response(
        status_code=201,
        body=user_data_server,
        headers={
            "Location": user_data_server["meta"]["location"],
            "ETag": user_data_server["meta"]["version"],
        },
    )

    assert issues.to_dict(msg=True) == {}


def test_resource_type_post_request_data_can_be_deserialized(user_data_client, user_schema):
    user_data_client["id"] = "1234"
    validator = ResourcesPost(CONFIG, resource_schema=user_schema)

    data = validator.request_schema.deserialize(user_data_client)

    assert data.get("id") is Missing  # id is issued by the server
    assert data.get("groups") is Missing  # groups are read-only


def test_resource_type_post_response_data_can_be_serialized(user_data_server, user_schema):
    DateTime.set_serializer(datetime.isoformat)

    user_data_server["meta"]["created"] = datetime.fromisoformat(
        user_data_server["meta"]["created"]
    )
    user_data_server["meta"]["lastModified"] = datetime.fromisoformat(
        user_data_server["meta"]["lastModified"]
    )
    validator = ResourcesPost(CONFIG, resource_schema=user_schema)

    data = validator.response_schema.serialize(user_data_server)

    assert "id" in data
    assert "groups" in data
    assert "password" not in data
    assert data["meta"]["created"] == user_data_server["meta"]["created"].isoformat()
    assert data["meta"]["lastModified"] == user_data_server["meta"]["lastModified"].isoformat()

    DateTime.set_serializer(str)


@pytest.mark.parametrize(
    "validator_cls",
    (
        ResourcesQuery,
        SearchRequestPost,
    ),
)
def test_correct_list_response_passes_validation(validator_cls, list_user_data, user_schema):
    list_user_data["Resources"][0].pop("name")
    list_user_data["Resources"][1].pop("name")
    validator = validator_cls(resource_schema=user_schema)

    issues = validator.validate_response(
        status_code=200,
        body=list_user_data,
        start_index=1,
        count=2,
        filter_=Filter(Present(AttrRep(attr="username"))),
        sorter=Sorter(AttrRep(attr="userName"), True),
        presence_config=AttrValuePresenceConfig(
            direction="RESPONSE", attr_reps=[AttrRep(attr="name")], include=False
        ),
    )

    assert issues.to_dict(msg=True) == {}


@pytest.mark.parametrize(
    "validator_cls",
    (
        ResourcesQuery,
        SearchRequestPost,
    ),
)
def test_missing_version_in_list_response_resources_is_not_validated_if_etag_not_supported(
    validator_cls, list_user_data, user_schema
):
    list_user_data = ScimData(list_user_data)
    list_user_data["Resources"][0].pop("meta.version")
    list_user_data["Resources"][1].pop("meta.version")
    validator = validator_cls(
        ServiceProviderConfig.create(etag={"supported": False}), resource_schema=user_schema
    )

    issues = validator.validate_response(
        status_code=200,
        body=list_user_data,
    )

    assert issues.to_dict(msg=True) == {}


def test_resources_get_request_validation_does_nothing(list_user_data, user_schema):
    validator = ResourcesQuery(resource_schema=user_schema)

    issues = validator.validate_request(
        body={"what": "ever"},
    )

    assert issues.to_dict(msg=True) == {}


@pytest.mark.parametrize(
    "validator_cls",
    (
        ResourcesQuery,
        SearchRequestPost,
    ),
)
def test_missing_version_in_list_response_resources_is_validated_if_etag_supported(
    validator_cls, list_user_data, user_schema
):
    list_user_data = ScimData(list_user_data)
    list_user_data["Resources"][0].pop("meta.version")
    list_user_data["Resources"][1].pop("meta.version")
    validator = validator_cls(
        ServiceProviderConfig.create(etag={"supported": True}), resource_schema=user_schema
    )
    expected_issues = {
        "body": {
            "Resources": {
                "0": {"meta": {"version": {"_errors": [{"code": 5}]}}},
                "1": {"meta": {"version": {"_errors": [{"code": 5}]}}},
            }
        }
    }

    issues = validator.validate_response(
        status_code=200,
        body=list_user_data,
    )

    assert issues.to_dict() == expected_issues


@pytest.mark.parametrize(
    "validator_cls",
    (
        ResourcesQuery,
        SearchRequestPost,
    ),
)
def test_attributes_existence_is_validated_in_list_response(validator_cls, user_schema):
    expected_issues = {
        "body": {
            "schemas": {
                "_errors": [{"code": 5}],
            },
            "totalResults": {"_errors": [{"code": 5}]},
        }
    }
    validator = validator_cls(resource_schema=user_schema)

    issues = validator.validate_response(
        status_code=200,
        body={},
    )

    assert issues.to_dict() == expected_issues


@pytest.mark.parametrize(
    "validator_cls",
    (
        ResourcesQuery,
        SearchRequestPost,
    ),
)
def test_attributes_presence_is_validated_in_resources_in_list_response(validator_cls, user_schema):
    expected_issues = {
        "body": {
            "Resources": {
                "0": {
                    "id": {"_errors": [{"code": 5}]},
                    "schemas": {"_errors": [{"code": 5}]},
                    "userName": {"_errors": [{"code": 5}]},
                }
            },
        }
    }
    validator = validator_cls(resource_schema=user_schema)

    issues = validator.validate_response(
        status_code=200,
        body={
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
            "totalResults": 1,
            "Resources": [{}],
        },
    )

    assert issues.to_dict() == expected_issues


@pytest.mark.parametrize(
    "validator_cls",
    (
        ResourcesQuery,
        SearchRequestPost,
    ),
)
def test_start_index_consistency_is_not_validated_if_bad_type(
    validator_cls, list_user_data, user_schema
):
    list_user_data["startIndex"] = "9"
    expected_issues = {
        "body": {
            "startIndex": {"_errors": [{"code": 2}]},
        }
    }
    validator = validator_cls(resource_schema=user_schema)

    issues = validator.validate_response(
        status_code=200,
        body=list_user_data,
        start_index=10,
    )

    assert issues.to_dict() == expected_issues


@pytest.mark.parametrize(
    "validator_cls",
    (
        ResourcesQuery,
        SearchRequestPost,
    ),
)
def test_resources_are_not_validated_for_pagination_if_bad_type(
    validator_cls, list_user_data, user_schema
):
    expected_issues = {
        "body": {
            "Resources": {"_errors": [{"code": 2}]},
        }
    }
    list_user_data["Resources"] = {}
    validator = validator_cls(resource_schema=user_schema)

    issues = validator.validate_response(
        status_code=200,
        body=list_user_data,
        start_index=10,
    )

    assert issues.to_dict() == expected_issues


@pytest.mark.parametrize(
    "validator_cls",
    (
        ResourcesQuery,
        SearchRequestPost,
    ),
)
def test_resources_are_not_validated_for_filtering_and_sorting_if_one_of_resources_has_issues(
    validator_cls, list_user_data, user_schema
):
    list_user_data["Resources"].append(list_user_data["Resources"][0])
    list_user_data["Resources"][0]["id"] = "z"
    list_user_data["Resources"][1] = "abc"
    list_user_data["Resources"][2]["id"] = "a"
    list_user_data["itemsPerPage"] = 3
    list_user_data["totalResults"] = 3
    validator = validator_cls(resource_schema=user_schema)

    # no issue about resource with "z" id in body
    # no issue about bad sorting
    expected_issues = {
        "body": {
            "Resources": {"1": {"_errors": [{"code": 2}]}},
        }
    }

    issues = validator.validate_response(
        status_code=200,
        body=list_user_data,
        filter=Filter.deserialize("id eq 'a'"),
        sorter=Sorter(attr_rep=AttrRep(attr="id"), asc=True),
    )

    assert issues.to_dict() == expected_issues


@pytest.mark.parametrize(
    "validator_cls",
    (
        ResourcesQuery,
        SearchRequestPost,
    ),
)
def test_resources_response_data_can_be_serialized(validator_cls, list_user_data, user_schema):
    validator = validator_cls(resource_schema=user_schema)
    data = validator.response_schema.serialize(list_user_data)

    for resource in data["Resources"]:
        assert "password" not in resource


def test_correct_search_request_passes_validation(user_schema):
    validator = SearchRequestPost(CONFIG, resource_schema=[user_schema])

    issues = validator.validate_request(
        body={
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:SearchRequest"],
            "attributes": ["userName", "name"],
            "filter": 'userName eq "bjensen"',
            "sortBy": "name.familyName",
            "sortOrder": "descending",
            "startIndex": 2,
            "count": 10,
        }
    )

    assert issues.to_dict(msg=True) == {}


def test_search_request_validation_fails_if_attributes_and_excluded_attributes_provided(
    user_schema,
):
    validator = SearchRequestPost(CONFIG, resource_schema=[user_schema])
    expected_issues = {
        "body": {
            "attributes": {"_errors": [{"code": 11}]},
            "excludedAttributes": {"_errors": [{"code": 11}]},
        }
    }

    issues = validator.validate_request(
        body={
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:SearchRequest"],
            "attributes": ["userName"],
            "excludedAttributes": ["name"],
        }
    )

    assert issues.to_dict() == expected_issues


def test_correct_remove_operations_pass_validation(fake_schema):
    validator = ResourceObjectPatch(CONFIG, resource_schema=fake_schema)
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


@pytest.mark.parametrize("op", ("add", "replace"))
def test_correct_add_and_replace_operations_pass_validation(op, fake_schema):
    validator = ResourceObjectPatch(CONFIG, resource_schema=fake_schema)
    issues = validator.validate_request(
        body={
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "Operations": [
                {
                    "op": op,
                    "path": "str",
                    "value": "abc",
                },
                {
                    "op": op,
                    "path": "str_mv[value eq 'abc']",
                    "value": "def",
                },
                {
                    "op": op,
                    "path": "c2.int",
                    "value": 42,
                },
                {
                    "op": op,
                    "path": "c2_mv[int eq 1]",
                    "value": {
                        "str": "abc",
                        "int": 42,
                        "bool": True,
                    },
                },
                {
                    "op": op,
                    "path": "c2_mv[int eq 1].str",
                    "value": "def",
                },
            ],
        }
    )

    assert issues.to_dict(msg=True) == {}


def test_attr_value_presence_in_value_is_not_validated_if_bad_operations(fake_schema):
    validator = ResourceObjectPatch(CONFIG, resource_schema=fake_schema)
    expected_issues = {"body": {"Operations": {"0": {"path": {"_errors": [{"code": 17}]}}}}}

    issues = validator.validate_request(
        body={
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "Operations": [
                {
                    "op": "add",
                    "path": "totally bad path",
                    "value": "abc",
                },
            ],
        }
    )

    assert issues.to_dict() == expected_issues


def test_attr_value_presence_in_value_is_not_validated_if_bad_path(fake_schema):
    validator = ResourceObjectPatch(CONFIG, resource_schema=fake_schema)
    expected_issues = {"body": {"Operations": {"_errors": [{"code": 2}]}}}

    issues = validator.validate_request(
        body={
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "Operations": "123",
        }
    )

    assert issues.to_dict() == expected_issues


def test_resource_object_patch_request_data_can_be_deserialized(fake_schema):
    validator = ResourceObjectPatch(CONFIG, resource_schema=fake_schema)
    data = validator.request_schema.deserialize(
        {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "Operations": [
                {
                    "op": "add",
                    "path": "str",
                    "value": "abc",
                },
                {
                    "op": "replace",
                    "path": "str_mv[value eq 'abc']",
                    "value": "def",
                },
                {
                    "op": "remove",
                    "path": "c2_mv[int eq 1].str",
                    "value": "def",
                },
            ],
        }
    )

    assert isinstance(data.get("Operations")[0].get("path"), PatchPath)
    assert isinstance(data.get("Operations")[1].get("path"), PatchPath)
    assert isinstance(data.get("Operations")[2].get("path"), PatchPath)
    assert data.get("Operations")[2].get("value") is Missing


def test_resource_object_patch_response_validation_fails_if_204_but_attributes_requested(
    user_schema,
):
    validator = ResourceObjectPatch(CONFIG, resource_schema=user_schema)

    issues = validator.validate_response(
        status_code=204,
        body=None,
        presence_config=AttrValuePresenceConfig(
            direction="RESPONSE", attr_reps=[AttrRep(attr="userName")], include=True
        ),
    )

    assert issues.to_dict() == {"status": {"_errors": [{"code": 19}]}}


def test_resource_object_patch_response_validation_succeeds_if_204_and_no_attributes_requested(
    user_schema,
):
    validator = ResourceObjectPatch(CONFIG, resource_schema=user_schema)

    issues = validator.validate_response(
        status_code=204,
        body=None,
        presence_config=None,
    )

    assert issues.to_dict(msg=True) == {}


def test_resource_object_patch_response_validation_succeeds_if_200_and_user_data(
    user_data_server, user_schema
):
    validator = ResourceObjectPatch(CONFIG, resource_schema=user_schema)

    issues = validator.validate_response(
        status_code=200,
        body=user_data_server,
        presence_config=None,
        headers={"ETag": user_data_server["meta"]["version"]},
    )

    assert issues.to_dict(msg=True) == {}


def test_resource_object_patch_response_validation_succeeds_if_200_and_selected_attributes(
    user_data_server, user_schema
):
    validator = ResourceObjectPatch(CONFIG, resource_schema=user_schema)

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
        presence_config=AttrValuePresenceConfig(
            direction="RESPONSE", attr_reps=[AttrRep(attr="userName")], include=True
        ),
        headers={"ETag": 'W/"3694e05e9dff591"'},
    )

    assert issues.to_dict(msg=True) == {}


def test_runtime_error_is_raised_if_patch_not_supported_and_resource_object_patch_object_created(
    user_schema,
):
    with pytest.raises(RuntimeError):
        ResourceObjectPatch(
            config=ServiceProviderConfig.create(patch={"supported": False}),
            resource_schema=user_schema,
        )


def test_resource_object_delete_response_validation_fails_if_status_different_than_204():
    validator = ResourceObjectDelete(CONFIG)

    issues = validator.validate_response(status_code=200)

    assert issues.to_dict() == {"status": {"_errors": [{"code": 19}]}}


def test_resource_object_delete_response_validation_succeeds_if_status_204():
    validator = ResourceObjectDelete(CONFIG)

    issues = validator.validate_response(status_code=204)

    assert issues.to_dict(msg=True) == {}


def test_resource_object_delete_request_validation_does_nothing():
    validator = ResourceObjectDelete(CONFIG)

    issues = validator.validate_request()

    assert issues.to_dict(msg=True) == {}


def test_not_implemented_error_is_raised_if_accessing_response_schema_for_delete():
    validator = ResourceObjectDelete(CONFIG)

    with pytest.raises(NotImplementedError):
        print(validator.response_schema)


def test_runtime_error_is_raised_if_bulk_ops_not_supported_and_bulk_operations_instance_created(
    user_schema,
):
    with pytest.raises(RuntimeError):
        BulkOperations(
            config=ServiceProviderConfig.create(bulk={"supported": False}),
            resource_schemas=[user_schema],
        )


def test_bulk_operations_data_not_validated_if_bad_operations_type(user_schema):
    validator = BulkOperations(CONFIG, resource_schemas=[user_schema])
    expected_issues = {"body": {"Operations": {"_errors": [{"code": 2}]}}}

    data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:BulkRequest"],
        "failOnErrors": 1,
        "Operations": "abc",
    }

    issues = validator.validate_request(body=data)

    assert issues.to_dict() == expected_issues


def test_bulk_operations_data_not_validated_if_bad_path_or_method(user_schema):
    validator = BulkOperations(CONFIG, resource_schemas=[user_schema])
    expected_issues = {
        "body": {
            "Operations": {
                "0": {"path": {"_errors": [{"code": 1}]}},
                "1": {"method": {"_errors": [{"code": 9}]}},
            }
        }
    }
    data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:BulkRequest"],
        "failOnErrors": 1,
        "Operations": [
            {
                "method": "POST",
                "path": "123",
                "bulkId": "qwerty",
                "data": {},
            },
            {
                "method": "CREATE",
                "path": "/Users",
                "bulkId": "qwerty",
                "data": {},
            },
        ],
    }

    issues = validator.validate_request(body=data)

    assert issues.to_dict() == expected_issues


def test_bulk_operations_data_not_validated_if_bad_resource_name(user_schema):
    validator = BulkOperations(CONFIG, resource_schemas=[user_schema])
    expected_issues = {"body": {"Operations": {"0": {"path": {"_errors": [{"code": 25}]}}}}}
    data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:BulkRequest"],
        "failOnErrors": 1,
        "Operations": [
            {
                "method": "POST",
                "path": "/SuperUsers",
                "bulkId": "qwerty",
                "data": {},
            },
        ],
    }

    issues = validator.validate_request(body=data)

    assert issues.to_dict() == expected_issues


def test_bulk_operations_request_is_valid_if_correct_data(
    bulk_request_serialized, bulk_request_deserialized, user_schema
) -> None:
    validator = BulkOperations(CONFIG, resource_schemas=[user_schema])

    issues = validator.validate_request(body=bulk_request_serialized)

    assert issues.to_dict(msg=True) == {}


def test_bulk_operations_request_validation_fails_for_bad_data(user_schema):
    validator = BulkOperations(
        config=ServiceProviderConfig.create(
            patch={"supported": True},
            bulk={"max_operations": 2, "max_payload_size": 1024, "supported": True},
        ),
        resource_schemas=[user_schema],
    )
    expected_issues = {
        "body": {
            "Operations": {
                "_errors": [{"code": 26}],
                "0": {
                    "data": {
                        "userName": {"_errors": [{"code": 5}]},
                        "nickName": {"_errors": [{"code": 2}]},
                    }
                },
                "1": {
                    "data": {
                        "schemas": {"_errors": [{"code": 5}]},
                        "userName": {"_errors": [{"code": 2}]},
                    }
                },
                "2": {
                    "version": {"_errors": [{"code": 2}]},
                    "data": {
                        "Operations": {
                            "0": {"path": {"_errors": [{"code": 17}]}},
                            "1": {"op": {"_errors": [{"code": 9}]}},
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


def test_bulk_operations_response_is_valid_if_correct_data(user_data_server, user_schema):
    validator = BulkOperations(CONFIG, resource_schemas=[user_schema])

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

    assert validator.response_schema.serialize(data)


def test_bulk_operations_response_validation_fails_for_incorrect_data(
    user_data_server, user_schema
):
    validator = BulkOperations(CONFIG, resource_schemas=[user_schema])

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
                    "location": {"_errors": [{"code": 8}]},
                    "response": {
                        "id": {"_errors": [{"code": 5}]},
                        "meta": {"location": {"_errors": [{"code": 8}]}},
                        "userName": {"_errors": [{"code": 2}]},
                    },
                },
                "1": {
                    "version": {"_errors": [{"code": 8}]},
                    "response": {"meta": {"version": {"_errors": [{"code": 8}]}}},
                },
                "2": {
                    "method": {"_errors": [{"code": 9}]},
                },
                "3": {"location": {"_errors": [{"code": 25}]}},
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


def test_bulk_operations_response_operations_not_validated_further_if_bad_type(
    user_data_server, user_schema
):
    validator = BulkOperations(CONFIG, resource_schemas=[user_schema])
    expected_issues = {"body": {"Operations": {"_errors": [{"code": 2}]}}}
    data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:BulkResponse"],
        "Operations": "123",
    }

    issues = validator.validate_response(body=data, status_code=200, fail_on_errors=2)

    assert issues.to_dict() == expected_issues


def test_bulk_operations_responses_are_not_validated_if_bad_location_or_method(user_schema):
    validator = BulkOperations(CONFIG, resource_schemas=[user_schema])
    expected_issues = {
        "body": {
            "Operations": {
                "0": {"method": {"_errors": [{"code": 9}]}},
                "1": {"location": {"_errors": [{"code": 25}]}},
            }
        }
    }

    data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:BulkResponse"],
        "Operations": [
            {
                "location": "https://example.com/v2/Users/92b725cd-9465-4e7d-8c16-01f8e146b87a",
                "method": "CREATE",
                "bulkId": "qwerty",
                "version": 'W/"oY4m4wn58tkVjJxK"',
                "response": {"dummy": "whatever"},
                "status": "201",
            },
            {
                "location": (
                    "https://example.com/v2/SuperUsers/b7c14771-226c-4d05-8860-134711653041"
                ),
                "method": "PUT",
                "version": 'W/"huJj29dMNgu3WXPD"',
                "response": {"dummy": "whatever"},
                "status": "200",
            },
        ],
    }

    issues = validator.validate_response(body=data, status_code=200)

    assert issues.to_dict() == expected_issues


def test_bulk_operations_response_validation_fails_if_too_many_failed_operations(
    user_data_server, user_schema
):
    validator = BulkOperations(CONFIG, resource_schemas=[user_schema])

    expected_issues = {
        "body": {
            "Operations": {
                "_errors": [{"code": 27}],
                "0": {"status": {"_errors": [{"code": 5}]}},
                "1": {"status": {"_errors": [{"code": 5}]}},
            }
        }
    }

    data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:BulkResponse"],
        "Operations": [
            {
                "method": "POST",
                "bulkId": "qwerty",
                "response": {
                    "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
                    "scimType": "invalidSyntax",
                    "detail": "Request is unparsable, syntactically incorrect, or violates schema.",
                    "status": "400",
                },
            },
            {
                "method": "POST",
                "bulkId": "qwerty",
                "response": {
                    "scimType": "invalidSyntax",
                    "detail": "Request is unparsable, syntactically incorrect, or violates schema.",
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
    validator = ResourceObjectGet(
        CONFIG, resource_schema=service_provider_config.ServiceProviderConfigSchema()
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


def test_group_output_is_validated_correctly(group_data_server, group_schema):
    validator = ResourceObjectGet(CONFIG, resource_schema=group_schema)

    issues = validator.validate_response(
        status_code=200,
        body=group_data_server,
        headers={
            "Location": group_data_server["meta"]["location"],
            "ETag": group_data_server["meta"]["version"],
        },
    )

    assert issues.to_dict(msg=True) == {}


def test_schemas_output_can_be_validated(user_schema, group_schema):
    schema = SchemaDefinitionSchema()
    validator = ResourcesQuery(CONFIG, resource_schema=schema)
    body = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "totalResults": 2,
        "itemsPerPage": 2,
        "startIndex": 1,
        "Resources": [schema.get_repr(user_schema), schema.get_repr(group_schema)],
    }

    issues = validator.validate_response(status_code=200, body=body)

    assert issues.to_dict(msg=True) == {}


def test_schema_response_can_be_validated(user_schema):
    schema = SchemaDefinitionSchema()
    validator = ResourceObjectGet(CONFIG, resource_schema=schema)

    issues = validator.validate_response(
        status_code=200,
        body=schema.get_repr(user_schema, version='W/"3694e05e9dff591"'),
        headers={
            "ETag": 'W/"3694e05e9dff591"',
        },
    )

    assert issues.to_dict(msg=True) == {}


def test_resource_type_response_can_be_validated():
    validator = ResourceObjectGet(CONFIG, resource_schema=ResourceTypeSchema())
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
    validator = ResourcesQuery(CONFIG, resource_schema=ResourceTypeSchema())
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


@pytest.mark.parametrize(
    ("filter_", "checker", "expected"),
    (
        (
            Filter.deserialize("userName pr"),
            AttrValuePresenceConfig(
                direction="RESPONSE", attr_reps=[AttrRep(attr="userName")], include=True
            ),
            True,
        ),
        (
            Filter.deserialize("userName pr"),
            AttrValuePresenceConfig(
                direction="RESPONSE", attr_reps=[AttrRep(attr="name")], include=True
            ),
            False,
        ),
        (
            Filter.deserialize("userName pr and name.formatted pr"),
            AttrValuePresenceConfig(
                direction="RESPONSE",
                attr_reps=[AttrRep(attr="userName"), AttrRep(attr="name")],
                include=True,
            ),
            True,
        ),
        (
            Filter.deserialize("userName pr and name.formatted pr"),
            AttrValuePresenceConfig(
                direction="RESPONSE", attr_reps=[AttrRep(attr="name")], include=True
            ),
            False,
        ),
        (
            Filter.deserialize("name.formatted pr"),
            AttrValuePresenceConfig(
                direction="RESPONSE", attr_reps=[AttrRep(attr="name")], include=True
            ),
            True,
        ),
        (
            Filter.deserialize("name pr"),
            AttrValuePresenceConfig(
                direction="RESPONSE",
                attr_reps=[AttrRep(attr="name", sub_attr="display")],
                include=True,
            ),
            True,
        ),
        (
            Filter.deserialize("userName pr"),
            AttrValuePresenceConfig(
                direction="RESPONSE", attr_reps=[AttrRep(attr="userName")], include=False
            ),
            False,
        ),
        (
            Filter.deserialize("userName pr"),
            AttrValuePresenceConfig(
                direction="RESPONSE", attr_reps=[AttrRep(attr="name")], include=False
            ),
            True,
        ),
        (
            Filter.deserialize("userName pr and name.formatted pr"),
            AttrValuePresenceConfig(
                direction="RESPONSE",
                attr_reps=[AttrRep(attr="userName"), AttrRep(attr="name")],
                include=False,
            ),
            False,
        ),
        (
            Filter.deserialize("userName pr and name.formatted pr"),
            AttrValuePresenceConfig(
                direction="RESPONSE", attr_reps=[AttrRep(attr="name")], include=False
            ),
            False,
        ),
        (
            Filter.deserialize("name.formatted pr"),
            AttrValuePresenceConfig(
                direction="RESPONSE", attr_reps=[AttrRep(attr="name")], include=False
            ),
            False,
        ),
        (
            Filter.deserialize("name pr"),
            AttrValuePresenceConfig(
                direction="RESPONSE",
                attr_reps=[AttrRep(attr="name", sub_attr="display")],
                include=False,
            ),
            True,
        ),
        (
            Filter.deserialize("name pr and unknown pr"),
            AttrValuePresenceConfig(
                direction="RESPONSE",
                attr_reps=[AttrRep(attr="name", sub_attr="display")],
                include=True,
            ),
            False,
        ),
        (
            Filter.deserialize("name pr and unknown pr"),
            AttrValuePresenceConfig(
                direction="RESPONSE",
                attr_reps=[AttrRep(attr="name", sub_attr="display")],
                include=False,
            ),
            True,
        ),
        (
            Filter.deserialize("addresses eq 'Krakow'"),  # 'addresses' has no 'value'
            AttrValuePresenceConfig(direction="RESPONSE"),
            True,
        ),
        (
            Filter.deserialize("emails eq 'user@example.com'"),  # 'emails' has 'value'
            AttrValuePresenceConfig(
                direction="RESPONSE", attr_reps=["emails.value"], include=False
            ),
            False,
        ),
    ),
)
def test_can_validate_filtering(filter_, checker, expected, user_schema):
    assert can_validate_filtering(filter_, checker, user_schema) is expected


def test_can_validate_filtering_with_bounded_attributes(user_schema):
    assert can_validate_filtering(
        filter_=Filter.deserialize("urn:ietf:params:scim:schemas:core:2.0:User:name pr"),
        presence_config=AttrValuePresenceConfig(
            direction="RESPONSE",
            attr_reps=[
                BoundedAttrRep(
                    schema="urn:ietf:params:scim:schemas:core:2.0:User",
                    attr="name",
                    sub_attr="formatted",
                )
            ],
            include=True,
        ),
        schema=user_schema,
    )

    assert not can_validate_filtering(
        filter_=Filter.deserialize(
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:nonExisting pr"
        ),
        presence_config=AttrValuePresenceConfig(
            direction="RESPONSE",
            attr_reps=[
                BoundedAttrRep(
                    schema="urn:ietf:params:scim:schemas:core:2.0:User",
                    attr="nonExisting",
                    sub_attr="formatted",
                )
            ],
            include=True,
        ),
        schema=user_schema,
    )


@pytest.mark.parametrize(
    ("sorter", "checker", "expected"),
    (
        (
            Sorter(attr_rep=AttrRep(attr="userName")),
            AttrValuePresenceConfig(
                direction="RESPONSE", attr_reps=[AttrRep(attr="userName")], include=True
            ),
            True,
        ),
        (
            Sorter(attr_rep=AttrRep(attr="userName")),
            AttrValuePresenceConfig(
                direction="RESPONSE", attr_reps=[AttrRep(attr="name")], include=True
            ),
            False,
        ),
        (
            Sorter(attr_rep=AttrRep(attr="name", sub_attr="formatted")),
            AttrValuePresenceConfig(
                direction="RESPONSE", attr_reps=[AttrRep(attr="name")], include=True
            ),
            True,
        ),
        (
            Sorter(attr_rep=AttrRep(attr="name")),
            AttrValuePresenceConfig(
                direction="RESPONSE",
                attr_reps=[AttrRep(attr="name", sub_attr="formatted")],
                include=True,
            ),
            True,
        ),
        (
            Sorter(attr_rep=AttrRep(attr="userName")),
            AttrValuePresenceConfig(
                direction="RESPONSE", attr_reps=[AttrRep(attr="userName")], include=False
            ),
            False,
        ),
        (
            Sorter(attr_rep=AttrRep(attr="userName")),
            AttrValuePresenceConfig(
                direction="RESPONSE", attr_reps=[AttrRep(attr="name")], include=False
            ),
            True,
        ),
        (
            Sorter(attr_rep=AttrRep(attr="name", sub_attr="formatted")),
            AttrValuePresenceConfig(
                direction="RESPONSE", attr_reps=[AttrRep(attr="name")], include=False
            ),
            False,
        ),
        (
            Sorter(attr_rep=AttrRep(attr="name")),
            AttrValuePresenceConfig(
                direction="RESPONSE",
                attr_reps=[AttrRep(attr="name", sub_attr="formatted")],
                include=False,
            ),
            True,
        ),
        (
            Sorter(attr_rep=AttrRep(attr="emails")),
            AttrValuePresenceConfig(
                direction="RESPONSE",
                attr_reps=[AttrRep(attr="emails", sub_attr="type")],
                include=False,
            ),
            True,
        ),
        (
            Sorter(attr_rep=AttrRep(attr="emails")),
            AttrValuePresenceConfig(
                direction="RESPONSE",
                attr_reps=[AttrRep(attr="emails", sub_attr="value")],
                include=False,
            ),
            False,
        ),
        (
            Sorter(attr_rep=AttrRep(attr="emails")),
            AttrValuePresenceConfig(
                direction="RESPONSE",
                attr_reps=[AttrRep(attr="emails", sub_attr="value")],
                include=True,
            ),
            False,  # primary excluded
        ),
        (
            Sorter(attr_rep=AttrRep(attr="emails")),
            AttrValuePresenceConfig(
                direction="RESPONSE",
                attr_reps=[
                    AttrRep(attr="emails", sub_attr="value"),
                    AttrRep(attr="emails", sub_attr="primary"),
                ],
                include=True,
            ),
            True,
        ),
        (
            Sorter(attr_rep=AttrRep(attr="unknown")),
            AttrValuePresenceConfig(direction="RESPONSE"),
            True,
        ),
        (
            Sorter(attr_rep=AttrRep(attr="addresses")),  # 'addresses' has no 'value'
            AttrValuePresenceConfig(direction="RESPONSE"),
            True,
        ),
        (
            Sorter(attr_rep=AttrRep(attr="groups")),  # 'groups' has 'value', but no 'primary'
            AttrValuePresenceConfig(direction="RESPONSE"),
            True,
        ),
    ),
)
def test_can_validate_sorting(sorter, checker, expected, user_schema):
    assert can_validate_sorting(sorter, checker, user_schema) == expected


def test_bulk_request_with_bulk_ids_is_validated(user_schema, group_schema):
    validator = BulkOperations(CONFIG, resource_schemas=[user_schema, group_schema])
    data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:BulkRequest"],
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
                "method": "POST",
                "path": "/Groups",
                "bulkId": "ytrewq",
                "data": {
                    "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"],
                    "displayName": "Tour Guides",
                    "members": [{"type": "User", "value": "bulkId:qwerty"}],
                },
            },
        ],
    }

    issues = validator.validate_request(body=data)

    assert issues.to_dict(msg=True) == {}


@pytest.mark.parametrize(
    ("operation_data", "operation_issues"),
    (
        (
            {
                "method": "UNKNOWN_METHOD",
                "path": "/Users",
                "bulkId": "qwerty",
                "data": {
                    "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
                    "userName": "Alice",
                },
            },
            {"method": {"_errors": [{"code": 9}]}},
        ),
        (
            {
                "method": "POST",
                "path": "bad^path",
                "bulkId": "qwerty",
                "data": {
                    "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
                    "userName": "Alice",
                },
            },
            {"path": {"_errors": [{"code": 1}]}},
        ),
        (
            {
                "method": "POST",
                "path": "/Users",
                "bulkId": "qwerty",
                "data": 42,
            },
            {"data": {"_errors": [{"code": 2}]}},
        ),
        (
            {
                "method": "DELETE",
                "path": "/Users/123",
                "bulkId": "qwerty",
                "data": {"what": "ever"},
            },
            {},
        ),
    ),
)
def test_request_data_validation_in_bulk_request_is_skipped(
    user_schema, group_schema, operation_data, operation_issues
):
    validator = BulkOperations(resource_schemas=[user_schema, group_schema])
    expected_issues = {"body": {"Operations": {"0": operation_issues}}} if operation_issues else {}
    data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:BulkRequest"],
        "Operations": [
            operation_data,
        ],
    }

    issues = validator.validate_request(body=data)

    assert issues.to_dict() == expected_issues
