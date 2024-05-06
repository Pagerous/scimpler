from copy import deepcopy

import pytest

from src.assets.schemas import user
from src.data.schemas import (
    ResourceSchema,
    SchemaExtension,
    validate_resource_type_consistency,
)


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
    expected_issues = {"schemas": {"_errors": [{"code": 27}]}}

    issues = user.User.validate(user_data_client)

    assert issues.to_dict() == expected_issues


def test_validate_schemas_field__fails_if_main_schema_is_missing(user_data_client):
    user_data_client["schemas"] = ["urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"]
    expected_issues = {"schemas": {"_errors": [{"code": 28}]}}

    issues = user.User.validate(user_data_client)

    assert issues.to_dict() == expected_issues


def test_validate_schemas_field__fails_if_extension_schema_is_missing(user_data_client):
    user_data_client["schemas"] = ["urn:ietf:params:scim:schemas:core:2.0:User"]
    expected_issues = {"schemas": {"_errors": [{"code": 29}]}}

    issues = user.User.validate(user_data_client)

    assert issues.to_dict() == expected_issues


def test_validate_schemas_field__fails_if_duplicated_values(user_data_client):
    user_data_client["schemas"] = [
        "urn:ietf:params:scim:schemas:core:2.0:User",
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:user",
    ]
    expected_issues = {"schemas": {"_errors": [{"code": 41}]}}

    issues = user.User.validate(user_data_client)

    assert issues.to_dict() == expected_issues


def test_validate_schemas_field__multiple_errors(user_data_client):
    user_data_client["schemas"] = ["bad:user:schema"]
    expected_issues = {"schemas": {"_errors": [{"code": 27}, {"code": 28}, {"code": 29}]}}

    issues = user.User.validate(user_data_client)

    assert issues.to_dict() == expected_issues


def test_validate_resource_type_consistency__fails_if_no_consistency():
    expected = {
        "meta": {
            "resourceType": {
                "_errors": [
                    {
                        "code": 17,
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
