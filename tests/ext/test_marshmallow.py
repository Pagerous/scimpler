from copy import deepcopy
from datetime import datetime

import marshmallow
import pytest

import scimpler.data
import scimpler.ext.marshmallow
from scimpler.data import Integer, ResourceSchema, SchemaExtension
from scimpler.data.filter import Filter
from scimpler.data.identifiers import AttrRep
from scimpler.data.patch_path import PatchPath
from scimpler.data.scim_data import ScimData
from scimpler.ext.marshmallow import (
    ResponseContext,
    create_request_schema,
    create_response_schema,
    initialize,
)
from scimpler.validator import (
    BulkOperations,
    ResourceObjectGet,
    ResourceObjectPatch,
    ResourcesQuery,
    SearchRequestPost,
)


@pytest.fixture(autouse=True)
def reset_marshmallow():
    mapping_before = scimpler.ext.marshmallow._marshmallow_field_by_attr_type.copy()  # noqa
    yield
    scimpler.ext.marshmallow._initialized = False
    scimpler.ext.marshmallow._auto_initialized = False
    scimpler.ext.marshmallow._marshmallow_field_by_attr_type = mapping_before


@pytest.fixture
def list_data_deserialized(list_data):
    list_data = deepcopy(list_data)
    for resource in list_data["Resources"]:
        resource["meta"]["created"] = datetime.fromisoformat(resource["meta"]["created"])
        resource["meta"]["lastModified"] = datetime.fromisoformat(resource["meta"]["lastModified"])
    return ScimData(list_data)


@pytest.fixture
def list_user_data_deserialized(list_user_data):
    list_user_data = deepcopy(list_user_data)
    for resource in list_user_data["Resources"]:
        resource["meta"]["created"] = datetime.fromisoformat(resource["meta"]["created"])
        resource["meta"]["lastModified"] = datetime.fromisoformat(resource["meta"]["lastModified"])
    return ScimData(list_user_data)


@pytest.fixture
def user_deserialized(user_data_server):
    user_data_server = deepcopy(user_data_server)
    user_data_server["meta"]["created"] = datetime.fromisoformat(
        user_data_server["meta"]["created"]
    )
    user_data_server["meta"]["lastModified"] = datetime.fromisoformat(
        user_data_server["meta"]["lastModified"]
    )
    return ScimData(user_data_server)


@pytest.fixture
def group_deserialized(group_data_server):
    group_data_server = deepcopy(group_data_server)
    group_data_server["meta"]["created"] = datetime.fromisoformat(
        group_data_server["meta"]["created"]
    )
    group_data_server["meta"]["lastModified"] = datetime.fromisoformat(
        group_data_server["meta"]["lastModified"]
    )
    return group_data_server


def get_bulk_data(user_1, user_2, group):
    return {
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
                "location": "https://example.com/v2/Groups/e9e30dba-f08f-4109-8486-d5c6a331660a",
                "method": "PATCH",
                "version": 'W/"3694e05e9dff594"',
                "response": group,
                "status": "200",
            },
            {
                "location": "https://example.com/v2/Groups/e9e30dba-f08f-4109-8486-d5c6a331660a",
                "method": "PATCH",
                "version": 'W/"3694e05e9dff594"',
                "status": "200",
            },
        ],
    }


@pytest.fixture
def bulk_response_deserialized(user_deserialized, group_deserialized):
    user_1 = deepcopy(user_deserialized)
    user_1.set("id", "92b725cd-9465-4e7d-8c16-01f8e146b87a")
    user_1.set("meta.location", "https://example.com/v2/Users/92b725cd-9465-4e7d-8c16-01f8e146b87a")
    user_1.set("meta.version", 'W/"oY4m4wn58tkVjJxK"')

    user_2 = deepcopy(user_deserialized)
    user_2.set("id", "b7c14771-226c-4d05-8860-134711653041")
    user_2.set("meta.location", "https://example.com/v2/Users/b7c14771-226c-4d05-8860-134711653041")
    user_2.set("meta.version", 'W/"huJj29dMNgu3WXPD"')
    return ScimData(get_bulk_data(user_1, user_2, group_deserialized))


@pytest.fixture
def bulk_response_serialized(user_data_server, group_data_server):
    user_1 = deepcopy(user_data_server)
    user_1["id"] = "92b725cd-9465-4e7d-8c16-01f8e146b87a"
    user_1["meta"]["location"] = "https://example.com/v2/Users/92b725cd-9465-4e7d-8c16-01f8e146b87a"
    user_1["meta"]["version"] = 'W/"oY4m4wn58tkVjJxK"'

    user_2 = deepcopy(user_data_server)
    user_2["id"] = "b7c14771-226c-4d05-8860-134711653041"
    user_2["meta"]["location"] = "https://example.com/v2/Users/b7c14771-226c-4d05-8860-134711653041"
    user_2["meta"]["version"] = 'W/"huJj29dMNgu3WXPD"'
    return get_bulk_data(user_1, user_2, group_data_server)


@pytest.fixture
def user_patch_serialized():
    return {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [
            {
                "op": "add",
                "path": "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:manager",
                "value": {"$ref": "/Users/10", "value": "10"},
            },
            {
                "op": "replace",
                "path": "emails[value ew '.com']",
                "value": {"type": "home"},
            },
            {
                "op": "replace",
                "value": {
                    "nickName": "SuperSonic",
                },
            },
            {
                "op": "add",
                "path": "emails",
                "value": [
                    {"type": "home", "value": "example@domain.pl"},
                    {"type": "work", "value": "example@domain.eu"},
                ],
            },
            {
                "op": "replace",
                "path": "name.formatted",
                "value": "John Doe",
            },
        ],
    }


@pytest.fixture
def search_request_serialized():
    return {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:SearchRequest"],
        "attributes": ["userName", "name.formatted", "emails"],
        "filter": "userName sw 'a'",
        "sortBy": "nickName",
        "sortOrder": "descending",
        "startIndex": 10,
        "count": 20,
    }


@pytest.fixture
def search_request_deserialized():
    return ScimData(
        {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:SearchRequest"],
            "attributes": [
                AttrRep(attr="userName"),
                AttrRep(attr="name", sub_attr="formatted"),
                AttrRep(attr="emails"),
            ],
            "filter": Filter.deserialize("userName sw 'a'"),
            "sortBy": AttrRep(attr="nickName"),
            "sortOrder": "descending",
            "startIndex": 10,
            "count": 20,
        }
    )


@pytest.fixture
def user_patch_deserialized(user_patch_serialized: dict):
    deserialized: dict = deepcopy(user_patch_serialized)
    deserialized["Operations"][0]["path"] = PatchPath.deserialize(
        deserialized["Operations"][0]["path"]
    )
    deserialized["Operations"][1]["path"] = PatchPath.deserialize(
        deserialized["Operations"][1]["path"]
    )
    deserialized["Operations"][3]["path"] = PatchPath.deserialize(
        deserialized["Operations"][3]["path"]
    )
    deserialized["Operations"][4]["path"] = PatchPath.deserialize(
        deserialized["Operations"][4]["path"]
    )
    return ScimData(deserialized)


def test_user_response_can_be_dumped(user_deserialized, user_data_server, user_schema):
    initialize()
    validator = ResourceObjectGet(resource_schema=user_schema)
    schema_cls = create_response_schema(validator)

    dumped = schema_cls().dump(user_deserialized)

    assert dumped == user_data_server


def test_user_response_can_be_loaded(user_deserialized, user_data_server, user_schema):
    initialize()
    validator = ResourceObjectGet(resource_schema=user_schema)
    schema_cls = create_response_schema(
        validator,
        lambda: ResponseContext(status_code=200, headers={"ETag": r'W/"3694e05e9dff591"'}),
    )

    loaded = schema_cls().load(user_data_server)

    assert loaded == user_deserialized


def test_attr_names_are_case_insensitive_when_loading_data(
    user_deserialized, user_data_server, user_schema
):
    initialize()
    validator = ResourceObjectGet(resource_schema=user_schema)
    schema_cls = create_response_schema(
        validator,
        lambda: ResponseContext(status_code=200, headers={"ETag": r'W/"3694e05e9dff591"'}),
    )
    user_data_server["sChEmAs"] = user_data_server.pop("schemas")
    user_data_server["name"]["FORMATTED"] = user_data_server["name"].pop("formatted")

    loaded = schema_cls().load(user_data_server)

    assert loaded == user_deserialized


def test_user_response_loading_fails_if_validation_error(user_data_server, user_schema):
    initialize()
    user_data_server["id"] = 123
    validator = ResourceObjectGet(resource_schema=user_schema)
    schema_cls = create_response_schema(
        validator,
        lambda: ResponseContext(status_code=200, headers={"ETag": r'W/"3694e05e9dff591"'}),
    )

    with pytest.raises(marshmallow.ValidationError, match="bad type, expecting 'string'"):
        schema_cls().load(user_data_server)


def test_user_response_can_be_validated(user_data_server, user_schema):
    initialize()
    user_data_server["id"] = 123
    validator = ResourceObjectGet(resource_schema=user_schema)
    schema_cls = create_response_schema(
        validator,
        lambda: ResponseContext(status_code=200, headers={"ETag": r'W/"3694e05e9dff591"'}),
    )

    issues = schema_cls().validate(user_data_server)

    assert issues == {"body": {"id": ["bad type, expecting 'string'"]}}


def test_response_with_extension_that_have_uri_without_dots_can_be_loaded():
    initialize()

    class NiceResource(ResourceSchema):
        schema = "nice:resource:schema"
        name = "Nice"
        endpoint = "/NiceResources"
        base_attrs = [Integer("number")]

    class NiceExtension(SchemaExtension):
        schema = "nice_extension"
        name = "NiceExtension"
        base_attrs = [Integer("extended_number")]

    nice = NiceResource()
    nice.extend(NiceExtension(), required=False)
    validator = ResourceObjectGet(resource_schema=nice)
    schema_cls = create_response_schema(
        validator,
        lambda: ResponseContext(status_code=200, headers={"ETag": 'W/"3694e05e9dff591"'}),
    )
    data = {
        "schemas": ["nice:resource:schema", "nice_extension"],
        "id": "42",
        "number": 1,
        "nice_extension": {
            "extended_number": 2,
        },
        "meta": {"version": 'W/"3694e05e9dff591"'},
    }

    loaded = schema_cls().load(data)

    assert loaded == data


def test_list_response_with_many_resource_schemas_can_be_dumped(
    list_data, list_data_deserialized, user_schema, group_schema
):
    initialize()
    validator = ResourcesQuery(resource_schema=[user_schema, group_schema])
    schema_cls = create_response_schema(validator)

    dumped = schema_cls().dump(list_data_deserialized)

    assert dumped == list_data


def test_list_response_for_many_resource_schemas_without_actual_resources_can_be_loaded(
    user_schema, group_schema
):
    initialize()
    data = {"schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"], "totalResults": 0}
    validator = ResourcesQuery(resource_schema=[user_schema, group_schema])
    schema_cls = create_response_schema(validator, lambda: ResponseContext(status_code=200))

    loaded = schema_cls().load(data)

    assert loaded == data


def test_list_response_for_many_resource_schemas_without_actual_resources_can_be_dumped(
    user_schema, group_schema
):
    initialize()
    data = {"schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"], "totalResults": 0}
    validator = ResourcesQuery(resource_schema=[user_schema, group_schema])
    schema_cls = create_response_schema(validator)

    dumped = schema_cls().dump(data)

    assert dumped == data


def test_creating_list_response_schema_for_response_without_context_fails(
    user_schema, group_schema
):
    initialize()
    validator = ResourcesQuery(resource_schema=[user_schema, group_schema])
    schema_cls = create_response_schema(validator)

    with pytest.raises(
        scimpler.ext.marshmallow.ContextError,
        match="response context must be provided when loading ListResponseSchema",
    ):
        schema_cls().load({})


def test_loading_list_response_for_many_resource_schemas_with_unknown_resource_fails(
    user_schema, group_schema
):
    initialize()
    data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "totalResults": 0,
        "Resources": [{"schemas": ["schema:for:tests"]}],
    }
    validator = ResourcesQuery(resource_schema=[user_schema, group_schema])
    schema_cls = create_response_schema(validator, lambda: ResponseContext(status_code=200))

    with pytest.raises(marshmallow.ValidationError, match="unknown schema"):
        schema_cls().load(data)


def test_dumping_list_response_for_many_resource_schemas_with_unknown_resource_passes(
    user_schema, group_schema
):
    initialize()
    data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "totalResults": 0,
        "Resources": [{"schemas": ["schema:for:tests"]}],
    }
    expected = data.copy()
    expected["Resources"] = [{}]
    validator = ResourcesQuery(resource_schema=[user_schema, group_schema])
    schema_cls = create_response_schema(validator)

    dumped = schema_cls().dump(data)

    assert dumped == expected


def test_list_response_with_many_resource_schemas_can_be_loaded(
    list_data, list_data_deserialized, user_schema, group_schema
):
    initialize()
    validator = ResourcesQuery(resource_schema=[user_schema, group_schema])
    schema_cls = create_response_schema(validator, lambda: ResponseContext(status_code=200))

    loaded = schema_cls().load(list_data)

    assert loaded == list_data_deserialized


def test_list_response_with_single_resource_schema_can_be_dumped(
    list_user_data, list_user_data_deserialized, user_schema, group_schema
):
    initialize()
    validator = ResourcesQuery(resource_schema=user_schema)
    schema_cls = create_response_schema(validator)

    dumped = schema_cls().dump(list_user_data_deserialized)

    assert dumped == list_user_data


def test_list_response_with_single_resource_schema_can_be_loaded(
    list_user_data, list_user_data_deserialized, user_schema, group_schema
):
    initialize()
    validator = ResourcesQuery(resource_schema=user_schema)
    schema_cls = create_response_schema(validator, lambda: ResponseContext(status_code=200))

    loaded = schema_cls().load(list_user_data)

    assert loaded == list_user_data_deserialized


def test_list_response_loading_fails_if_validation_error(list_data, user_schema, group_schema):
    initialize()
    list_data["Resources"][1]["id"] = 123
    list_data["Resources"][2]["meta"]["created"] = "123"
    validator = ResourcesQuery(resource_schema=[user_schema, group_schema])
    schema_cls = create_response_schema(validator, lambda: ResponseContext(status_code=200))

    with pytest.raises(
        marshmallow.ValidationError, match="bad type, expecting 'string'.*'bad value syntax'"
    ):
        schema_cls().load(list_data)


def test_list_response_can_be_validated(list_data, user_schema, group_schema):
    initialize()
    list_data["Resources"][1]["id"] = 123
    list_data["Resources"][2]["meta"]["created"] = "123"
    validator = ResourcesQuery(resource_schema=[user_schema, group_schema])
    schema_cls = create_response_schema(validator, lambda: ResponseContext(status_code=200))
    expected_issues = {
        "body": {
            "Resources": {
                "1": {"id": ["bad type, expecting 'string'"]},
                "2": {"meta": {"created": ["bad value syntax"]}},
            }
        }
    }

    issues = schema_cls().validate(list_data)

    assert issues == expected_issues


def test_bulk_response_can_be_dumped(
    bulk_response_deserialized, bulk_response_serialized, user_schema, group_schema
):
    initialize()
    validator = BulkOperations(resource_schemas=[user_schema, group_schema])
    schema_cls = create_response_schema(validator)

    dumped = schema_cls().dump(bulk_response_deserialized)

    assert dumped == bulk_response_serialized


def test_bulk_response_can_be_loaded(
    bulk_response_deserialized, bulk_response_serialized, user_schema, group_schema
):
    initialize()
    validator = BulkOperations(resource_schemas=[user_schema, group_schema])
    schema_cls = create_response_schema(validator, lambda: ResponseContext(status_code=200))

    loaded = schema_cls().load(bulk_response_serialized)

    assert loaded.to_dict() == bulk_response_deserialized.to_dict()


def test_loading_bulk_response_without_context_fails(user_schema, group_schema):
    initialize()
    validator = BulkOperations(resource_schemas=[user_schema, group_schema])
    schema_cls = create_response_schema(validator)

    with pytest.raises(
        scimpler.ext.marshmallow.ContextError,
        match="context must be provided when loading BulkResponseSchema",
    ):
        schema_cls().load({})


def test_loading_bulk_response_with_operation_response_for_unknown_resource_fails(
    bulk_response_serialized, user_schema, group_schema
):
    initialize()
    bulk_response_serialized["Operations"] = [
        {
            "location": "https://example.com/v2/Others/92b725cd-9465-4e7d-8c16-01f8e146b87a",
            "method": "POST",
            "bulkId": "qwerty",
            "version": 'W/"oY4m4wn58tkVjJxK"',
            "response": {"id": "42"},
            "status": "201",
        }
    ]
    validator = BulkOperations(resource_schemas=[user_schema, group_schema])
    schema_cls = create_response_schema(validator, lambda: ResponseContext(status_code=200))

    with pytest.raises(marshmallow.ValidationError, match="unknown bulk operation resource"):
        schema_cls().load(bulk_response_serialized)


def test_dumping_bulk_response_with_operation_response_for_unknown_resource_passes(
    bulk_response_serialized, user_schema, group_schema
):
    initialize()
    bulk_response_serialized["Operations"] = [
        {
            "location": "https://example.com/v2/Others/92b725cd-9465-4e7d-8c16-01f8e146b87a",
            "method": "POST",
            "bulkId": "qwerty",
            "version": 'W/"oY4m4wn58tkVjJxK"',
            "response": {"id": "42"},
            "status": "201",
        }
    ]
    validator = BulkOperations(resource_schemas=[user_schema, group_schema])
    schema_cls = create_response_schema(validator)

    dumped = schema_cls().dump(bulk_response_serialized)

    assert dumped["Operations"][0]["response"] == {}


def test_bulk_response_can_be_validated(bulk_response_serialized: dict, user_schema, group_schema):
    initialize()
    bulk_response_serialized["Operations"][0]["status"] = "200"
    bulk_response_serialized["Operations"][1]["response"]["name"]["formatted"] = 123
    bulk_response_serialized["Operations"][2]["status"] = "601"
    bulk_response_serialized["Operations"][3]["response"]["members"][1]["type"] = "BadMemberType"
    validator = BulkOperations(resource_schemas=[user_schema, group_schema])
    schema_cls = create_response_schema(validator, lambda: ResponseContext(status_code=200))
    expected_issues = {
        "body": {
            "Operations": {
                "0": {"status": ["bad status code, expecting '201'"]},
                "1": {"response": {"name": {"formatted": ["bad type, expecting 'string'"]}}},
                "2": {
                    "response": {
                        "status": ["must be equal to response status code"],
                    },
                    "status": ["must be equal to 'status' attribute", "bad value content"],
                },
                "3": {
                    "response": {"members": {"1": {"type": ["must be one of: ['user', 'group']"]}}}
                },
            }
        }
    }

    issues = schema_cls().validate(bulk_response_serialized)

    assert issues == expected_issues


def test_resource_patch_request_can_be_dumped(
    user_patch_serialized, user_patch_deserialized, user_schema
):
    initialize()
    validator = ResourceObjectPatch(resource_schema=user_schema)
    schema_cls = create_request_schema(validator)

    dumped = schema_cls().dump(user_patch_deserialized)

    assert dumped == user_patch_serialized


def test_resource_patch_request_can_be_loaded(
    user_patch_serialized, user_patch_deserialized, user_schema
):
    initialize()
    validator = ResourceObjectPatch(resource_schema=user_schema)
    schema_cls = create_request_schema(validator)

    loaded = schema_cls().load(user_patch_serialized)

    assert loaded == user_patch_deserialized


def test_resource_patch_request_can_be_validated(user_patch_serialized, user_schema):
    initialize()
    validator = ResourceObjectPatch(resource_schema=user_schema)
    schema_cls = create_request_schema(validator)
    user_patch_serialized["Operations"][0]["value"]["displayName"] = "John Doe"
    user_patch_serialized["Operations"][1]["path"] = "bad^attr"
    user_patch_serialized["Operations"][2]["value"]["nickName"] = 123  # noqa
    user_patch_serialized["Operations"][3]["op"] = "delete"
    expected_issues = {
        "body": {
            "Operations": {
                "0": {"value": {"displayName": ["attribute can not be modified"]}},
                "1": {"path": ["bad attribute name 'bad^attr'"]},
                "2": {"value": {"nickName": ["bad type, expecting 'string'"]}},
                "3": {"op": ["must be one of: ['add', 'remove', 'replace']"]},
            }
        }
    }

    issues = schema_cls().validate(user_patch_serialized)

    assert issues == expected_issues


def test_bulk_request_can_be_dumped(
    bulk_request_deserialized, bulk_request_serialized, user_schema, group_schema
):
    initialize()
    validator = BulkOperations(resource_schemas=[user_schema, group_schema])
    schema_cls = create_request_schema(validator)

    dumped = schema_cls().dump(bulk_request_deserialized)

    assert dumped == bulk_request_serialized


def test_bulk_request_can_be_loaded(
    bulk_request_deserialized, bulk_request_serialized, user_schema, group_schema
):
    initialize()
    validator = BulkOperations(resource_schemas=[user_schema, group_schema])
    schema_cls = create_request_schema(validator)

    loaded = schema_cls().load(bulk_request_serialized)

    assert loaded == bulk_request_deserialized


def test_bulk_request_can_be_validated(bulk_request_serialized, user_schema, group_schema):
    initialize()
    validator = BulkOperations(resource_schemas=[user_schema, group_schema])
    schema_cls = create_request_schema(validator)
    bulk_request_serialized["Operations"][0]["data"]["schemas"].append("unknown:schema")
    bulk_request_serialized["Operations"][1]["data"]["userName"] = 123
    bulk_request_serialized["Operations"][2]["data"]["Operations"][1]["path"] = "nonExisting"
    bulk_request_serialized["Operations"][3]["method"] = "ANNIHILATE"
    expected_issues = {
        "body": {
            "Operations": {
                "0": {"data": {"schemas": ["unknown schema"]}},
                "1": {"data": {"userName": ["bad type, expecting 'string'"]}},
                "2": {"data": {"Operations": {"1": {"path": ["unknown modification target"]}}}},
                "3": {"method": ["must be one of: ['get', 'post', 'patch', 'put', 'delete']"]},
            }
        }
    }

    issues = schema_cls().validate(bulk_request_serialized)

    assert issues == expected_issues


def test_search_request_can_be_dumped(
    search_request_serialized, search_request_deserialized, user_schema, group_schema
):
    initialize()
    validator = SearchRequestPost(resource_schema=[user_schema, group_schema])
    schema_cls = create_request_schema(validator)

    dumped = schema_cls().dump(search_request_deserialized)

    assert dumped == search_request_serialized


def test_search_request_can_be_loaded(
    search_request_serialized, search_request_deserialized, user_schema, group_schema
):
    initialize()
    validator = SearchRequestPost(resource_schema=[user_schema, group_schema])
    schema_cls = create_request_schema(validator)

    loaded = schema_cls().load(search_request_serialized)

    assert loaded == search_request_deserialized


def test_initializing_after_creating_schema_fails(user_schema):
    validator = ResourceObjectGet(resource_schema=user_schema)

    create_response_schema(validator)

    with pytest.raises(
        RuntimeError, match="marshmallow extension has been automatically initialized"
    ):
        initialize()


def test_initializing_second_time_fails(user_schema):
    initialize()
    with pytest.raises(RuntimeError, match="marshmallow extension has been already initialized"):
        initialize()


def test_custom_field_converter_can_be_specified_during_initialization(
    user_deserialized, user_data_server, user_schema
):
    initialize({scimpler.data.DateTime: marshmallow.fields.String})
    validator = ResourceObjectGet(resource_schema=user_schema)
    schema_cls = create_response_schema(
        validator,
        lambda: ResponseContext(status_code=200, headers={"ETag": r'W/"3694e05e9dff591"'}),
    )

    loaded = schema_cls().load(user_data_server)

    assert isinstance(loaded["meta.created"], str)  # normally it would be `datetime`
