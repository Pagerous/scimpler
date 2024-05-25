from copy import deepcopy

import pytest

from src.assets.schemas import User, user
from src.assets.schemas.user import EnterpriseUserExtension
from src.container import SCIMDataContainer
from src.data.attributes import Integer, String
from src.data.schemas import (
    BaseResourceSchema,
    ResourceSchema,
    SchemaExtension,
    validate_resource_type_consistency,
)
from src.warning import ScimpleUserWarning


def test_correct_user_data_can_be_deserialized(user_data_client):
    expected_data = deepcopy(user_data_client)
    user_data_client["unexpected"] = 123

    data = user.User.deserialize(user_data_client)

    assert data.to_dict() == expected_data
    assert "unexpected" not in data.to_dict()


def test_validation_fails_if_bad_types(user_data_client):
    user_data_client["userName"] = 123  # noqa
    user_data_client["name"]["givenName"] = 123  # noqa
    expected_issues = {
        "userName": {
            "_errors": [
                {
                    "code": 2,
                }
            ]
        },
        "name": {
            "givenName": {
                "_errors": [
                    {
                        "code": 2,
                    }
                ]
            }
        },
    }

    issues = user.User.validate(user_data_client)

    assert issues.to_dict() == expected_issues


def test_validate_schemas_field__unknown_additional_field_is_validated(user_data_client):
    user_data_client["schemas"].append("bad:user:schema")
    expected_issues = {"schemas": {"_errors": [{"code": 14}]}}

    issues = user.User.validate(user_data_client)

    assert issues.to_dict() == expected_issues


def test_validate_schemas_field__fails_if_main_schema_is_missing(user_data_client):
    user_data_client["schemas"] = ["urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"]
    expected_issues = {"schemas": {"_errors": [{"code": 12}]}}

    issues = user.User.validate(user_data_client)

    assert issues.to_dict() == expected_issues


def test_validate_schemas_field__fails_if_extension_schema_is_missing(user_data_client):
    user_data_client["schemas"] = ["urn:ietf:params:scim:schemas:core:2.0:User"]
    expected_issues = {"schemas": {"_errors": [{"code": 13}]}}

    issues = user.User.validate(user_data_client)

    assert issues.to_dict() == expected_issues


def test_validate_schemas_field__fails_if_duplicated_values(user_data_client):
    user_data_client["schemas"] = [
        "urn:ietf:params:scim:schemas:core:2.0:User",
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:user",
    ]
    expected_issues = {"schemas": {"_errors": [{"code": 10}]}}

    issues = user.User.validate(user_data_client)

    assert issues.to_dict() == expected_issues


def test_validate_schemas_field__multiple_errors(user_data_client):
    user_data_client["schemas"] = ["bad:user:schema"]
    expected_issues = {"schemas": {"_errors": [{"code": 14}, {"code": 12}, {"code": 13}]}}

    issues = user.User.validate(user_data_client)

    assert issues.to_dict() == expected_issues


def test_validate_resource_type_consistency__fails_if_no_consistency():
    expected = {
        "meta": {
            "resourceType": {
                "_errors": [
                    {
                        "code": 8,
                    }
                ]
            }
        }
    }

    issues = validate_resource_type_consistency("Group", "User")

    assert issues.to_dict() == expected


def test_validate_resource_type_consistency__succeeds_if_consistency():
    issues = validate_resource_type_consistency("User", "User")

    assert issues.to_dict(msg=True) == {}


def test_adding_same_schema_extension_to_resource_fails():
    schema = ResourceSchema(schema="my:schema", name="MyResource")
    extension = SchemaExtension(schema="my:schema:extension", name="MyExtension")
    schema.extend(extension)

    with pytest.raises(
        ValueError,
        match="schema 'my:schema:extension' already in 'MyResource' resource",
    ):
        schema.extend(extension)


def test_schema_can_be_cloned_with_attr_filter_specified():
    schema = User.clone(attr_filter=lambda attr: attr.rep.attr in ["id", "userName"])

    assert len(list(schema.attrs)) == 2


@pytest.mark.parametrize("use_container", (True, False))
def test_data_can_be_filtered_according_to_attr_filter(user_data_client, use_container):
    expected = {
        "schemas": [
            "urn:ietf:params:scim:schemas:core:2.0:User",
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
        ],
        "groups": [
            {
                "value": "e9e30dba-f08f-4109-8486-d5c6a331660a",
                "$ref": "../Groups/e9e30dba-f08f-4109-8486-d5c6a331660a",
                "display": "Tour Guides",
            },
            {
                "value": "fc348aa8-3835-40eb-a20b-c726e15c55b5",
                "$ref": "../Groups/fc348aa8-3835-40eb-a20b-c726e15c55b5",
                "display": "Employees",
            },
            {
                "value": "71ddacd2-a8e7-49b8-a5db-ae50d0a5bfd7",
                "$ref": "../Groups/71ddacd2-a8e7-49b8-a5db-ae50d0a5bfd7",
                "display": "US Employees",
            },
        ],
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
            "manager": {
                "displayName": "John Smith",
            },
        },
    }
    if use_container:
        user_data_client = SCIMDataContainer(user_data_client)

    actual = User.filter(user_data_client, lambda attr: attr.mutability == "readOnly")

    assert actual == expected


def test_schemas_is_not_validated_further_if_bad_type(user_data_client):
    user_data_client["schemas"] = 123

    issues = User.validate(user_data_client)

    assert issues.to_dict() == {"schemas": {"_errors": [{"code": 2}]}}


def test_endpoint_can_be_changed_for_base_resource_schema():
    schema = BaseResourceSchema(
        schema="base:resource:schema", name="BaseResource", endpoint="/BaseResource"
    )

    schema.endpoint = "/BaseResourceDifferentEndpoint"

    assert schema.endpoint == "/BaseResourceDifferentEndpoint"


def test_value_error_is_raised_if_retrieving_non_existent_extension():
    with pytest.raises(ValueError, match="'User' has no 'NonExistentExtension' extension"):
        User.get_extension("NonExistentExtension")


def test_same_extension_can_not_be_registered_twice():
    with pytest.raises(RuntimeError, match="extension 'EnterpriseUser' already in resource"):
        User.extend(EnterpriseUserExtension)


def test_warning_is_raised_if_adding_extension_with_the_same_attr_name():
    resource_schema = ResourceSchema(
        schema="my:schema", name="MyResource", attrs=[String(name="attr")]
    )
    extension = SchemaExtension(
        schema="my:schema:extension", name="MyExtension", attrs=[Integer(name="attr")]
    )

    with pytest.warns(ScimpleUserWarning):
        resource_schema.extend(extension)
