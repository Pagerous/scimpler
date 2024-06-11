import pytest

from src.assets.schemas import group, list_response, user
from src.container import AttrRep, SCIMDataContainer
from src.data.attr_presence import AttrPresenceConfig


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


def test_resources_validation_fails_if_bad_type(list_user_data):
    schema = list_response.ListResponse([user.User])
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


def test_resources_validation_succeeds_for_correct_data(list_user_data):
    schema = list_response.ListResponse([user.User])
    # below fields should be filtered-out
    list_user_data["unexpected"] = 123
    list_user_data["Resources"][0]["unexpected"] = 123
    list_user_data["Resources"][1]["name"]["unexpected"] = 123

    issues = schema.validate(list_user_data, AttrPresenceConfig("RESPONSE"))

    assert issues.to_dict(msg=True) == {}


def test_resources_validation_fails_if_bad_items_per_page_and_resource_type(list_user_data):
    schema = list_response.ListResponse([user.User])
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


def test_resources_validation_fails_if_unknown_schema_in_resource(list_user_data):
    schema = list_response.ListResponse([user.User, group.Group])
    list_user_data["Resources"][0]["schemas"] = ["totally:unknown:schema"]
    expected = {
        "Resources": {
            "0": {"_errors": [{"code": 14}]},
        },
    }

    issues = schema.validate(list_user_data, AttrPresenceConfig("RESPONSE"))

    assert issues.to_dict() == expected


@pytest.mark.parametrize(
    ("data", "expected"),
    (
        (
            [
                SCIMDataContainer(
                    {
                        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
                        "userName": "bjensen",
                    }
                )
            ],
            [user.User],
        ),
        (
            [
                # only "schemas" attribute is used
                SCIMDataContainer(
                    {
                        "urn:ietf:params:scim:schemas:core:2.0:User:userName": "bjensen",
                    }
                )
            ],
            [None],
        ),
        (
            [
                SCIMDataContainer(
                    {
                        "userName": "bjensen",
                    }
                )
            ],
            [None],
        ),
        (
            [
                # extensions are ignored
                SCIMDataContainer(
                    {
                        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
                            "employeeNumber": "2",
                        }
                    }
                )
            ],
            [None],
        ),
    ),
)
def test_get_schema_for_resources(data, expected):
    schema = list_response.ListResponse([user.User, user.User])

    actual = schema.get_schemas_for_resources(data)

    assert isinstance(actual, type(expected))


@pytest.mark.parametrize(
    ("data", "expected"),
    (
        (
            [
                SCIMDataContainer(
                    {
                        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
                        "userName": "bjensen",
                    }
                )
            ],
            [user.User],
        ),
        (
            [
                SCIMDataContainer(
                    {
                        "urn:ietf:params:scim:schemas:core:2.0:User:userName": "bjensen",
                    }
                )
            ],
            [user.User],
        ),
        (
            [
                SCIMDataContainer(
                    {
                        "userName": "bjensen",
                    }
                )
            ],
            [user.User],
        ),
        (
            [
                # extensions are ignored
                SCIMDataContainer(
                    {
                        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
                            "employeeNumber": "2",
                        }
                    }
                )
            ],
            [user.User],
        ),
    ),
)
def test_get_schema_for_resources__returns_schema_for_bad_data_if_single_schema(data, expected):
    schema = list_response.ListResponse([user.User])

    actual = schema.get_schemas_for_resources(data)

    assert isinstance(actual, type(expected))


def test_list_response_can_be_serialized(user_data_client):
    schema = list_response.ListResponse(resource_schemas=[user.User])
    data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "totalResults": 3,
        "Resources": [
            user.User.deserialize(user_data_client),
            user.User.deserialize(user_data_client),
            user.User.deserialize(user_data_client),
        ],
    }
    expected_data = {
        "schemas": data["schemas"],
        "totalResults": data["totalResults"],
        "Resources": [item.to_dict() for item in data["Resources"]],
    }

    serialized = schema.serialize(data)

    assert serialized == expected_data


def test_list_response_with_missing_resources_can_be_serialized(user_data_client):
    schema = list_response.ListResponse(resource_schemas=[user.User])
    data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "totalResults": 3,
    }

    serialized = schema.serialize(data)

    assert serialized == data


def test_bad_resources_type_is_serialized_as_empty_dict(user_data_client):
    schema = list_response.ListResponse(resource_schemas=[user.User])
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


def test_bad_resources_type_is_validated(user_data_client):
    schema = list_response.ListResponse(resource_schemas=[user.User])
    data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "totalResults": 3,
        "Resources": "foo",
    }
    expected_issues = {"Resources": {"_errors": [{"code": 2}]}}

    issues = schema.validate(data, AttrPresenceConfig("RESPONSE"))

    assert issues.to_dict() == expected_issues


def test_no_schema_is_inferred_for_resource_with_no_schemas_field_and_many_schemas():
    schema = list_response.ListResponse(resource_schemas=[user.User, group.Group])

    schemas = schema.get_schemas_for_resources([{"userName": "some_user"}])

    assert len(schemas) == 1
    assert schemas[0] is None


def test_no_schema_is_inferred_for_resource_with_unknown_schemas_and_many_schemas():
    schema = list_response.ListResponse(resource_schemas=[user.User, group.Group])

    schemas = schema.get_schemas_for_resources(
        [{"schemas": ["unknown:schema"], "userName": "some_user"}]
    )

    assert len(schemas) == 1
    assert schemas[0] is None


def test_validate_resources_attribute_presence__fails_if_requested_attribute_not_excluded(
    list_user_data,
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

    issues = list_response.ListResponse([user.User]).validate(
        list_user_data,
        resource_presence_config=AttrPresenceConfig(
            direction="RESPONSE",
            attr_reps=[AttrRep(attr="name")],
            include=False,
        ),
    )

    assert issues.to_dict() == expected
