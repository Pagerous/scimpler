from typing import Optional

import pytest

from src.attributes.attributes import AttributeName
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
    ("path", "expected_attr_name", "expected_multivalued_filter", "expected_value_sub_attr_name"),
    (
        ("members", AttributeName(attr="members"), None, None),
        ("name.familyName", AttributeName(attr="name", sub_attr="familyName"), None, None),
        (
            'addresses[type eq "work"]',
            AttributeName(attr="addresses"),
            Equal(AttributeName(attr="addresses", sub_attr="type"), "work"),
            None,
        ),
        (
            'members[value eq "2819c223-7f76-453a-919d-413861904646"].displayName',
            AttributeName(attr="members"),
            Equal(
                AttributeName(attr="members", sub_attr="value"),
                "2819c223-7f76-453a-919d-413861904646",
            ),
            AttributeName(attr="members", sub_attr="displayName"),
        ),
    ),
)
def test_patch_path_parsing_success(
    path,
    expected_attr_name: AttributeName,
    expected_multivalued_filter: Optional[Equal],
    expected_value_sub_attr_name: Optional[AttributeName],
):
    parsed, issues = PatchPath.parse(path)

    assert not issues
    assert parsed.attr_name == expected_attr_name
    if expected_multivalued_filter is not None:
        assert isinstance(parsed.complex_filter, type(expected_multivalued_filter))
        assert parsed.complex_filter.value == expected_multivalued_filter.value
        assert parsed.complex_filter.attr_name == expected_multivalued_filter.attr_name
    else:
        assert parsed.complex_filter is None
    assert parsed.complex_filter_attr_name == expected_value_sub_attr_name


@pytest.mark.parametrize(
    "kwargs",
    (
        {
            "attr_name": AttributeName(attr="attr", sub_attr="sub_attr"),
            "complex_filter": Equal(AttributeName(attr="attr", sub_attr="sub_attr"), "whatever"),
            "complex_filter_attr_name": None,
        },
        {
            "attr_name": AttributeName(attr="attr", sub_attr="sub_attr"),
            "complex_filter": Equal(AttributeName(attr="attr", sub_attr="sub_attr"), "whatever"),
            "complex_filter_attr_name": AttributeName(attr="attr", sub_attr="other_attr"),
        },
        {
            "attr_name": AttributeName(attr="attr", sub_attr="sub_attr"),
            "complex_filter": Equal(AttributeName(attr="attr"), "whatever"),
            "complex_filter_attr_name": AttributeName(attr="attr", sub_attr="other_attr"),
        },
        {
            "attr_name": AttributeName(attr="attr", sub_attr="sub_attr"),
            "complex_filter": Equal(AttributeName(attr="attr", sub_attr="sub_attr"), "whatever"),
            "complex_filter_attr_name": AttributeName(attr="attr"),
        },
        {
            "attr_name": AttributeName(attr="attr"),
            "complex_filter": Equal(
                AttributeName(attr="different_attr", sub_attr="sub_attr"), "whatever"
            ),
            "complex_filter_attr_name": AttributeName(attr="attr", sub_attr="other_attr"),
        },
        {
            "attr_name": AttributeName(attr="attr"),
            "complex_filter": Equal(AttributeName(attr="attr", sub_attr="sub_attr"), "whatever"),
            "complex_filter_attr_name": AttributeName(attr="different_attr", sub_attr="other_attr"),
        },
    ),
)
def test_patch_path_object_construction_fails_if_broken_constraints(kwargs):
    with pytest.raises(ValueError):
        PatchPath(**kwargs)
