import pytest

from src.assets.schemas.bulk_ops import request_operations, response_operations
from src.data.container import SCIMDataContainer


def test_validation_bulk_request_operation_fails_if_no_method():
    expected_issues = {"0": {"method": {"_errors": [{"code": 15}]}}}

    issues = request_operations.validate([SCIMDataContainer({"path": "/Users"})])

    assert issues.to_dict() == expected_issues


def test_validation_bulk_request_operation_fails_if_unknown_method():
    expected_issues = {"0": {"method": {"_errors": [{"code": 14}]}}}

    issues = request_operations.validate(
        [SCIMDataContainer({"method": "TERMINATE", "path": "/Users"})]
    )

    assert issues.to_dict() == expected_issues


def test_validation_bulk_request_operation_fails_if_no_bulk_id_for_post():
    expected_issues = {"0": {"bulkId": {"_errors": [{"code": 15}]}}}

    issues = request_operations.validate(
        [SCIMDataContainer({"method": "POST", "data": {"a": 1, "b": 2}, "path": "/NiceResource"})]
    )

    assert issues.to_dict() == expected_issues


def test_validation_bulk_request_operation_fails_if_no_data_for_post():
    expected_issues = {"0": {"data": {"_errors": [{"code": 15}]}}}

    issues = request_operations.validate(
        [SCIMDataContainer({"method": "POST", "bulkId": "abc", "path": "/NiceResource"})]
    )

    assert issues.to_dict() == expected_issues


def test_validation_bulk_request_operation_fails_if_no_data_for_patch():
    expected_issues = {"0": {"data": {"_errors": [{"code": 15}]}}}

    issues = request_operations.validate(
        [SCIMDataContainer({"method": "PATCH", "path": "/NiceResource/123"})]
    )

    assert issues.to_dict() == expected_issues


def test_validation_bulk_request_operation_fails_if_no_data_for_put():
    expected_issues = {"0": {"data": {"_errors": [{"code": 15}]}}}

    issues = request_operations.validate(
        [SCIMDataContainer({"method": "PUT", "path": "/NiceResource/123"})]
    )

    assert issues.to_dict() == expected_issues


def test_validation_bulk_request_operation_fails_if_path_missing():
    expected_issues = {"0": {"path": {"_errors": [{"code": 15}]}}}

    issues = request_operations.validate([SCIMDataContainer({"method": "PUT", "data": {"a": 1}})])

    assert issues.to_dict() == expected_issues


def test_validation_bulk_request_operation_fails_if_bad_path_for_post():
    expected_issues = {"0": {"path": {"_errors": [{"code": 34}]}}}

    issues = request_operations.validate(
        [
            SCIMDataContainer(
                {"method": "POST", "bulkId": "abc", "data": {"a": 1}, "path": "/NiceResource/123"}
            )
        ]
    )

    assert issues.to_dict() == expected_issues


@pytest.mark.parametrize("method", ["GET", "PATCH", "PUT", "DELETE"])
def test_validation_bulk_request_operation_fails_if_bad_path(method):
    expected_issues = {"0": {"path": {"_errors": [{"code": 35}]}}}

    issues = request_operations.validate(
        [
            SCIMDataContainer(
                {"method": method, "bulkId": "abc", "data": {"a": 1}, "path": "/NiceResource"}
            )
        ]
    )

    assert issues.to_dict() == expected_issues


@pytest.mark.parametrize("method", ["GET", "DELETE"])
def test_data_is_removed_when_parsing_bulk_request_get_or_delete_operation(method):
    parsed = request_operations.parse(
        [SCIMDataContainer({"method": method, "data": {"a": 1}, "path": "/NiceResource/123"})]
    )

    assert "data" not in parsed[0].to_dict()


def test_validation_bulk_request_post_operation_succeeds():
    issues = request_operations.validate(
        [
            SCIMDataContainer(
                {"method": "POST", "bulkId": "abc", "data": {"a": 1}, "path": "/NiceResource"}
            )
        ]
    )

    assert issues.to_dict(msg=True) == {}


def test_validation_bulk_request_get_operation_succeeds():
    issues = request_operations.validate(
        [SCIMDataContainer({"method": "GET", "path": "/NiceResource/123"})]
    )

    assert issues.to_dict(msg=True) == {}


def test_validation_bulk_request_put_operation_succeeds():
    issues = request_operations.validate(
        [
            SCIMDataContainer(
                {
                    "method": "PUT",
                    "data": {"a": 1},
                    "version": 'W/"4weymrEsh5O6cAEK"',
                    "path": "/NiceResource/123",
                }
            )
        ]
    )

    assert issues.to_dict(msg=True) == {}


def test_validation_bulk_request_patch_operation_succeeds():
    issues = request_operations.validate(
        [
            SCIMDataContainer(
                {
                    "method": "PATCH",
                    "data": {"a": 1},
                    "version": 'W/"4weymrEsh5O6cAEK"',
                    "path": "/NiceResource/123",
                }
            )
        ]
    )

    assert issues.to_dict(msg=True) == {}


def test_validation_bulk_request_delete_operation_succeeds():
    issues = request_operations.validate(
        [
            SCIMDataContainer(
                {
                    "method": "DELETE",
                    "version": 'W/"4weymrEsh5O6cAEK"',
                    "path": "/NiceResource/123",
                }
            )
        ]
    )

    assert issues.to_dict(msg=True) == {}


def test_validation_bulk_response_operation_fails_if_no_method():
    expected_issues = {"0": {"method": {"_errors": [{"code": 15}]}}}

    issues = response_operations.validate([SCIMDataContainer({"status": "200"})])

    assert issues.to_dict() == expected_issues


def test_validation_bulk_response_operation_fails_if_unknown_method():
    expected_issues = {"0": {"method": {"_errors": [{"code": 14}]}}}

    issues = response_operations.validate(
        [
            SCIMDataContainer(
                {
                    "method": "TERMINATE",
                    "status": "200",
                    "location": "https://example.com/v2/Users/b7c14771-226c-4d05-8860-134711653041",
                }
            )
        ]
    )

    assert issues.to_dict() == expected_issues


def test_validation_bulk_response_operation_fails_if_no_bulk_id_for_post():
    expected_issues = {"0": {"bulkId": {"_errors": [{"code": 15}]}}}

    issues = response_operations.validate(
        [
            SCIMDataContainer(
                {
                    "method": "POST",
                    "status": "200",
                    "location": "https://example.com/v2/Users/b7c14771-226c-4d05-8860-134711653041",
                }
            )
        ]
    )

    assert issues.to_dict() == expected_issues


def test_validation_bulk_response_operation_fails_if_no_status():
    expected_issues = {"0": {"status": {"_errors": [{"code": 15}]}}}

    issues = response_operations.validate(
        [
            SCIMDataContainer(
                {
                    "method": "POST",
                    "bulkId": "qwerty",
                    "location": "https://example.com/v2/Users/b7c14771-226c-4d05-8860-134711653041",
                }
            )
        ]
    )

    assert issues.to_dict() == expected_issues


def test_validation_bulk_response_operation_fails_if_no_location_for_normal_completion():
    expected_issues = {"0": {"location": {"_errors": [{"code": 15}]}}}

    issues = response_operations.validate(
        [SCIMDataContainer({"method": "POST", "bulkId": "qwerty", "status": "200"})]
    )

    assert issues.to_dict() == expected_issues


def test_validation_bulk_response_operation_succeeds_if_no_location_for_post_failure():
    issues = response_operations.validate(
        [
            SCIMDataContainer(
                {
                    "method": "POST",
                    "bulkId": "qwerty",
                    "status": "400",
                    "response": {
                        "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
                        "scimType": "invalidSyntax",
                        "detail": (
                            "Request is unparsable, syntactically incorrect, or violates schema."
                        ),
                        "status": "401",
                    },
                }
            )
        ]
    )

    assert issues.to_dict(msg=True) == {}


def test_validation_bulk_response_operation_fails_if_no_response_for_failed_operation():
    expected_issues = {"0": {"response": {"_errors": [{"code": 15}]}}}

    issues = response_operations.validate(
        [SCIMDataContainer({"method": "POST", "bulkId": "qwerty", "status": "401"})]
    )

    assert issues.to_dict() == expected_issues


def test_validation_bulk_response_operation_fails_if_bad_status_syntax():
    expected_issues = {"0": {"status": {"_errors": [{"code": 1}]}}}

    issues = response_operations.validate(
        [SCIMDataContainer({"method": "POST", "bulkId": "qwerty", "status": "abc"})]
    )

    assert issues.to_dict() == expected_issues
