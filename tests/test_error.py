import pytest

from scimpler.error import ValidationError, ValidationIssues, ValidationWarning


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
    issues.add_warning(issue=ValidationWarning.missing(), location=["c", "d"])
    issues.add_warning(issue=ValidationWarning.multiple_type_value_pairs(), location=["c", "d"])

    assert issues.to_dict() == {
        "a": {"b": {"_errors": [{"code": 4}, {"code": 1}], "_warnings": [{"code": 4}]}},
        "c": {"d": {"_warnings": [{"code": 4}, {"code": 2}]}},
    }
    assert not issues.can_proceed(["a", "b"])

    popped = issues.pop(location=["a", "b"], error_codes=[1])

    assert popped.to_dict() == {"_errors": [{"code": 1}]}
    assert issues.to_dict() == {
        "a": {"b": {"_errors": [{"code": 4}], "_warnings": [{"code": 4}]}},
        "c": {"d": {"_warnings": [{"code": 4}, {"code": 2}]}},
    }
    assert not issues.can_proceed(["a", "b"])

    issues.pop(location=["a", "b"], error_codes=[4])
    assert issues.to_dict() == {
        "a": {"b": {"_warnings": [{"code": 4}]}},
        "c": {"d": {"_warnings": [{"code": 4}, {"code": 2}]}},
    }
    assert issues.can_proceed(["a", "b"])

    issues.pop(warning_codes=[4])
    assert issues.to_dict() == {"c": {"d": {"_warnings": [{"code": 2}]}}}


def test_issues_can_be_converted_to_dict(issues):
    expected = {
        "_errors": [{"code": 31, "message": "value or operation not supported", "context": {}}],
        "a": {
            "b": {
                "_errors": [
                    {"code": 4, "message": "bad value content", "context": {}},
                    {"code": 1, "message": "bad value syntax", "context": {}},
                ],
                "c": {
                    "_errors": [{"code": 4, "message": "bad value content", "context": {}}],
                },
                "d": {
                    "_errors": [{"code": 1, "message": "bad value syntax", "context": {}}],
                },
            },
            "e": {
                "_warnings": [{"code": 4, "message": "missing", "context": {}}],
            },
        },
    }

    actual = issues.to_dict(message=True, context=True)

    assert actual == expected


def test_custom_validation_error_can_be_created():
    error = ValidationError(code=1001, scim_error="invalidValue", message="You did something wrong")

    assert error.code == 1001
    assert error.scim_error == "invalidValue"
    assert error.message == "You did something wrong"


def test_custom_validation_error_message_can_be_specified_for_built_in_code():
    error = ValidationError(code=1, scim_error="invalidValue", message="really bad value")

    assert error.code == 1
    assert error.scim_error == "invalidValue"
    assert error.message == "really bad value"


def test_creating_custom_validation_error_with_code_below_1000_fails():
    with pytest.raises(
        ValueError,
        match="error code for custom validation error must be greater than 1000",
    ):
        ValidationError(code=999, scim_error="invalidValue", message="really bad value")


def test_validation_errors_are_identified_by_code():
    error_1 = ValidationError(code=1, scim_error="invalidValue", message="really bad value")
    error_2 = ValidationError(code=1, scim_error="invalidFilter", message="even worse value")
    error_3 = ValidationError(code=1001, scim_error="invalidValue", message="really bad value")

    assert error_1 == error_2
    assert error_1 != error_3
    assert error_1 != 1


def test_custom_validation_warning_can_be_created():
    error = ValidationWarning(code=1001, message="You probably did something wrong")

    assert error.code == 1001
    assert error.message == "You probably did something wrong"


def test_custom_validation_warning_message_can_be_specified_for_built_in_code():
    error = ValidationWarning(code=1, message="You probably did something wrong")

    assert error.code == 1
    assert error.message == "You probably did something wrong"


def test_creating_custom_validation_warning_with_code_below_1000_fails():
    with pytest.raises(
        ValueError,
        match="error code for custom validation warning must be greater than 1000",
    ):
        ValidationWarning(code=999, message="You probably did something wrong")


def test_validation_warnings_are_identified_by_code():
    warning_1 = ValidationWarning(code=1, message="You probably did something wrong")
    warning_2 = ValidationWarning(code=1, message="You did something weird")
    warning_3 = ValidationWarning(code=1001, message="You probably did something wrong")

    assert warning_1 == warning_2
    assert warning_1 != warning_3
    assert warning_1 != 1
