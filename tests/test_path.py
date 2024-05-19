from typing import Optional

import pytest

from src.assets.schemas import User
from src.container import AttrRep, BoundedAttrRep
from src.filter import Filter
from src.operator import ComplexAttributeOperator, Equal
from src.path import PatchPath
from src.schemas import BaseSchema
from tests.conftest import SchemaForTests


@pytest.mark.parametrize(
    ("path", "expected_issues"),
    (
        ("bad^attr", {"_errors": [{"code": 111, "context": {"attribute": "bad^attr"}}]}),
        (
            "good_attr.bad^sub_attr",
            {"_errors": [{"code": 111, "context": {"attribute": "good_attr.bad^sub_attr"}}]},
        ),
        ("attr[", {"_errors": [{"code": 300, "context": {}}]}),
        ("attr]", {"_errors": [{"code": 300, "context": {}}]}),
        ("attr[[]", {"_errors": [{"code": 300, "context": {}}]}),
        ("attr[]]", {"_errors": [{"code": 300, "context": {}}]}),
        ("attr[]", {"_errors": [{"code": 110, "context": {"attribute": "attr"}}]}),
        (
            "attr.sub_attr[value eq 1]",
            {"_errors": [{"code": 33, "context": {"attr": "attr", "sub_attr": "sub_attr"}}]},
        ),
        (
            "attr.sub_attr[value eq 1]",
            {"_errors": [{"code": 33, "context": {"attr": "attr", "sub_attr": "sub_attr"}}]},
        ),
        (
            "attr[value eq 1].sub_attr.sub_sub_attr",
            {"_errors": [{"code": 111, "context": {"attribute": "sub_attr.sub_sub_attr"}}]},
        ),
        (
            "attr[value eq]",
            {"_errors": [{"code": 104, "context": {"expression": "value eq", "operator": "eq"}}]},
        ),
        (
            "attr[eq 1]",
            {
                "_errors": [
                    {
                        "code": 105,
                        "context": {
                            "expression": "eq 1",
                            "operator": "1",
                            "operator_type": "unary",
                        },
                    }
                ]
            },
        ),
        ("attr[value eq abc]", {"_errors": [{"code": 112, "context": {"value": "abc"}}]}),
        (
            "attr.sub_attr[value eq abc].sub_attr.sub_sub_attr",
            {
                "_errors": [
                    {"code": 33, "context": {"attr": "attr", "sub_attr": "sub_attr"}},
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
    (
        "path",
        "expected_attr_rep",
        "expected_multivalued_filter",
        "expected_filter_sub_attr_rep",
    ),
    (
        ("members", BoundedAttrRep(attr="members"), None, None),
        ("name.familyName", BoundedAttrRep(attr="name", sub_attr="familyName"), None, None),
        (
            'addresses[type eq "work"]',
            BoundedAttrRep(attr="addresses"),
            Filter(
                ComplexAttributeOperator(
                    attr_rep=BoundedAttrRep(attr="addressed"),
                    sub_operator=Equal(AttrRep(attr="type"), "work"),
                )
            ),
            None,
        ),
        (
            'members[value eq "2819c223-7f76-453a-919d-413861904646"].displayName',
            BoundedAttrRep(attr="members"),
            Filter(
                ComplexAttributeOperator(
                    attr_rep=BoundedAttrRep(attr="members"),
                    sub_operator=Equal(
                        AttrRep(attr="value"),
                        "2819c223-7f76-453a-919d-413861904646",
                    ),
                )
            ),
            AttrRep(attr="displayName"),
        ),
    ),
)
def test_patch_path_parsing_success(
    path,
    expected_attr_rep: AttrRep,
    expected_multivalued_filter: Optional[Filter],
    expected_filter_sub_attr_rep: Optional[AttrRep],
):
    issues = PatchPath.validate(path)
    assert issues.to_dict(msg=True) == {}

    deserialized = PatchPath.deserialize(path)
    assert deserialized.attr_rep == expected_attr_rep
    if expected_multivalued_filter is not None:
        assert isinstance(deserialized.filter, type(expected_multivalued_filter))
        assert (
            deserialized.filter.operator.sub_operator.value
            == expected_multivalued_filter.operator.sub_operator.value
        )
        assert (
            deserialized.filter.operator.sub_operator.attr_rep
            == expected_multivalued_filter.operator.sub_operator.attr_rep
        )
    else:
        assert deserialized.filter is None
    assert deserialized.filter_sub_attr_rep == expected_filter_sub_attr_rep


@pytest.mark.parametrize(
    "kwargs",
    (
        {
            "attr_rep": BoundedAttrRep(attr="attr", sub_attr="sub_attr"),
            "filter_": Filter(
                ComplexAttributeOperator(
                    attr_rep=BoundedAttrRep(attr="attr"),
                    sub_operator=Equal(AttrRep(attr="sub_attr"), "whatever"),
                )
            ),
            "filter_sub_attr_rep": None,
        },
        {
            "attr_rep": BoundedAttrRep(attr="attr", sub_attr="sub_attr"),
            "filter_": Filter(
                ComplexAttributeOperator(
                    attr_rep=BoundedAttrRep(attr="attr"),
                    sub_operator=Equal(AttrRep(attr="sub_attr"), "whatever"),
                )
            ),
            "filter_sub_attr_rep": AttrRep(attr="other_attr"),
        },
        {
            "attr_rep": BoundedAttrRep(attr="attr"),
            "filter_": Filter(
                ComplexAttributeOperator(
                    attr_rep=BoundedAttrRep(attr="different_attr"),
                    sub_operator=Equal(AttrRep(attr="sub_attr"), "whatever"),
                )
            ),
            "filter_sub_attr_rep": AttrRep(attr="other_attr"),
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
    assert deserialized.filter.operator.sub_operator.value == expected_filter_value


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
