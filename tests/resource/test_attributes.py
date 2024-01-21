import pytest

from src.resource.attributes.patch_op import operations


@pytest.mark.parametrize(
    ("value", "expected_issues"),
    (
        (
            [{"op": "add", "path": "userName", "value": "bjensen"}, {"op": "unknown"}],
            {"1": {"op": {"_errors": [{"code": 14}]}}},
        ),
        (
            [{"op": "add", "path": "userName", "value": "bjensen"}, {"op": "remove", "path": None}],
            {"1": {"path": {"_errors": [{"code": 15}]}}},
        ),
        (
            [{"op": "add", "path": "userName", "value": "bjensen"}, {"op": "add", "value": None}],
            {"1": {"value": {"_errors": [{"code": 15}]}}},
        ),
        (
            [
                {"op": "add", "path": "userName", "value": "bjensen"},
                {"op": "add", "path": 'emails[type eq "work"]', "value": {"primary": True}},
            ],
            {"1": {"path": {"_errors": [{"code": 305}]}}},
        ),
    ),
)
def test_parse_patch_operations(value, expected_issues):
    parsed, issues = operations.parse(value)

    assert parsed is None
    assert issues.to_dict() == expected_issues
