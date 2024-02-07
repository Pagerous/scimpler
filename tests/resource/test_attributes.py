import pytest

from src.data.container import SCIMDataContainer
from src.resource.schemas.patch_op import operations


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
def test_parse_patch_operations(value, expected_issues):
    parsed, issues = operations.parse(value)

    assert issues.to_dict() == expected_issues
