import pytest

from src.assets.schemas import Error
from src.data.attr_presence import AttrPresenceConfig


@pytest.mark.parametrize(
    ("value", "expected_issues"),
    (
        ("abc", {"_errors": [{"code": 1}]}),
        ("399", {"_errors": [{"code": 18}]}),
        ("600", {"_errors": [{"code": 18}]}),
        ("400", {}),
    ),
)
def test_error_status_is_validated(value, expected_issues):
    issues = Error.validate({"status": value}, AttrPresenceConfig("RESPONSE"))

    assert issues.get(location=["status"]).to_dict() == expected_issues
