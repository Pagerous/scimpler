import pytest

from scimpler.container import SCIMData
from scimpler.data.attr_presence import AttrPresenceConfig
from scimpler.identifiers import AttrRep
from scimpler.schemas import list_response


def test_validate_items_per_page_consistency__fails_if_not_matching_resources(list_user_data):
    expected = {
        "itemsPerPage": {"_errors": [{"code": 8}]},
        "Resources": {"_errors": [{"code": 8}]},
    }

    issues = list_response.validate_items_per_page_consistency(
        resources_=list_user_data["Resources"],
        items_per_page_=1,
    )

    assert issues.to_dict() == expected


def test_validate_items_per_page_consistency__succeeds_if_correct_data(list_user_data):
    issues = list_response.validate_items_per_page_consistency(
        resources_=list_user_data["Resources"],
        items_per_page_=2,
    )

    assert issues.to_dict(msg=True) == {}


def test_resources_validation_fails_if_bad_type(list_user_data, user_schema):
    schema = list_response.ListResponseSchema([user_schema])
    list_user_data["Resources"][0]["userName"] = 123
    list_user_data["Resources"][1]["userName"] = 123

    expected_issues = {
        "Resources": {
            "0": {"userName": {"_errors": [{"code": 2}]}},
            "1": {"userName": {"_errors": [{"code": 2}]}},
        }
    }

    issues = schema.validate(list_user_data, AttrPresenceConfig("RESPONSE"))

    assert issues.to_dict() == expected_issues


def test_resources_validation_succeeds_for_correct_data(list_user_data, user_schema):
    schema = list_response.ListResponseSchema([user_schema])
    # below fields should be filtered-out
    list_user_data["unexpected"] = 123
    list_user_data["Resources"][0]["unexpected"] = 123
    list_user_data["Resources"][1]["name"]["unexpected"] = 123

    issues = schema.validate(list_user_data, AttrPresenceConfig("RESPONSE"))

    assert issues.to_dict(msg=True) == {}


def test_resources_validation_fails_if_bad_items_per_page_and_resource_type(
    list_user_data, user_schema
):
    schema = list_response.ListResponseSchema([user_schema])
    list_user_data["Resources"][0] = []
    list_user_data["Resources"][1]["userName"] = 123
    list_user_data["itemsPerPage"] = "incorrect"
    expected = {
        "itemsPerPage": {"_errors": [{"code": 2}]},
        "Resources": {
            "0": {"_errors": [{"code": 2}]},
            "1": {"userName": {"_errors": [{"code": 2}]}},
        },
    }

    issues = schema.validate(list_user_data, AttrPresenceConfig("RESPONSE"))

    assert issues.to_dict() == expected


def test_resources_validation_fails_if_unknown_schema_in_resource(
    list_user_data, user_schema, group_schema
):
    schema = list_response.ListResponseSchema([user_schema, group_schema])
    list_user_data["Resources"][0]["schemas"] = ["totally:unknown:schema"]
    expected = {
        "Resources": {
            "0": {"_errors": [{"code": 14}]},
        },
    }

    issues = schema.validate(list_user_data, AttrPresenceConfig("RESPONSE"))

    assert issues.to_dict() == expected


@pytest.mark.parametrize(
    ("data", "schema"),
    (
        (
            [
                SCIMData(
                    {
                        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
                        "userName": "bjensen",
                    }
                )
            ],
            "user_schema",
        ),
        (
            [
                # only "schemas" attribute is used
                SCIMData(
                    {
                        "urn:ietf:params:scim:schemas:core:2.0:User:userName": "bjensen",
                    }
                )
            ],
            None,
        ),
        (
            [
                SCIMData(
                    {
                        "userName": "bjensen",
                    }
                )
            ],
            None,
        ),
        (
            [
                # extensions are ignored
                SCIMData(
                    {
                        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
                            "employeeNumber": "2",
                        }
                    }
                )
            ],
            None,
        ),
    ),
    indirect=["schema"],
)
def test_get_schema_for_resources(data, schema, user_schema):
    list_schema = list_response.ListResponseSchema([user_schema, user_schema])

    actual = list_schema.get_schemas(data)[0]

    assert isinstance(actual, type(schema))


@pytest.mark.parametrize(
    ("data",),
    (
        (
            [
                SCIMData(
                    {
                        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
                        "userName": "bjensen",
                    }
                )
            ],
        ),
        (
            [
                SCIMData(
                    {
                        "urn:ietf:params:scim:schemas:core:2.0:User:userName": "bjensen",
                    }
                )
            ],
        ),
        (
            [
                SCIMData(
                    {
                        "userName": "bjensen",
                    }
                )
            ],
        ),
        (
            [
                # extensions are ignored
                SCIMData(
                    {
                        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
                            "employeeNumber": "2",
                        }
                    }
                )
            ],
        ),
    ),
)
def test_get_schema_for_resources__returns_schema_for_bad_data_if_single_schema(data, user_schema):
    list_schema = list_response.ListResponseSchema([user_schema])

    actual = list_schema.get_schemas(data)[0]

    assert actual is user_schema


def test_list_response_can_be_serialized(user_data_client, user_schema):
    schema = list_response.ListResponseSchema(resource_schemas=[user_schema])
    data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "totalResults": 3,
        "Resources": [
            user_schema.deserialize(user_data_client),
            user_schema.deserialize(user_data_client),
            user_schema.deserialize(user_data_client),
        ],
    }
    expected_data = {
        "schemas": data["schemas"],
        "totalResults": data["totalResults"],
        "Resources": [item.to_dict() for item in data["Resources"]],
    }

    serialized = schema.serialize(data)

    assert serialized == expected_data


def test_list_response_with_missing_resources_can_be_serialized(user_data_client, user_schema):
    schema = list_response.ListResponseSchema(resource_schemas=[user_schema])
    data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "totalResults": 3,
    }

    serialized = schema.serialize(data)

    assert serialized == data


def test_bad_resources_type_is_serialized_as_empty_dict(user_data_client, user_schema):
    schema = list_response.ListResponseSchema(resource_schemas=[user_schema])
    data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "totalResults": 3,
        "Resources": ["bad_type", ["also_bad_type"]],
    }
    expected_data = {
        "schemas": data["schemas"],
        "totalResults": data["totalResults"],
        "Resources": [{}, {}],
    }

    serialized = schema.serialize(data)

    assert serialized == expected_data


def test_bad_resources_type_is_validated(user_data_client, user_schema):
    schema = list_response.ListResponseSchema(resource_schemas=[user_schema])
    data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "totalResults": 3,
        "Resources": "foo",
    }
    expected_issues = {"Resources": {"_errors": [{"code": 2}]}}

    issues = schema.validate(data, AttrPresenceConfig("RESPONSE"))

    assert issues.to_dict() == expected_issues


def test_no_schema_is_inferred_for_resource_with_no_schemas_field_and_many_schemas(
    user_schema, group_schema
):
    schema = list_response.ListResponseSchema(resource_schemas=[user_schema, group_schema])

    schemas = schema.get_schemas([{"userName": "some_user"}])

    assert len(schemas) == 1
    assert schemas[0] is None


def test_no_schema_is_inferred_for_resource_with_unknown_schemas_and_many_schemas(
    user_schema, group_schema
):
    schema = list_response.ListResponseSchema(resource_schemas=[user_schema, group_schema])

    schemas = schema.get_schemas([{"schemas": ["unknown:schema"], "userName": "some_user"}])

    assert len(schemas) == 1
    assert schemas[0] is None


def test_validate_resources_attribute_presence__fails_if_requested_attribute_not_excluded(
    list_user_data, user_schema
):
    expected = {
        "Resources": {
            "0": {
                "name": {
                    "_errors": [
                        {
                            "code": 7,
                        }
                    ]
                }
            },
            "1": {
                "name": {
                    "_errors": [
                        {
                            "code": 7,
                        }
                    ]
                }
            },
        }
    }

    issues = list_response.ListResponseSchema([user_schema]).validate(
        list_user_data,
        resource_presence_config=AttrPresenceConfig(
            direction="RESPONSE",
            attr_reps=[AttrRep(attr="name")],
            include=False,
        ),
    )

    assert issues.to_dict() == expected
