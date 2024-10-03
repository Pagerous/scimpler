import pytest

from scimpler.data.attr_value_presence import AttrValuePresenceConfig
from scimpler.data.attrs import AttributeMutability, String
from scimpler.data.filter import Filter
from scimpler.data.identifiers import AttrName, AttrRep
from scimpler.data.operator import ComplexAttributeOperator, Equal
from scimpler.data.patch import PatchPath
from scimpler.data.schemas import ResourceSchema, SchemaExtension
from scimpler.data.scim_data import Invalid, ScimData
from scimpler.schemas.patch_op import PatchOpSchema


@pytest.mark.parametrize(
    ("value", "expected_issues"),
    (
        (
            [
                ScimData({"op": "add", "path": "userName", "value": "bjensen"}),
                ScimData({"op": "unknown"}),
            ],
            {"1": {"op": {"_errors": [{"code": 9}]}}},
        ),
        (
            [
                ScimData({"op": "add", "path": "userName", "value": "bjensen"}),
                ScimData({"op": "remove", "path": None}),
            ],
            {"1": {"path": {"_errors": [{"code": 5}]}}},
        ),
        (
            [
                ScimData({"op": "add", "path": "userName", "value": "bjensen"}),
                ScimData({"op": "add"}),
            ],
            {"1": {"value": {"_errors": [{"code": 5}]}}},
        ),
    ),
)
def test_validate_patch_operations(value, expected_issues, user_schema):
    issues = PatchOpSchema(user_schema).attrs.get("operations").validate(value)

    assert issues.to_dict() == expected_issues


@pytest.mark.parametrize("op", ("add", "replace"))
def test_patch_op__add_and_replace_operation_without_path_can_be_deserialized(
    op, user_client_schema
):
    schema = PatchOpSchema(resource_schema=user_client_schema)
    input_data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [
            {
                "op": op,
                "value": {
                    "ignore_me": 42,
                    "name": {
                        "formatted": "Ms. Barbara J Jensen III",
                        "ignore_me": 42,
                    },
                    "userName": "bjensen",
                    "emails": [{"value": "bjensen@example.com", "type": "work"}],
                    "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
                        "ignore_me": 42,
                        "department": "Tour Operations",
                        "manager": {"value": "10", "$ref": "/Users/10"},
                    },
                },
            }
        ],
    }
    expected_operation_value = {
        "name": {
            "formatted": "Ms. Barbara J Jensen III",
        },
        "userName": "bjensen",
        "emails": [{"value": "bjensen@example.com", "type": "work"}],
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
            "department": "Tour Operations",
            "manager": {"value": "10", "$ref": "/Users/10"},
        },
    }

    issues = schema.validate(input_data, AttrValuePresenceConfig("REQUEST"))
    assert issues.to_dict(message=True) == {}

    actual_data = schema.deserialize(input_data)
    assert actual_data["Operations"][0].type == op
    assert actual_data["Operations"][0].value == expected_operation_value


@pytest.mark.parametrize("op", ("add", "replace"))
def test_validate_add_and_replace_operation_without_path__fails_for_incorrect_data(op, user_schema):
    schema = PatchOpSchema(resource_schema=user_schema)
    input_data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [
            {
                "op": op,
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
            },
        ],
    }
    expected_issues = {
        "Operations": {
            "0": {
                "value": {
                    "name": {"formatted": {"_errors": [{"code": 2}]}},
                    "userName": {"_errors": [{"code": 2}]},
                    "emails": {"0": {"type": {"_errors": [{"code": 2}]}}},
                    "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
                        "department": {"_errors": [{"code": 2}]},
                        "manager": {"displayName": {"_errors": [{"code": 2}, {"code": 29}]}},
                    },
                }
            }
        }
    }

    issues = schema.validate(input_data, AttrValuePresenceConfig("REQUEST"))
    assert issues.to_dict() == expected_issues


@pytest.mark.parametrize("op", ("add", "replace"))
def test_validate_add_and_replace_operation_without_path__fails_if_attribute_is_readonly(
    op, user_schema
):
    schema = PatchOpSchema(resource_schema=user_schema)
    input_data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [
            {
                "op": op,
                "value": {"meta": {"resourceType": "Users"}},
            }
        ],
    }
    expected_issues = {
        "Operations": {
            "0": {
                "value": {
                    "meta": {"_errors": [{"code": 29}], "resourceType": {"_errors": [{"code": 8}]}}
                }
            }
        }
    }

    issues = schema.validate(input_data, AttrValuePresenceConfig("REQUEST"))

    assert issues.to_dict() == expected_issues


@pytest.mark.parametrize("op", ("add", "replace"))
@pytest.mark.parametrize(
    ("path", "input_value", "expected_value", "expected_value_issues"),
    (
        (
            "userName",
            123,
            Invalid,
            {"_errors": [{"code": 2}]},
        ),
        (
            "name.formatted",
            123,
            Invalid,
            {"_errors": [{"code": 2}]},
        ),
        (
            "name",
            {"formatted": 123, "familyName": 123},
            {"formatted": Invalid, "familyName": Invalid},
            {"formatted": {"_errors": [{"code": 2}]}, "familyName": {"_errors": [{"code": 2}]}},
        ),
        (
            "name",
            123,
            Invalid,
            {"_errors": [{"code": 2}]},
        ),
        (
            "emails",
            123,
            Invalid,
            {"_errors": [{"code": 2}]},
        ),
        (
            "emails",
            [{"type": 123, "value": 123}],
            [{"type": Invalid, "value": Invalid}],
            {"0": {"type": {"_errors": [{"code": 2}]}, "value": {"_errors": [{"code": 2}]}}},
        ),
        (
            "emails",
            {"type": "home", "value": "home@example.com"},
            Invalid,
            {"_errors": [{"code": 2}]},
        ),
        (
            'emails[type eq "work"].value',
            123,
            Invalid,
            {"_errors": [{"code": 2}]},
        ),
    ),
)
def test_validate_add_and_replace_operation__fails_for_incorrect_data(
    op, path, input_value, expected_value, expected_value_issues, user_schema
):
    schema = PatchOpSchema(resource_schema=user_schema)
    input_data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [
            {
                "op": op,
                "path": path,
                "value": input_value,
            }
        ],
    }
    expected_issues = {"Operations": {"0": {"value": expected_value_issues}}}

    issues = schema.validate(input_data, AttrValuePresenceConfig("REQUEST"))

    assert issues.to_dict() == expected_issues


@pytest.mark.parametrize("op", ("add", "replace"))
@pytest.mark.parametrize(
    ("path", "expected_path", "value", "expected_value"),
    (
        (
            "userName",
            PatchPath(
                attr_rep=AttrRep(attr="userName"),
                sub_attr_name=None,
                filter_=None,
            ),
            "bjensen",
            "bjensen",
        ),
        (
            "name.formatted",
            PatchPath(
                attr_rep=AttrRep(attr="name"),
                sub_attr_name=AttrName("formatted"),
                filter_=None,
            ),
            "Jan Kowalski",
            "Jan Kowalski",
        ),
        (
            "name",
            PatchPath(
                attr_rep=AttrRep(attr="name"),
                sub_attr_name=None,
                filter_=None,
            ),
            {"formatted": "Jan Kowalski", "familyName": "Kowalski"},
            ScimData({"formatted": "Jan Kowalski", "familyName": "Kowalski"}),
        ),
        (
            "emails",
            PatchPath(
                attr_rep=AttrRep(attr="emails"),
                sub_attr_name=None,
                filter_=None,
            ),
            [{"type": "work", "value": "work@example.com"}],
            [ScimData({"type": "work", "value": "work@example.com"})],
        ),
        (
            'emails[type eq "work"].value',
            PatchPath(
                attr_rep=AttrRep(attr="emails"),
                sub_attr_name=AttrName("value"),
                filter_=Filter(
                    ComplexAttributeOperator(
                        attr_rep=AttrRep(attr="emails"),
                        sub_operator=Equal(
                            attr_rep=AttrRep(attr="type"),
                            value="work",
                        ),
                    )
                ),
            ),
            "work@example.com",
            "work@example.com",
        ),
        (
            'emails[type eq "work"]',
            PatchPath(
                attr_rep=AttrRep(attr="emails"),
                sub_attr_name=None,
                filter_=Filter(
                    ComplexAttributeOperator(
                        attr_rep=AttrRep(attr="emails"),
                        sub_operator=Equal(
                            attr_rep=AttrRep(attr="type"),
                            value="work",
                        ),
                    )
                ),
            ),
            {"value": "work@example.com"},
            {"value": "work@example.com"},
        ),
    ),
)
def test_deserialize_add_and_replace_operation__succeeds_on_correct_data(
    op, path, expected_path, value, expected_value, user_schema
):
    schema = PatchOpSchema(resource_schema=user_schema)
    input_data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [
            {
                "op": op,
                "path": path,
                "value": value,
            }
        ],
    }

    issues = schema.validate(input_data, AttrValuePresenceConfig("REQUEST"))
    assert issues.to_dict(message=True) == {}

    actual_data = schema.deserialize(input_data)
    assert actual_data.get("Operations")[0].value == expected_value
    assert actual_data.get("Operations")[0].path == expected_path


@pytest.mark.parametrize("op", ("add", "replace"))
@pytest.mark.parametrize(
    ("path", "value"),
    (
        ("id", "123"),
        (
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:manager.displayName",
            "The Grok",
        ),
        ("meta", {"resourceType": "Users"}),
        ("groups", [{"type": "direct", "value": "admins"}]),
        ('groups[type eq "direct"].value', "admins"),
    ),
)
def test_add_operation__fails_if_attribute_is_readonly(op, path, value, user_schema):
    schema = PatchOpSchema(resource_schema=user_schema)
    input_data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [
            {
                "op": op,
                "path": path,
                "value": value,
            }
        ],
    }
    expected_issues = {"Operations": {"0": {"value": {"_errors": [{"code": 29}]}}}}

    issues = schema.validate(input_data, AttrValuePresenceConfig("REQUEST"))

    assert issues.to_dict() == expected_issues


@pytest.mark.parametrize(
    "path",
    (
        "name",
        "urn:ietf:params:scim:schemas:core:2.0:User:name.formatted",
        "emails",
        "emails[type eq 'work']",
        "emails[type eq 'work'].value",
    ),
)
def test_remove_operation__succeeds_if_correct_path(path, user_schema):
    schema = PatchOpSchema(resource_schema=user_schema)
    input_data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [
            {
                "op": "remove",
                "path": path,
                "value": "dummy",
            }
        ],
    }

    assert (
        schema.validate(input_data, AttrValuePresenceConfig("REQUEST")).to_dict(message=True) == {}
    )

    deserialized = schema.deserialize(input_data)
    assert deserialized["Operations"][0].path == PatchPath.deserialize(path)
    assert deserialized["Operations"][0].type == "remove"
    assert deserialized["Operations"][0].value is None


def test_remove_operation__path_can_point_at_item_of_simple_multivalued_attribute(fake_schema):
    schema = PatchOpSchema(resource_schema=fake_schema)
    path = "str_mv[value sw 'a']"
    input_data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [
            {
                "op": "remove",
                "path": path,
            }
        ],
    }

    assert (
        schema.validate(input_data, AttrValuePresenceConfig("REQUEST")).to_dict(message=True) == {}
    )

    deserialized = schema.deserialize(input_data)
    assert deserialized["Operations"][0].type == "remove"
    assert deserialized["Operations"][0].path == PatchPath.deserialize(path)


@pytest.mark.parametrize(
    ("path", "expected_path_issue_codes", "schema"),
    (
        ("id", [{"code": 29}, {"code": 30}], "user_schema"),
        ("userName", [{"code": 30}], "user_schema"),
        (
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:manager.displayName",
            [{"code": 29}],
            "user_schema",
        ),
        ("meta", [{"code": 29}], "user_schema"),
        ("groups", [{"code": 29}], "user_schema"),
        ('groups[type eq "direct"].value', [{"code": 29}], "user_schema"),
        ("c2_mv[int eq 1].bool", [{"code": 30}], "fake_schema"),
    ),
    indirect=["schema"],
)
def test_remove_operation__fails_if_attribute_is_readonly_or_required(
    path, expected_path_issue_codes, schema: ResourceSchema
):
    patch_schema = PatchOpSchema(schema)
    input_data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [
            {
                "op": "remove",
                "path": path,
            }
        ],
    }
    expected_issues = {"Operations": {"0": {"path": {"_errors": expected_path_issue_codes}}}}

    assert (
        patch_schema.validate(input_data, AttrValuePresenceConfig("REQUEST")).to_dict()
        == expected_issues
    )

    deserialized = patch_schema.deserialize(input_data)
    assert deserialized["Operations"][0].path == PatchPath.deserialize(path)


def test_validate_empty_body(user_schema):
    schema = PatchOpSchema(resource_schema=user_schema)
    expected_issues = {
        "schemas": {"_errors": [{"code": 5}]},
        "Operations": {"_errors": [{"code": 5}]},
    }

    issues = schema.validate({}, AttrValuePresenceConfig("REQUEST"))

    assert issues.to_dict() == expected_issues


def test_value_is_removed_if_remove_operation_during_deserialization(user_schema):
    schema = PatchOpSchema(resource_schema=user_schema)
    data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [
            {
                "op": "add",
                "path": "name.formatted",
                "value": "John Doe",
            },
            {
                "op": "remove",
                "path": "name.formatted",
                "value": "John Doe",
            },
        ],
    }

    deserialized = schema.deserialize(data)

    assert deserialized["Operations"][0].value is not None
    assert deserialized["Operations"][1].value is None


def test_operation_value_is_not_validated_if_bad_path(user_schema):
    schema = PatchOpSchema(resource_schema=user_schema)
    data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [
            {
                "op": "add",
                "path": "non.existing",
                "value": "John Doe",
            },
            {
                "op": "replace",
                "path": "non.existing",
                "value": "John Doe",
            },
            {
                "op": "remove",
                "path": "non.existing",
                "value": "John Doe",
            },
        ],
    }
    expected_issues = {
        "Operations": {
            "0": {"path": {"_errors": [{"code": 28}]}},
            "1": {"path": {"_errors": [{"code": 28}]}},
            "2": {"path": {"_errors": [{"code": 28}]}},
        }
    }

    issues = schema.validate(data, AttrValuePresenceConfig("REQUEST"))

    assert issues.to_dict() == expected_issues


def test_operation_value_is_validated_against_mutability_for_sub_attribute_in_extension(
    user_schema,
):
    schema = PatchOpSchema(resource_schema=user_schema)
    data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [
            {
                "op": "add",
                "value": {
                    "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
                        "manager": {"displayName": "John Doe"}
                    }
                },
            },
        ],
    }
    expected_issues = {
        "Operations": {
            "0": {
                "value": {
                    "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
                        "manager": {"displayName": {"_errors": [{"code": 29}]}}
                    }
                }
            },
        }
    }

    issues = schema.validate(data, AttrValuePresenceConfig("REQUEST"))

    assert issues.to_dict() == expected_issues


def test_operation_value_is_validated_against_mutability_for_attribute_in_extension():
    class MyResourceSchema(ResourceSchema):
        schema = "my:custom:schema"
        name = "MyResource"
        endpoint = "/MyResources"

    class MyExtension(SchemaExtension):
        schema = "my:custom:schema:extension"
        name = "MyResourceExtension"
        base_attrs = [String(name="my_attr", mutability=AttributeMutability.READ_ONLY)]

    my_resource = MyResourceSchema()
    my_resource.extend(MyExtension())
    schema = PatchOpSchema(resource_schema=my_resource)
    data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [
            {
                "op": "add",
                "value": {"my:custom:schema:extension": {"my_attr": "abc"}},
            },
        ],
    }
    expected_issues = {
        "Operations": {
            "0": {
                "value": {"my:custom:schema:extension": {"my_attr": {"_errors": [{"code": 29}]}}}
            },
        }
    }

    issues = schema.validate(data, AttrValuePresenceConfig("REQUEST"))

    assert issues.to_dict() == expected_issues


def test_operation_value_is_validated_against_mutability_for_sub_attribute_in_extension_with_path(
    user_schema,
):
    schema = PatchOpSchema(resource_schema=user_schema)
    data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [
            {
                "op": "add",
                "path": "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:manager",
                "value": {"displayName": "John Doe", "$ref": "/Users/10", "value": "10"},
            },
            {
                "op": "add",
                "path": "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:manager",
                "value": {"$ref": "/Users/10", "value": "10"},
            },
        ],
    }
    expected_issues = {
        "Operations": {"0": {"value": {"displayName": {"_errors": [{"code": 29}]}}}},
    }

    issues = schema.validate(data, AttrValuePresenceConfig("REQUEST"))

    assert issues.to_dict() == expected_issues


@pytest.mark.parametrize("op", ("add", "replace"))
def test_required_sub_attrs_are_checked_when_adding_or_replacing_multivalued_complex_items(
    op, fake_schema
):
    schema = PatchOpSchema(fake_schema)
    expected_issues = {
        "Operations": {
            "0": {
                "value": {
                    "0": {"bool": {"_errors": [{"code": 5}]}},
                    "2": {"bool": {"_errors": [{"code": 2}]}},
                }
            }
        }
    }

    issues = schema.validate(
        data={
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
def test_required_sub_attrs_are_checked_when_adding_or_replacing_multivalued_complex_attr(
    op, fake_schema
):
    schema = PatchOpSchema(fake_schema)

    expected_issues = {
        "Operations": {
            "0": {
                "value": {
                    "c2_mv": {
                        "0": {"bool": {"_errors": [{"code": 5}]}},
                        "2": {"bool": {"_errors": [{"code": 2}]}},
                    }
                }
            }
        }
    }

    issues = schema.validate(
        data={
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


@pytest.mark.parametrize("op", ("add", "replace"))
def test_required_sub_attrs_are_checked_when_adding_or_replacing_complex_attr(op, fake_schema):
    schema = PatchOpSchema(fake_schema)

    expected_issues = {"Operations": {"0": {"value": {"c2": {"bool": {"_errors": [{"code": 5}]}}}}}}

    issues = schema.validate(
        data={
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "Operations": [
                {
                    "op": op,
                    "value": {
                        "c2": {"str": "abc", "int": 123},
                    },
                }
            ],
        }
    )

    assert issues.to_dict() == expected_issues


def test_patch_op_deserialization_fails_if_bad_target(user_schema):
    schema = PatchOpSchema(user_schema)

    with pytest.raises(ValueError, match="target indicated by path .* does not exist"):
        schema.deserialize(
            data={
                "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
                "Operations": [{"op": "add", "path": "name.nonExisting", "value": "whatever"}],
            }
        )


def test_patch_path_operation_can_be_serialized(user_schema):
    schema = PatchOpSchema(user_schema)
    data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [{"op": "add", "path": "nickName", "value": "johndoe"}],
    }
    deserialized = schema.deserialize(data)

    actual = schema.serialize(deserialized)

    assert actual == data


def test_replace_operation_with_bad_complex_item_value_is_validated(user_schema):
    schema = PatchOpSchema(resource_schema=user_schema)
    expected_issues = {
        "Operations": {"0": {"value": {"_errors": [{"code": 2}]}}},
    }

    issues = schema.validate(
        {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "Operations": [
                {
                    "op": "replace",
                    "path": "emails[type eq 'home']",
                    "value": 42,
                }
            ],
        },
        AttrValuePresenceConfig("REQUEST"),
    )

    assert issues.to_dict() == expected_issues
