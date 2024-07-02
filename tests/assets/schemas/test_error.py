import pytest

from src.assets.schemas import ErrorSchema
from src.data.attr_presence import AttrPresenceConfig


@pytest.mark.parametrize(
    ("value", "expected_issues"),
    (
        ("abc", {"_errors": [{"code": 1}]}),
        ("399", {"_errors": [{"code": 4}]}),
        ("600", {"_errors": [{"code": 4}]}),
        ("400", {}),
    ),
)
def test_error_status_is_validated(value, expected_issues):
    issues = ErrorSchema().validate({"status": value}, AttrPresenceConfig("RESPONSE"))

    assert issues.get(location=["status"]).to_dict() == expected_issues
