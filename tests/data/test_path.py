import pytest

from src.assets.schemas import User
from src.container import AttrRep, BoundedAttrRep
from src.data.filter import Filter
from src.data.operator import ComplexAttributeOperator, Equal
from src.data.path import PatchPath
from src.schema.schemas import BaseSchema
from tests.conftest import SchemaForTests


@pytest.mark.parametrize(
    ("path", "expected_issues"),
    (
        ("bad^attr", {"_errors": [{"code": 17, "context": {"attribute": "bad^attr"}}]}),
        (
            "good_attr.bad^sub_attr",
            {"_errors": [{"code": 17, "context": {"attribute": "good_attr.bad^sub_attr"}}]},
        ),
        ("attr[", {"_errors": [{"code": 1, "context": {}}]}),
        ("attr]", {"_errors": [{"code": 1, "context": {}}]}),
        ("attr[[]", {"_errors": [{"code": 1, "context": {}}]}),
        ("attr[]]", {"_errors": [{"code": 1, "context": {}}]}),
        ("attr[]", {"_errors": [{"code": 108, "context": {"attribute": "attr"}}]}),
        (
            "attr.sub_attr[value eq 1]",
            {"_errors": [{"code": 102, "context": {"attr": "attr", "sub_attr": "sub_attr"}}]},
        ),
        (
            "attr.sub_attr[value eq 1]",
            {"_errors": [{"code": 102, "context": {"attr": "attr", "sub_attr": "sub_attr"}}]},
        ),
        (
            "attr[value eq 1].sub_attr.sub_sub_attr",
            {"_errors": [{"code": 17, "context": {"attribute": "sub_attr.sub_sub_attr"}}]},
        ),
        (
            "attr[value eq]",
            {"_errors": [{"code": 103, "context": {"expression": "value eq", "operator": "eq"}}]},
        ),
        (
            "attr[eq 1]",
            {
                "_errors": [
                    {
                        "code": 104,
                        "context": {
                            "expression": "eq 1",
                            "operator": "1",
                        },
                    }
                ]
            },
        ),
        ("attr[value eq abc]", {"_errors": [{"code": 109, "context": {"value": "abc"}}]}),
        (
            "attr.sub_attr[value eq abc].sub_attr.sub_sub_attr",
            {
                "_errors": [
                    {"code": 102, "context": {"attr": "attr", "sub_attr": "sub_attr"}},
                ]
            },
        ),
    ),
)
def test_patch_path_parsing_failure(path, expected_issues):
    issues = PatchPath.validate(path)
    assert issues.to_dict(ctx=True) == expected_issues

    with pytest.raises(ValueError, match="invalid path expression"):
        PatchPath.deserialize(path)


@pytest.mark.parametrize(
    ("path", "expected"),
    (
        (
            "members",
            PatchPath(
                attr_rep=BoundedAttrRep(attr="members"),
                sub_attr_rep=None,
                filter_=None,
            ),
        ),
        (
            "name.familyName",
            PatchPath(
                attr_rep=BoundedAttrRep(attr="name"),
                sub_attr_rep=AttrRep(attr="familyName"),
                filter_=None,
            ),
        ),
        (
            'addresses[type eq "work"]',
            PatchPath(
                attr_rep=BoundedAttrRep(attr="addresses"),
                sub_attr_rep=None,
                filter_=Filter(
                    ComplexAttributeOperator(
                        attr_rep=BoundedAttrRep(attr="addresses"),
                        sub_operator=Equal(AttrRep(attr="type"), "work"),
                    )
                ),
            ),
        ),
        (
            'members[value eq "2819c223-7f76-453a-919d-413861904646"].displayName',
            PatchPath(
                attr_rep=BoundedAttrRep(attr="members"),
                sub_attr_rep=AttrRep(attr="displayName"),
                filter_=Filter(
                    ComplexAttributeOperator(
                        attr_rep=BoundedAttrRep(attr="members"),
                        sub_operator=Equal(
                            AttrRep(attr="value"),
                            "2819c223-7f76-453a-919d-413861904646",
                        ),
                    )
                ),
            ),
        ),
    ),
)
def test_patch_path_deserialization_success(path, expected):
    issues = PatchPath.validate(path)
    assert issues.to_dict(msg=True) == {}

    deserialized = PatchPath.deserialize(path)
    assert deserialized == expected


@pytest.mark.parametrize(
    "kwargs",
    (
        {
            "attr_rep": BoundedAttrRep(attr="attr", sub_attr="sub_attr"),
            "sub_attr_rep": None,
            "filter_": Filter(
                ComplexAttributeOperator(
                    attr_rep=BoundedAttrRep(attr="attr"),
                    sub_operator=Equal(AttrRep(attr="sub_attr"), "whatever"),
                )
            ),
        },
        {
            "attr_rep": BoundedAttrRep(attr="attr"),
            "sub_attr_rep": AttrRep(attr="other_attr"),
            "filter_": Filter(
                ComplexAttributeOperator(
                    attr_rep=BoundedAttrRep(attr="different_attr"),
                    sub_operator=Equal(AttrRep(attr="sub_attr"), "whatever"),
                )
            ),
        },
    ),
)
def test_patch_path_object_construction_fails_if_broken_constraints(kwargs):
    with pytest.raises(ValueError):
        PatchPath(**kwargs)


@pytest.mark.parametrize(
    ("path", "expected_filter_value"),
    (
        (
            'emails[value eq "id eq 1 and attr neq 2"]',
            "id eq 1 and attr neq 2",
        ),
        ('emails[value eq "ims[type eq "work"]"]', 'ims[type eq "work"]'),
    ),
)
def test_complex_filter_string_values_can_contain_anything(path, expected_filter_value):
    issues = PatchPath.validate(path)
    assert issues.to_dict(msg=True) == {}

    deserialized = PatchPath.deserialize(path)
    assert deserialized({"value": expected_filter_value}, User)


@pytest.mark.parametrize(
    ("path", "data", "schema", "expected"),
    (
        (
            PatchPath.deserialize("name.formatted"),
            "John Doe",
            User,
            True,
        ),
        (
            PatchPath.deserialize("emails[type eq 'work']"),
            {"type": "work", "value": "my@example.com"},
            User,
            True,
        ),
        (
            PatchPath.deserialize("emails[type eq 'work']"),
            42,
            User,
            False,
        ),
        (
            PatchPath.deserialize("emails[type eq 'work']"),
            {"type": "home", "value": "my@example.com"},
            User,
            False,
        ),
        (
            PatchPath.deserialize("emails[type eq 'work'].display"),
            "MY@EXAMPLE.COM",
            User,
            False,
        ),
        (
            PatchPath.deserialize("str_mv[value sw 'a']"),
            "abc",
            SchemaForTests,
            True,
        ),
        (
            PatchPath.deserialize("str_mv[value sw 'a']"),
            "cba",
            SchemaForTests,
            False,
        ),
        (
            PatchPath.deserialize("str_mv[value sw 'a' or value ew 'a']"),
            "cba",
            SchemaForTests,
            True,
        ),
        (
            PatchPath.deserialize("str_mv[value sw 'a']"),
            {"bad": "value"},
            SchemaForTests,
            False,
        ),
    ),
)
def test_check_if_data_matches_path(path, data, schema: BaseSchema, expected):
    actual = path(data, schema)

    assert actual is expected
