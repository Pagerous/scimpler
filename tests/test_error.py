import pytest

from src.error import ValidationError, ValidationIssues, ValidationWarning


@pytest.fixture
def issues():
    issues = ValidationIssues()
    issues.add_error(issue=ValidationError.not_supported(), proceed=True)
    issues.add_error(issue=ValidationError.bad_value_content(), proceed=False, location=["a", "b"])
    issues.add_error(issue=ValidationError.bad_value_syntax(), proceed=False, location=["a", "b"])
    issues.add_error(
        issue=ValidationError.bad_value_content(), proceed=False, location=["a", "b", "c"]
    )
    issues.add_error(
        issue=ValidationError.bad_value_syntax(), proceed=False, location=["a", "b", "d"]
    )
    issues.add_warning(issue=ValidationWarning.missing(), location=["a", "e"])
    return issues


def test_issues_can_be_accessed_by_location():
    issues = ValidationIssues()
    issues.add_error(
        issue=ValidationError.bad_value_syntax(), proceed=False, location=["a", "b", "c"]
    )
    issues.add_error(issue=ValidationError.bad_value_content(), proceed=False, location=["a", "b"])
    issues.add_warning(issue=ValidationWarning.missing(), location=["a", "d", "e"])
    expected = {
        "_errors": [{"code": 4}],
        "c": {
            "_errors": [{"code": 1}],
        },
    }

    assert issues.get(location=["a", "b"]).to_dict() == expected


def test_issues_can_be_accessed_by_non_existing_location():
    issues = ValidationIssues()
    issues.add_error(issue=ValidationError.bad_value_content(), proceed=False, location=["a", "b"])

    assert issues.get(location=["a", "b", "c"]).to_dict() == {}


def test_issues_can_be_accessed_by_location_and_codes():
    issues = ValidationIssues()
    issues.add_error(issue=ValidationError.bad_value_content(), proceed=False, location=["a", "b"])
    issues.add_warning(issue=ValidationWarning.missing(), location=["a", "b"])

    assert issues.get(location=["a", "b"], error_codes=[4], warning_codes=[4]).to_dict() == {
        "_errors": [{"code": 4}],
        "_warnings": [{"code": 4}],
    }


def test_issues_can_be_accessed_by_location_and_non_existent_codes():
    issues = ValidationIssues()
    issues.add_error(issue=ValidationError.bad_value_content(), proceed=False, location=["a", "b"])
    issues.add_warning(issue=ValidationWarning.missing(), location=["a", "b"])

    assert issues.get(location=["a", "b"], error_codes=[1], warning_codes=[1]).to_dict() == {}


def test_errors_can_be_popped_by_location_and_codes():
    issues = ValidationIssues()
    issues.add_error(issue=ValidationError.bad_value_content(), proceed=False, location=["a", "b"])
    issues.add_error(issue=ValidationError.bad_value_syntax(), proceed=False, location=["a", "b"])
    issues.add_warning(issue=ValidationWarning.missing(), location=["a", "b"])

    assert issues.to_dict() == {
        "a": {"b": {"_errors": [{"code": 4}, {"code": 1}], "_warnings": [{"code": 4}]}}
    }
    assert not issues.can_proceed(["a", "b"])

    popped = issues.pop_errors(location=["a", "b"], codes=[1])

    assert popped.to_dict() == {"_errors": [{"code": 1}]}
    assert issues.to_dict() == {"a": {"b": {"_errors": [{"code": 4}], "_warnings": [{"code": 4}]}}}
    assert not issues.can_proceed(["a", "b"])

    issues.pop_errors(location=["a", "b"], codes=[4])
    assert issues.to_dict() == {"a": {"b": {"_warnings": [{"code": 4}]}}}
    assert issues.can_proceed(["a", "b"])


def test_issues_can_be_converted_to_dict(issues):
    expected = {
        "_errors": [{"code": 31, "error": "value or operation not supported", "context": {}}],
        "a": {
            "b": {
                "_errors": [
                    {"code": 4, "error": "bad value content", "context": {}},
                    {"code": 1, "error": "bad value syntax", "context": {}},
                ],
                "c": {
                    "_errors": [{"code": 4, "error": "bad value content", "context": {}}],
                },
                "d": {
                    "_errors": [{"code": 1, "error": "bad value syntax", "context": {}}],
                },
            },
            "e": {
                "_warnings": [{"code": 4, "error": "missing", "context": {}}],
            },
        },
    }

    actual = issues.to_dict(msg=True, ctx=True)

    assert actual == expected


def test_issues_can_be_converted_to_flat_dict(issues):
    expected = {
        "errors": {
            "": [{"code": 31, "error": "value or operation not supported", "context": {}}],
            "a.b": [
                {"code": 4, "error": "bad value content", "context": {}},
                {"code": 1, "error": "bad value syntax", "context": {}},
            ],
            "a.b.c": [{"code": 4, "error": "bad value content", "context": {}}],
            "a.b.d": [{"code": 1, "error": "bad value syntax", "context": {}}],
        },
        "warnings": {
            "a.e": [{"code": 4, "error": "missing", "context": {}}],
        },
    }

    actual = issues.flatten(msg=True, ctx=True)

    assert actual == expected
