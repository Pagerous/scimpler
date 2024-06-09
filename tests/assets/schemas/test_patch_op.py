import pytest

from src.assets.schemas import User, patch_op, user
from src.container import AttrName, AttrRep, Invalid, Missing, SCIMDataContainer
from src.data.attr_presence import AttrPresenceConfig
from src.data.attrs import AttributeMutability, String
from src.data.filter import Filter
from src.data.operator import ComplexAttributeOperator, Equal
from src.data.patch_path import PatchPath
from src.data.schemas import ResourceSchema, SchemaExtension
from tests.conftest import SchemaForTests


@pytest.mark.parametrize(
    ("value", "expected_issues"),
    (
        (
            [
                SCIMDataContainer({"op": "add", "path": "userName", "value": "bjensen"}),
                SCIMDataContainer({"op": "unknown"}),
            ],
            {"1": {"op": {"_errors": [{"code": 9}]}}},
        ),
        (
            [
                SCIMDataContainer({"op": "add", "path": "userName", "value": "bjensen"}),
                SCIMDataContainer({"op": "remove", "path": None}),
            ],
            {"1": {"path": {"_errors": [{"code": 5}]}}},
        ),
        (
            [
                SCIMDataContainer({"op": "add", "path": "userName", "value": "bjensen"}),
                SCIMDataContainer({"op": "add", "value": None}),
            ],
            {"1": {"value": {"_errors": [{"code": 5}]}}},
        ),
    ),
)
def test_validate_patch_operations(value, expected_issues):
    issues = patch_op.PatchOp(User).attrs.get("operations").validate(value)

    assert issues.to_dict() == expected_issues


@pytest.mark.parametrize(
    ("path", "expected_issues"),
    (
        (
            PatchPath(
                attr_rep=AttrRep(attr="nonexisting"),
                sub_attr_name=None,
                filter_=None,
            ),
            {"_errors": [{"code": 28}]},
        ),
        (
            PatchPath(
                attr_rep=AttrRep(attr="non"),
                sub_attr_name=AttrName("existing"),
                filter_=None,
            ),
            {"_errors": [{"code": 28}]},
        ),
        (
            PatchPath(
                attr_rep=AttrRep(attr="emails"),
                sub_attr_name=None,
                filter_=Filter(
                    ComplexAttributeOperator(
                        attr_rep=AttrRep(attr="emails"),
                        sub_operator=Equal(
                            attr_rep=AttrRep(attr="nonexisting"),
                            value="whatever",
                        ),
                    )
                ),
            ),
            {},
        ),
        (
            PatchPath(
                attr_rep=AttrRep(attr="emails"),
                sub_attr_name=AttrName("nonexisting"),
                filter_=Filter(
                    ComplexAttributeOperator(
                        attr_rep=AttrRep(attr="emails"),
                        sub_operator=Equal(attr_rep=AttrRep(attr="type"), value="whatever"),
                    ),
                ),
            ),
            {"_errors": [{"code": 28}]},
        ),
        (
            PatchPath(
                attr_rep=AttrRep(attr="name"),
                sub_attr_name=None,
                filter_=Filter(
                    ComplexAttributeOperator(
                        attr_rep=AttrRep(attr="name"),
                        sub_operator=Equal(attr_rep=AttrRep(attr="formatted"), value="whatever"),
                    ),
                ),
            ),
            {"_errors": [{"code": 28}]},
        ),
        (
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
                    ),
                ),
            ),
            {},
        ),
        (
            PatchPath(
                attr_rep=AttrRep(attr="emails"),
                sub_attr_name=None,
                filter_=Filter(
                    ComplexAttributeOperator(
                        attr_rep=AttrRep(attr="emails"),
                        sub_operator=Equal(attr_rep=AttrRep(attr="type"), value="work"),
                    )
                ),
            ),
            {},
        ),
        (
            PatchPath(
                attr_rep=AttrRep(attr="name"),
                sub_attr_name=AttrName("familyName"),
                filter_=None,
            ),
            {},
        ),
        (
            PatchPath(
                attr_rep=AttrRep(attr="name"),
                sub_attr_name=None,
                filter_=None,
            ),
            {},
        ),
    ),
)
def test_validate_operation_path(path, expected_issues):
    issues = patch_op.validate_operation_path(schema=user.User, path=path)

    assert issues.to_dict() == expected_issues


@pytest.mark.parametrize("op", ("add", "replace"))
def test_patch_op__add_and_replace_operation_without_path_can_be_deserialized(op):
    schema = patch_op.PatchOp(resource_schema=user.User)
    input_data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [
            {
                "op": op,
                "value": {
                    "ignore^me": 42,
                    "name": {
                        "formatted": "Ms. Barbara J Jensen III",
                        "ignore^me": 42,
                    },
                    "userName": "bjensen",
                    "emails": [{"value": "bjensen@example.com", "type": "work"}],
                    "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
                        "ignore^me": 42,
                        "department": "Tour Operations",
                        "manager": {"value": "10", "$ref": "/Users/10"},
                    },
                },
            }
        ],
    }
    expected_data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [
            {
                "op": op,
                "path": Missing,
                "value": {
                    "name": {
                        "formatted": "Ms. Barbara J Jensen III",
                    },
                    "userName": "bjensen",
                    "emails": [{"value": "bjensen@example.com", "type": "work"}],
                    "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
                        "department": "Tour Operations",
                        "manager": {"value": "10", "$ref": "/Users/10"},
                    },
                },
            }
        ],
    }

    issues = schema.validate(input_data, AttrPresenceConfig("REQUEST"))
    assert issues.to_dict(msg=True) == {}

    actual_data = schema.deserialize(input_data)
    assert actual_data.to_dict() == expected_data


@pytest.mark.parametrize("op", ("add", "replace"))
def test_validate_add_and_replace_operation_without_path__fails_for_incorrect_data(op):
    schema = patch_op.PatchOp(resource_schema=user.User)
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

    issues = schema.validate(input_data, AttrPresenceConfig("REQUEST"))
    assert issues.to_dict() == expected_issues


@pytest.mark.parametrize("op", ("add", "replace"))
def test_validate_add_and_replace_operation_without_path__fails_if_attribute_is_readonly(op):
    schema = patch_op.PatchOp(resource_schema=user.User)
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

    issues = schema.validate(input_data, AttrPresenceConfig("REQUEST"))

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
    op, path, input_value, expected_value, expected_value_issues
):
    schema = patch_op.PatchOp(resource_schema=user.User)
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

    issues = schema.validate(input_data, AttrPresenceConfig("REQUEST"))

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
            SCIMDataContainer({"formatted": "Jan Kowalski", "familyName": "Kowalski"}),
        ),
        (
            "emails",
            PatchPath(
                attr_rep=AttrRep(attr="emails"),
                sub_attr_name=None,
                filter_=None,
            ),
            [{"type": "work", "value": "work@example.com"}],
            [SCIMDataContainer({"type": "work", "value": "work@example.com"})],
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
    op, path, expected_path, value, expected_value
):
    schema = patch_op.PatchOp(resource_schema=user.User)
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

    issues = schema.validate(input_data, AttrPresenceConfig("REQUEST"))
    assert issues.to_dict(msg=True) == {}

    actual_data = schema.deserialize(input_data)
    assert actual_data.get("Operations")[0].get("value") == expected_value
    assert actual_data.get("Operations")[0].get("path") == expected_path


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
def test_add_operation__fails_if_attribute_is_readonly(op, path, value):
    schema = patch_op.PatchOp(resource_schema=user.User)
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

    issues = schema.validate(input_data, AttrPresenceConfig("REQUEST"))

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
def test_remove_operation__succeeds_if_correct_path(path):
    schema = patch_op.PatchOp(resource_schema=user.User)
    input_data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [
            {
                "op": "remove",
                "path": path,
            }
        ],
    }
    expected_data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [{"op": "remove", "path": PatchPath.deserialize(path)}],
    }

    assert schema.validate(input_data, AttrPresenceConfig("REQUEST")).to_dict(msg=True) == {}

    actual_data = schema.deserialize(input_data)
    assert actual_data.to_dict() == expected_data


def test_remove_operation__path_can_point_at_item_of_simple_multivalued_attribute():
    schema = patch_op.PatchOp(resource_schema=SchemaForTests)
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
    expected_data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [{"op": "remove", "path": PatchPath.deserialize(path)}],
    }

    assert schema.validate(input_data, AttrPresenceConfig("REQUEST")).to_dict(msg=True) == {}

    actual_data = schema.deserialize(input_data)
    assert actual_data.to_dict() == expected_data


@pytest.mark.parametrize(
    ("path", "expected_path_issue_codes", "resource_schema"),
    (
        ("id", [{"code": 29}, {"code": 30}], user.User),
        ("userName", [{"code": 30}], user.User),
        (
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:manager.displayName",
            [{"code": 29}],
            user.User,
        ),
        ("meta", [{"code": 29}], user.User),
        ("groups", [{"code": 29}], user.User),
        ('groups[type eq "direct"].value', [{"code": 29}], user.User),
        ("c2_mv[int eq 1].bool", [{"code": 30}], SchemaForTests),
    ),
)
def test_remove_operation__fails_if_attribute_is_readonly_or_required(
    path, expected_path_issue_codes, resource_schema: ResourceSchema
):
    schema = patch_op.PatchOp(resource_schema)
    input_data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [
            {
                "op": "remove",
                "path": path,
            }
        ],
    }
    expected_data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [{"op": "remove", "path": PatchPath.deserialize(path)}],
    }
    expected_issues = {"Operations": {"0": {"path": {"_errors": expected_path_issue_codes}}}}

    assert schema.validate(input_data, AttrPresenceConfig("REQUEST")).to_dict() == expected_issues
    assert schema.deserialize(input_data).to_dict() == expected_data


def test_validate_empty_body():
    schema = patch_op.PatchOp(resource_schema=user.User)
    expected_issues = {
        "schemas": {"_errors": [{"code": 5}]},
        "Operations": {"_errors": [{"code": 5}]},
    }

    issues = schema.validate({}, AttrPresenceConfig("REQUEST"))

    assert issues.to_dict() == expected_issues


def test_value_is_removed_if_remove_operation_during_deserialization():
    schema = patch_op.PatchOp(resource_schema=user.User)
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

    assert "value" in deserialized.get("Operations")[0].to_dict()
    assert "value" not in deserialized.get("Operations")[1].to_dict()


def test_operation_value_is_not_validated_if_bad_path():
    schema = patch_op.PatchOp(resource_schema=user.User)
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

    issues = schema.validate(data, AttrPresenceConfig("REQUEST"))

    assert issues.to_dict() == expected_issues


def test_operation_value_is_validated_against_mutability_for_sub_attribute_in_extension():
    schema = patch_op.PatchOp(resource_schema=user.User)
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

    issues = schema.validate(data, AttrPresenceConfig("REQUEST"))

    assert issues.to_dict() == expected_issues


def test_operation_value_is_validated_against_mutability_for_attribute_in_extension():
    my_resource = ResourceSchema(
        schema="my:custom:schema",
        name="MyResource",
    )
    my_resource.extend(
        extension=SchemaExtension(
            schema="my:custom:schema:extension",
            name="MyResourceExtension",
            attrs=[String(name="my_attr", mutability=AttributeMutability.READ_ONLY)],
        )
    )
    schema = patch_op.PatchOp(resource_schema=my_resource)
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

    issues = schema.validate(data, AttrPresenceConfig("REQUEST"))

    assert issues.to_dict() == expected_issues


def test_operation_value_is_validated_against_mutability_for_sub_attribute_in_extension_with_path():
    schema = patch_op.PatchOp(resource_schema=user.User)
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

    issues = schema.validate(data, AttrPresenceConfig("REQUEST"))

    assert issues.to_dict() == expected_issues


@pytest.mark.parametrize("op", ("add", "replace"))
def test_required_sub_attrs_are_checked_when_adding_or_replacing_multivalued_complex_items(op):
    schema = patch_op.PatchOp(SchemaForTests)
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
def test_required_sub_attrs_are_checked_when_adding_or_replacing_multivalued_complex_attr(op):
    schema = patch_op.PatchOp(SchemaForTests)

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
def test_required_sub_attrs_are_checked_when_adding_or_replacing_complex_attr(op):
    schema = patch_op.PatchOp(SchemaForTests)

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
