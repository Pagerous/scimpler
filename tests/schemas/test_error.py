import pytest

from scimpler.data.attr_presence import AttrPresenceConfig
from scimpler.schemas import ErrorSchema


@pytest.mark.parametrize(
    ("value", "expected_issues"),
    (
        ("abc", {"_errors": [{"code": 1}]}),
        ("299", {"_errors": [{"code": 4}]}),
        ("600", {"_errors": [{"code": 4}]}),
        ("400", {}),
    ),
)
def test_error_status_is_validated(value, expected_issues):
    issues = ErrorSchema().validate({"status": value}, AttrPresenceConfig("RESPONSE"))

    assert issues.get(location=["status"]).to_dict() == expected_issues
