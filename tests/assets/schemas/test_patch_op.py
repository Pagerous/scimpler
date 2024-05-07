import pytest

from src.assets.schemas import User, patch_op, user
from src.data.container import (
    AttrRep,
    BoundedAttrRep,
    Invalid,
    Missing,
    SCIMDataContainer,
)
from src.data.operator import ComplexAttributeOperator, Equal
from src.data.path import PatchPath
from src.filter import Filter
from tests.conftest import SchemaForTests


@pytest.mark.parametrize(
    ("value", "expected_issues"),
    (
        (
            [
                SCIMDataContainer({"op": "add", "path": "userName", "value": "bjensen"}),
                SCIMDataContainer({"op": "unknown"}),
            ],
            {"1": {"op": {"_errors": [{"code": 14}]}}},
        ),
        (
            [
                SCIMDataContainer({"op": "add", "path": "userName", "value": "bjensen"}),
                SCIMDataContainer({"op": "remove", "path": None}),
            ],
            {"1": {"path": {"_errors": [{"code": 15}]}}},
        ),
        (
            [
                SCIMDataContainer({"op": "add", "path": "userName", "value": "bjensen"}),
                SCIMDataContainer({"op": "add", "value": None}),
            ],
            {"1": {"value": {"_errors": [{"code": 15}]}}},
        ),
        (
            [
                SCIMDataContainer({"op": "add", "path": "userName", "value": "bjensen"}),
                SCIMDataContainer(
                    {"op": "add", "path": 'emails[type eq "work"]', "value": {"primary": True}}
                ),
            ],
            {"1": {"path": {"_errors": [{"code": 305}]}}},
        ),
    ),
)
def test_validate_patch_operations(value, expected_issues):
    issues = patch_op.PatchOp(User).attrs.operations.validate(value)

    assert issues.to_dict() == expected_issues


@pytest.mark.parametrize(
    ("path", "expected_issues"),
    (
        (
            PatchPath(
                attr_rep=BoundedAttrRep(attr="nonexisting"),
                filter=None,
                filter_sub_attr_rep=None,
            ),
            {"_errors": [{"code": 303}]},
        ),
        (
            PatchPath(
                attr_rep=BoundedAttrRep(attr="non", sub_attr="existing"),
                filter=None,
                filter_sub_attr_rep=None,
            ),
            {"_errors": [{"code": 303}]},
        ),
        (
            PatchPath(
                attr_rep=BoundedAttrRep(attr="emails"),
                filter=Filter(
                    ComplexAttributeOperator(
                        attr_rep=BoundedAttrRep(attr="emails"),
                        sub_operator=Equal(
                            attr_rep=AttrRep(attr="nonexisting"),
                            value="whatever",
                        ),
                    )
                ),
                filter_sub_attr_rep=None,
            ),
            {},
        ),
        (
            PatchPath(
                attr_rep=BoundedAttrRep(attr="emails"),
                filter=Filter(
                    ComplexAttributeOperator(
                        attr_rep=BoundedAttrRep(attr="emails"),
                        sub_operator=Equal(attr_rep=AttrRep(attr="type"), value="whatever"),
                    ),
                ),
                filter_sub_attr_rep=AttrRep(attr="nonexisting"),
            ),
            {"_errors": [{"code": 303}]},
        ),
        (
            PatchPath(
                attr_rep=BoundedAttrRep(attr="emails"),
                filter=Filter(
                    ComplexAttributeOperator(
                        attr_rep=BoundedAttrRep(attr="emails"),
                        sub_operator=Equal(
                            attr_rep=AttrRep(attr="type"),
                            value="work",
                        ),
                    ),
                ),
                filter_sub_attr_rep=AttrRep(attr="value"),
            ),
            {},
        ),
        (
            PatchPath(
                attr_rep=BoundedAttrRep(attr="emails"),
                filter=Filter(
                    ComplexAttributeOperator(
                        attr_rep=BoundedAttrRep(attr="emails"),
                        sub_operator=Equal(attr_rep=AttrRep(attr="type"), value="work"),
                    )
                ),
                filter_sub_attr_rep=None,
            ),
            {},
        ),
        (
            PatchPath(
                attr_rep=BoundedAttrRep(attr="name", sub_attr="familyName"),
                filter=None,
                filter_sub_attr_rep=None,
            ),
            {},
        ),
        (
            PatchPath(
                attr_rep=BoundedAttrRep(attr="name"),
                filter=None,
                filter_sub_attr_rep=None,
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
                        "manager": {
                            "value": "Jan Kowalski",
                        },
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
                        "manager": {
                            "value": "Jan Kowalski",
                        },
                    },
                },
            }
        ],
    }

    issues = schema.validate(input_data)
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
                        "manager": {"displayName": {"_errors": [{"code": 2}, {"code": 304}]}},
                    },
                }
            }
        }
    }

    issues = schema.validate(input_data)
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
                    "meta": {
                        "_errors": [{"code": 304}],
                        "resourceType": {"_errors": [{"code": 17}, {"code": 304}]},
                    },
                }
            }
        }
    }

    issues = schema.validate(input_data)

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

    issues = schema.validate(input_data)

    assert issues.to_dict() == expected_issues


@pytest.mark.parametrize("op", ("add", "replace"))
@pytest.mark.parametrize(
    ("path", "expected_path", "value", "expected_value"),
    (
        (
            "userName",
            PatchPath(
                attr_rep=BoundedAttrRep(attr="userName"),
                filter=None,
                filter_sub_attr_rep=None,
            ),
            "bjensen",
            "bjensen",
        ),
        (
            "name.formatted",
            PatchPath(
                attr_rep=BoundedAttrRep(attr="name", sub_attr="formatted"),
                filter=None,
                filter_sub_attr_rep=None,
            ),
            "Jan Kowalski",
            "Jan Kowalski",
        ),
        (
            "name",
            PatchPath(
                attr_rep=BoundedAttrRep(attr="name"),
                filter=None,
                filter_sub_attr_rep=None,
            ),
            {"formatted": "Jan Kowalski", "familyName": "Kowalski"},
            SCIMDataContainer({"formatted": "Jan Kowalski", "familyName": "Kowalski"}),
        ),
        (
            "emails",
            PatchPath(
                attr_rep=BoundedAttrRep(attr="emails"),
                filter=None,
                filter_sub_attr_rep=None,
            ),
            [{"type": "work", "value": "work@example.com"}],
            [SCIMDataContainer({"type": "work", "value": "work@example.com"})],
        ),
        (
            'emails[type eq "work"].value',
            PatchPath(
                attr_rep=BoundedAttrRep(attr="emails"),
                filter=Filter(
                    ComplexAttributeOperator(
                        attr_rep=BoundedAttrRep(attr="emails"),
                        sub_operator=Equal(
                            attr_rep=AttrRep(attr="type"),
                            value="work",
                        ),
                    )
                ),
                filter_sub_attr_rep=AttrRep(attr="value"),
            ),
            "work@example.com",
            "work@example.com",
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

    issues = schema.validate(input_data)
    assert issues.to_dict(msg=True) == {}

    actual_data = schema.deserialize(input_data)
    assert actual_data.get("Operations")[0].get("value") == expected_value
    assert actual_data.get("Operations")[0].get("path").attr_rep == expected_path.attr_rep
    if expected_path.filter:
        assert actual_data.get("Operations")[0].get("path").filter == expected_path.filter
    if expected_path.filter_sub_attr_rep:
        assert (
            actual_data.get("Operations")[0].get("path").filter_sub_attr_rep
            == expected_path.filter_sub_attr_rep
        )


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
    expected_issues = {"Operations": {"0": {"value": {"_errors": [{"code": 304}]}}}}

    issues = schema.validate(input_data)

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

    assert schema.validate(input_data).to_dict(msg=True) == {}

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

    assert schema.validate(input_data).to_dict(msg=True) == {}

    actual_data = schema.deserialize(input_data)
    assert actual_data.to_dict() == expected_data


@pytest.mark.parametrize(
    ("path", "expected_path_issue_codes", "resource_schema"),
    (
        ("id", [{"code": 304}, {"code": 306}], user.User),
        ("userName", [{"code": 306}], user.User),
        (
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:manager.displayName",
            [{"code": 304}],
            user.User,
        ),
        ("meta", [{"code": 304}], user.User),
        ("groups", [{"code": 304}], user.User),
        ('groups[type eq "direct"].value', [{"code": 304}], user.User),
        ("c2_mv[int eq 1].bool", [{"code": 306}], SchemaForTests),
    ),
)
def test_remove_operation__fails_if_attribute_is_readonly_or_required(
    path, expected_path_issue_codes, resource_schema
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

    assert schema.validate(input_data).to_dict() == expected_issues
    assert schema.deserialize(input_data).to_dict() == expected_data
