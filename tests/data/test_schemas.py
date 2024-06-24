from copy import deepcopy
from typing import Generator

import pytest

from src.assets.schemas import User, user
from src.assets.schemas.user import EnterpriseUserExtension
from src.container import AttrRep, BoundedAttrRep, SCIMData
from src.data.attr_presence import AttrPresenceConfig
from src.data.attrs import Boolean, Complex, Integer, String
from src.data.schemas import (
    BaseResourceSchema,
    ResourceSchema,
    SchemaExtension,
    validate_resource_type_consistency,
)
from src.registry import register_resource_schema, resources, schemas
from src.warning import ScimpleUserWarning


@pytest.fixture
def schema_with_extensions() -> Generator[ResourceSchema, None, None]:
    schema = ResourceSchema(
        schema="my:schema",
        name="MyResource",
    )
    extension_1 = SchemaExtension(
        schema="my:schema:extension",
        name="MyExtension",
        attrs=[Complex("complex", sub_attributes=[Integer("value", required=True)])],
    )
    extension_2 = SchemaExtension(
        schema="my:schema:other_extension",
        name="MyOtherExtension",
        attrs=[Complex("complex", sub_attributes=[Integer("value", required=True)])],
    )
    schema.extend(extension_1, False)
    schema.extend(extension_2, False)
    register_resource_schema(schema)

    yield schema

    resources.pop("MyResource")
    schemas.pop("my:schema")
    schemas.pop("my:schema:extension")
    schemas.pop("my:schema:other_extension")


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

    issues = user.User.validate(user_data_client, AttrPresenceConfig("REQUEST"))

    assert issues.to_dict() == expected_issues


def test_validate_schemas_field__unknown_additional_field_is_validated(user_data_client):
    user_data_client["schemas"].append("bad:user:schema")
    expected_issues = {"schemas": {"_errors": [{"code": 14}]}}

    issues = user.User.validate(user_data_client, AttrPresenceConfig("REQUEST"))

    assert issues.to_dict() == expected_issues


def test_validate_schemas_field__fails_if_main_schema_is_missing(user_data_client):
    user_data_client["schemas"] = ["urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"]
    expected_issues = {"schemas": {"_errors": [{"code": 12}]}}

    issues = user.User.validate(user_data_client, AttrPresenceConfig("REQUEST"))

    assert issues.to_dict() == expected_issues


def test_validate_schemas_field__fails_if_extension_schema_is_missing(user_data_client):
    user_data_client["schemas"] = ["urn:ietf:params:scim:schemas:core:2.0:User"]
    expected_issues = {"schemas": {"_errors": [{"code": 13}]}}

    issues = user.User.validate(user_data_client, AttrPresenceConfig("REQUEST"))

    assert issues.to_dict() == expected_issues


def test_validate_schemas_field__fails_if_duplicated_values(user_data_client):
    user_data_client["schemas"] = [
        "urn:ietf:params:scim:schemas:core:2.0:User",
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:user",
    ]
    expected_issues = {"schemas": {"_errors": [{"code": 10}]}}

    issues = user.User.validate(user_data_client, AttrPresenceConfig("REQUEST"))

    assert issues.to_dict() == expected_issues


def test_validate_schemas_field__multiple_errors(user_data_client):
    user_data_client["schemas"] = ["bad:user:schema"]
    expected_issues = {"schemas": {"_errors": [{"code": 14}, {"code": 12}, {"code": 13}]}}

    issues = user.User.validate(user_data_client, AttrPresenceConfig("REQUEST"))

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
    schema = User.clone(attr_filter=lambda attr: attr.name in ["id", "userName"])

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
        user_data_client = SCIMData(user_data_client)

    actual = User.filter(user_data_client, lambda attr: attr.mutability == "readOnly")

    assert actual == expected


def test_schemas_is_not_validated_further_if_bad_type(user_data_client):
    user_data_client["schemas"] = 123

    issues = User.validate(user_data_client, AttrPresenceConfig("REQUEST"))

    assert issues.to_dict() == {"schemas": {"_errors": [{"code": 2}]}}


def test_invalid_schemas_items_are_detected(user_data_client):
    user_data_client["schemas"] = [User.schema, 123]
    expected_issues = {"schemas": {"_errors": [{"code": 13}], "1": {"_errors": [{"code": 2}]}}}

    issues = User.validate(user_data_client, AttrPresenceConfig("REQUEST"))

    assert issues.to_dict() == expected_issues


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
    with pytest.raises(ValueError, match="already in 'User' resource"):
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


def test_presence_validation_fails_if_returned_attribute_that_never_should_be_returned(
    user_data_server,
):
    user_data_server["password"] = "1234"
    expected = {
        "password": {
            "_errors": [
                {
                    "code": 7,
                }
            ]
        }
    }

    issues = User.validate(user_data_server, AttrPresenceConfig("RESPONSE"))

    assert issues.to_dict() == expected


def test_restricted_attributes_can_be_sent_with_request(user_data_client):
    user_data_client["password"] = "1234"

    issues = User.validate(user_data_client, AttrPresenceConfig("REQUEST"))

    assert issues.to_dict(msg=True) == {}


def test_presence_validation_fails_on_attr_not_requested_by_exclusion():
    data = SCIMData(
        {
            "id": "1",
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "userName": "Pagerous",
            "name": {"givenName": "Arkadiusz", "familyName": "Pajor"},
        }
    )

    expected = {"name": {"_errors": [{"code": 7}]}}

    issues = User.validate(
        data, AttrPresenceConfig("RESPONSE", attr_reps=[AttrRep(attr="name")], include=False)
    )

    assert issues.to_dict() == expected


def test_presence_validation_fails_on_attr_not_requested_by_inclusion():
    data = SCIMData(
        {
            "id": "1",
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "name": {"givenName": "Arkadiusz", "familyName": "Pajor"},
            "meta": {
                "resourceType": "User",
                "created": "2011-05-13T04:42:34Z",
                "lastModified": "2011-05-13T04:42:34Z",
                "location": "https://example.com/v2/Users/2819c223-7f76-453a-919d-413861904646",
                "version": r"W\/\"f250dd84f0671c3\"",
            },
        }
    )
    expected = {"meta": {"_errors": [{"code": 7}]}}

    issues = User.validate(
        data, AttrPresenceConfig("RESPONSE", attr_reps=[AttrRep(attr="name")], include=True)
    )

    assert issues.to_dict() == expected


def test_presence_validation_fails_on_sub_attr_not_requested_by_exclusion():
    data = SCIMData(
        {
            "id": "1",
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "userName": "Pagerous",
            "name": {"givenName": "Arkadiusz", "familyName": "Pajor"},
        }
    )
    expected = {
        "name": {
            "familyName": {
                "_errors": [
                    {
                        "code": 7,
                    }
                ]
            }
        }
    }

    issues = User.validate(
        data,
        AttrPresenceConfig(
            "RESPONSE",
            attr_reps=[
                BoundedAttrRep(
                    schema="urn:ietf:params:scim:schemas:core:2.0:User",
                    attr="name",
                    sub_attr="familyName",
                )
            ],
            include=False,
        ),
    )

    assert issues.to_dict() == expected


def test_presence_validation_fails_on_sub_attr_not_requested_by_inclusion():
    data = SCIMData(
        {
            "id": "1",
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "name": {"familyName": "Pajor", "givenName": "Arkadiusz"},
        }
    )
    expected = {
        "name": {
            "givenName": {
                "_errors": [
                    {
                        "code": 7,
                    }
                ]
            }
        }
    }

    issues = User.validate(
        data,
        AttrPresenceConfig(
            "RESPONSE",
            attr_reps=[
                BoundedAttrRep(
                    schema="urn:ietf:params:scim:schemas:core:2.0:User",
                    attr="name",
                    sub_attr="familyName",
                )
            ],
            include=True,
        ),
    )

    assert issues.to_dict() == expected


def test_presence_validation_fails_if_not_provided_attribute_that_always_should_be_returned():
    expected = {
        "id": {
            "_errors": [
                {
                    "code": 5,
                }
            ]
        },
        "schemas": {
            "_errors": [
                {
                    "code": 5,
                }
            ]
        },
        "userName": {
            "_errors": [
                {
                    "code": 5,
                }
            ]
        },
    }

    issues = User.validate({}, AttrPresenceConfig("RESPONSE"))

    assert issues.to_dict() == expected


def test_presence_validation_fails_if_not_provided_requested_required_attribute():
    data = SCIMData(
        {
            "id": "1",
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        }
    )
    expected = {
        "userName": {
            "_errors": [
                {
                    "code": 5,
                }
            ]
        },
    }

    issues = User.validate(
        data,
        AttrPresenceConfig("RESPONSE", attr_reps=[AttrRep(attr="username")], include=True),
    )

    assert issues.to_dict() == expected


def test_presence_validation_passes_if_not_provided_requested_optional_attribute():
    data = SCIMData(
        {
            "id": "1",
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        }
    )

    issues = User.validate(
        data,
        AttrPresenceConfig(
            "RESPONSE", attr_reps=[AttrRep(attr="name", sub_attr="familyname")], include=True
        ),
    )

    assert issues.to_dict(msg=True) == {}


def test_presence_validation_fails_on_multivalued_complex_attr_not_requested_by_exclusion():
    data = SCIMData(
        {
            "id": "1",
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "userName": "Pagerous",
            "emails": [
                {"type": "work", "primary": True, "display": "example@example.com"},
                {"type": "home", "primary": False},
                {"type": "other", "primary": False, "display": "example@example.com"},
            ],
        }
    )
    expected = {
        "emails": {
            "0": {"display": {"_errors": [{"code": 7}]}},
            "2": {"display": {"_errors": [{"code": 7}]}},
        }
    }

    issues = User.validate(
        data,
        AttrPresenceConfig(
            "RESPONSE", attr_reps=[AttrRep(attr="emails", sub_attr="display")], include=False
        ),
    )

    assert issues.to_dict() == expected


def test_presence_validation_fails_on_multivalued_complex_attr_not_requested_by_inclusion():
    data = SCIMData(
        {
            "id": "1",
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "emails": [
                {"type": "work", "primary": True, "display": "example@example.com"},
                {"display": "example@example.com"},
                {"type": "other", "primary": False, "display": "example@example.com"},
            ],
        }
    )
    expected = {
        "emails": {
            "0": {"type": {"_errors": [{"code": 7}]}, "primary": {"_errors": [{"code": 7}]}},
            "2": {"type": {"_errors": [{"code": 7}]}, "primary": {"_errors": [{"code": 7}]}},
        }
    }

    issues = User.validate(
        data,
        AttrPresenceConfig(
            "RESPONSE", attr_reps=[AttrRep(attr="emails", sub_attr="display")], include=True
        ),
    )

    assert issues.to_dict() == expected


def test_specifying_attribute_issued_by_service_provider_causes_validation_failure(
    user_data_client,
):
    user_data_client["id"] = "should-not-be-provided"
    expected_issues = {"id": {"_errors": [{"code": 6}]}}

    issues = User.validate(user_data_client, AttrPresenceConfig("REQUEST"))

    assert issues.to_dict() == expected_issues


def test_presence_validation_fails_if_missing_required_field_from_required_extension():
    schema = ResourceSchema(schema="my:schema", name="MyResource")
    extension = SchemaExtension(
        schema="my:schema:extension", name="MyExtension", attrs=[Integer("age", required=True)]
    )
    schema.extend(extension, required=True)
    expected_issues = {"my:schema:extension": {"age": {"_errors": [{"code": 5}]}}}

    issues = schema.validate(
        SCIMData({"id": "1", "schemas": ["my:schema"]}),
        AttrPresenceConfig("RESPONSE"),
    )

    assert issues.to_dict() == expected_issues


def test_presence_validation_succeeds_if_missing_required_field_from_non_required_extension():
    schema = ResourceSchema(schema="my:schema", name="MyResource")
    extension = SchemaExtension(
        schema="my:schema:extension", name="MyExtension", attrs=[Integer("age", required=True)]
    )
    schema.extend(extension, required=False)

    issues = schema.validate(
        SCIMData({"id": "1", "schemas": ["my:schema"]}),
        AttrPresenceConfig("RESPONSE"),
    )

    assert issues.to_dict(msg=True) == {}


def test_sub_attributes_presence_is_not_validated_if_multivalued_root_attribute_has_value_none():
    my_resource = ResourceSchema(
        schema="my:schema",
        name="MyResource",
        attrs=[
            Complex(
                name="super_complex",
                multi_valued=True,
                sub_attributes=[
                    String("str_required", required=True),
                    Integer("int_required", required=True),
                    Boolean("bool_required", required=True),
                ],
            )
        ],
    )
    data = SCIMData(
        {
            "schemas": ["my:schema"],
            "super_complex": None,
        }
    )

    issues = my_resource.validate(
        data,
        AttrPresenceConfig(
            "REQUEST",
            attr_reps=[
                AttrRep(attr="super_complex", sub_attr="str_required"),
                AttrRep(attr="super_complex", sub_attr="int_required"),
                AttrRep(attr="super_complex", sub_attr="bool_required"),
            ],
            include=True,
        ),
    )

    assert issues.to_dict(msg=True) == {}


def test_presence_validation_fails_if_provided_same_attr_from_different_schema(
    schema_with_extensions,
):
    data = {
        "id": "1",
        "schemas": ["my:schema", "my:schema:extension", "my:schema:other_extension"],
        "my:schema:extension": {"complex": {"value": 10}},
        "my:schema:other_extension": {"complex": {"value": 10}},
    }
    expected = {
        "my:schema:extension": {
            "complex": {
                "_errors": [
                    {
                        "code": 7,
                    }
                ]
            }
        }
    }

    issues = schema_with_extensions.validate(
        data,
        AttrPresenceConfig(
            "RESPONSE",
            attr_reps=[
                BoundedAttrRep(
                    schema="my:schema:other_extension",
                    attr="complex",
                    sub_attr="value",
                )
            ],
            include=True,
        ),
    )

    assert issues.to_dict() == expected


def test_presence_validation_passes_if_provided_same_attr_from_different_schema_and_attr_rep(
    schema_with_extensions,
):
    data = {
        "id": "1",
        "schemas": ["my:schema", "my:schema:extension", "my:schema:other_extension"],
        "my:schema:extension": {"complex": {"value": 10}},
        "my:schema:other_extension": {"complex": {"value": 10}},
    }

    issues = schema_with_extensions.validate(
        data,
        AttrPresenceConfig(
            "RESPONSE",
            attr_reps=[
                AttrRep(
                    attr="complex",
                    sub_attr="value",
                )
            ],
            include=True,
        ),
    )

    assert issues.to_dict(msg=True) == {}


def test_registering_different_extensions_but_with_the_same_name_fails():
    schema = ResourceSchema(
        schema="my:schema",
        name="MyResource",
    )
    extension_1 = SchemaExtension(
        schema="my:schema:extension",
        name="MyExtension",
    )
    extension_2 = SchemaExtension(
        schema="my:schema:other_extension",
        name="MyExtension",  # same name
    )
    schema.extend(extension_1)

    with pytest.raises(RuntimeError, match="extension 'MyExtension' already in resource"):
        schema.extend(extension_2)
