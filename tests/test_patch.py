from typing import Optional

import pytest

from src.data.container import AttrRep
from src.filter.operator import Equal
from src.patch import PatchPath


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
        ("attr[]", {"_errors": [{"code": 302, "context": {}}]}),
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
        ("attr[value neq 1]", {"_errors": [{"code": 301, "context": {}}]}),
        ("attr[value eq]", {"_errors": [{"code": 302, "context": {}}]}),
        ("attr[eq 1]", {"_errors": [{"code": 302, "context": {}}]}),
        ("attr[value eq abc]", {"_errors": [{"code": 112, "context": {"value": "abc"}}]}),
        (
            "attr.sub_attr[value eq abc].sub_attr.sub_sub_attr",
            {
                "_errors": [
                    {"code": 33, "context": {"attr": "attr", "sub_attr": "sub_attr"}},
                    {"code": 112, "context": {"value": "abc"}},
                    {"code": 33, "context": {"attr": "attr", "sub_attr": "sub_attr"}},
                ]
            },
        ),
    ),
)
def test_patch_path_parsing_failure(path, expected_issues):
    parsed, issues = PatchPath.parse(path)

    assert parsed is None
    assert issues.to_dict(ctx=True) == expected_issues


@pytest.mark.parametrize(
    ("path", "expected_attr_rep", "expected_multivalued_filter", "expected_value_sub_attr_rep"),
    (
        ("members", AttrRep(attr="members"), None, None),
        ("name.familyName", AttrRep(attr="name", sub_attr="familyName"), None, None),
        (
            'addresses[type eq "work"]',
            AttrRep(attr="addresses"),
            Equal(AttrRep(attr="addresses", sub_attr="type"), "work"),
            None,
        ),
        (
            'members[value eq "2819c223-7f76-453a-919d-413861904646"].displayName',
            AttrRep(attr="members"),
            Equal(
                AttrRep(attr="members", sub_attr="value"),
                "2819c223-7f76-453a-919d-413861904646",
            ),
            AttrRep(attr="members", sub_attr="displayName"),
        ),
    ),
)
def test_patch_path_parsing_success(
    path,
    expected_attr_rep: AttrRep,
    expected_multivalued_filter: Optional[Equal],
    expected_value_sub_attr_rep: Optional[AttrRep],
):
    parsed, issues = PatchPath.parse(path)

    assert not issues
    assert parsed.attr_rep == expected_attr_rep
    if expected_multivalued_filter is not None:
        assert isinstance(parsed.complex_filter, type(expected_multivalued_filter))
        assert parsed.complex_filter.value == expected_multivalued_filter.value
        assert parsed.complex_filter.attr_rep == expected_multivalued_filter.attr_rep
    else:
        assert parsed.complex_filter is None
    assert parsed.complex_filter_attr_rep == expected_value_sub_attr_rep


@pytest.mark.parametrize(
    "kwargs",
    (
        {
            "attr_rep": AttrRep(attr="attr", sub_attr="sub_attr"),
            "complex_filter": Equal(AttrRep(attr="attr", sub_attr="sub_attr"), "whatever"),
            "complex_filter_attr_rep": None,
        },
        {
            "attr_rep": AttrRep(attr="attr", sub_attr="sub_attr"),
            "complex_filter": Equal(AttrRep(attr="attr", sub_attr="sub_attr"), "whatever"),
            "complex_filter_attr_rep": AttrRep(attr="attr", sub_attr="other_attr"),
        },
        {
            "attr_rep": AttrRep(attr="attr", sub_attr="sub_attr"),
            "complex_filter": Equal(AttrRep(attr="attr"), "whatever"),
            "complex_filter_attr_rep": AttrRep(attr="attr", sub_attr="other_attr"),
        },
        {
            "attr_rep": AttrRep(attr="attr", sub_attr="sub_attr"),
            "complex_filter": Equal(AttrRep(attr="attr", sub_attr="sub_attr"), "whatever"),
            "complex_filter_attr_rep": AttrRep(attr="attr"),
        },
        {
            "attr_rep": AttrRep(attr="attr"),
            "complex_filter": Equal(
                AttrRep(attr="different_attr", sub_attr="sub_attr"), "whatever"
            ),
            "complex_filter_attr_rep": AttrRep(attr="attr", sub_attr="other_attr"),
        },
        {
            "attr_rep": AttrRep(attr="attr"),
            "complex_filter": Equal(AttrRep(attr="attr", sub_attr="sub_attr"), "whatever"),
            "complex_filter_attr_rep": AttrRep(attr="different_attr", sub_attr="other_attr"),
        },
    ),
)
def test_patch_path_object_construction_fails_if_broken_constraints(kwargs):
    with pytest.raises(ValueError):
        PatchPath(**kwargs)
