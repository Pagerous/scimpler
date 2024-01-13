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
        ("attr", AttributeName(attr="attr"), None, None),
        ("attr.sub_attr", AttributeName(attr="attr", sub_attr="sub_attr"), None, None),
        (
            "attr[sub_attr eq 1]",
            AttributeName(attr="attr"),
            Equal(AttributeName(attr="attr", sub_attr="sub_attr"), 1),
            None,
        ),
        (
            "attr[sub_attr eq 1].other_sub_attr",
            AttributeName(attr="attr"),
            Equal(AttributeName(attr="sub_attr"), 1),
            AttributeName(attr="attr", sub_attr="other_sub_attr"),
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
        assert isinstance(parsed.multivalued_filter, type(expected_multivalued_filter))
        assert parsed.multivalued_filter.value == expected_multivalued_filter.value
    else:
        assert parsed.multivalued_filter is None
    assert parsed.value_sub_attr_name == expected_value_sub_attr_name
