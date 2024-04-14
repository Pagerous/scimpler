from typing import Optional

import pytest

from src.data.container import AttrRep
from src.data.operator import ComplexAttributeOperator, Equal
from src.data.path import PatchPath
from src.filter import Filter


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
            {"_errors": [{"code": 33, "context": {"attr": "attr", "sub_attr": "sub_attr"}}]},
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
        PatchPath.parse(path)


@pytest.mark.parametrize(
    (
        "path",
        "expected_attr_rep",
        "expected_multivalued_filter",
        "expected_complex_filter_attr_rep",
    ),
    (
        ("members", AttrRep(attr="members"), None, None),
        ("name.familyName", AttrRep(attr="name", sub_attr="familyName"), None, None),
        (
            'addresses[type eq "work"]',
            AttrRep(attr="addresses"),
            Filter(
                ComplexAttributeOperator(
                    attr_rep=AttrRep(attr="addressed"),
                    sub_operator=Equal(AttrRep(attr="type"), "work"),
                )
            ),
            None,
        ),
        (
            'members[value eq "2819c223-7f76-453a-919d-413861904646"].displayName',
            AttrRep(attr="members"),
            Filter(
                ComplexAttributeOperator(
                    attr_rep=AttrRep(attr="members"),
                    sub_operator=Equal(
                        AttrRep(attr="value"),
                        "2819c223-7f76-453a-919d-413861904646",
                    ),
                )
            ),
            AttrRep(attr="members", sub_attr="displayName"),
        ),
    ),
)
def test_patch_path_parsing_success(
    path,
    expected_attr_rep: AttrRep,
    expected_multivalued_filter: Optional[Filter],
    expected_complex_filter_attr_rep: Optional[AttrRep],
):
    issues = PatchPath.validate(path)
    assert issues.to_dict(msg=True) == {}

    parsed = PatchPath.parse(path)
    assert parsed.attr_rep == expected_attr_rep
    if expected_multivalued_filter is not None:
        assert isinstance(parsed.complex_filter, type(expected_multivalued_filter))
        assert (
            parsed.complex_filter.operator.sub_operator.value
            == expected_multivalued_filter.operator.sub_operator.value
        )
        assert (
            parsed.complex_filter.operator.sub_operator.attr_rep
            == expected_multivalued_filter.operator.sub_operator.attr_rep
        )
    else:
        assert parsed.complex_filter is None
    assert parsed.complex_filter_attr_rep == expected_complex_filter_attr_rep


@pytest.mark.parametrize(
    "kwargs",
    (
        {
            "attr_rep": AttrRep(attr="attr", sub_attr="sub_attr"),
            "complex_filter": Filter(
                ComplexAttributeOperator(
                    attr_rep=AttrRep(attr="attr"),
                    sub_operator=Equal(AttrRep(attr="sub_attr"), "whatever"),
                )
            ),
            "complex_filter_attr_rep": None,
        },
        {
            "attr_rep": AttrRep(attr="attr", sub_attr="sub_attr"),
            "complex_filter": Filter(
                ComplexAttributeOperator(
                    attr_rep=AttrRep(attr="attr"),
                    sub_operator=Equal(AttrRep(attr="sub_attr"), "whatever"),
                )
            ),
            "complex_filter_attr_rep": AttrRep(attr="attr", sub_attr="other_attr"),
        },
        {
            "attr_rep": AttrRep(attr="attr", sub_attr="sub_attr"),
            "complex_filter": Filter(
                ComplexAttributeOperator(
                    attr_rep=AttrRep(attr="attr"),
                    sub_operator=Equal(AttrRep(attr="attr"), "whatever"),
                )
            ),
            "complex_filter_attr_rep": AttrRep(attr="attr", sub_attr="other_attr"),
        },
        {
            "attr_rep": AttrRep(attr="attr", sub_attr="sub_attr"),
            "complex_filter": Filter(
                ComplexAttributeOperator(
                    attr_rep=AttrRep(attr="attr"),
                    sub_operator=Equal(AttrRep(attr="sub_attr"), "whatever"),
                )
            ),
            "complex_filter_attr_rep": AttrRep(attr="attr"),
        },
        {
            "attr_rep": AttrRep(attr="attr"),
            "complex_filter": Filter(
                ComplexAttributeOperator(
                    attr_rep=AttrRep(attr="different_attr"),
                    sub_operator=Equal(AttrRep(attr="sub_attr"), "whatever"),
                )
            ),
            "complex_filter_attr_rep": AttrRep(attr="attr", sub_attr="other_attr"),
        },
        {
            "attr_rep": AttrRep(attr="attr"),
            "complex_filter": Filter(
                ComplexAttributeOperator(
                    attr_rep=AttrRep(attr="attr"),
                    sub_operator=Equal(AttrRep(attr="sub_attr"), "whatever"),
                )
            ),
            "complex_filter_attr_rep": AttrRep(attr="different_attr", sub_attr="other_attr"),
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

    parsed = PatchPath.parse(path)
    assert parsed.complex_filter.operator.sub_operator.value == expected_filter_value
