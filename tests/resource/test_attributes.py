import pytest

from src.data.container import SCIMDataContainer
from src.resource.schemas.bulk_ops import request_operations
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


def test_parsing_bulk_request_operation_fails_if_no_method():
    expected_issues = {"0": {"method": {"_errors": [{"code": 15}]}}}

    parsed, issues = request_operations.parse([SCIMDataContainer({"path": "/Users"})])

    assert issues.to_dict() == expected_issues


def test_parsing_bulk_request_operation_fails_if_unknown_method():
    expected_issues = {"0": {"method": {"_errors": [{"code": 14}]}}}

    parsed, issues = request_operations.parse(
        [SCIMDataContainer({"method": "TERMINATE", "path": "/Users"})]
    )

    assert issues.to_dict() == expected_issues


def test_parsing_bulk_request_operation_fails_if_no_bulk_id_for_post():
    expected_issues = {"0": {"bulkId": {"_errors": [{"code": 15}]}}}

    parsed, issues = request_operations.parse(
        [SCIMDataContainer({"method": "POST", "data": {"a": 1, "b": 2}, "path": "/NiceResource"})]
    )

    assert issues.to_dict() == expected_issues


def test_parsing_bulk_request_operation_fails_if_no_data_for_post():
    expected_issues = {"0": {"data": {"_errors": [{"code": 15}]}}}

    parsed, issues = request_operations.parse(
        [SCIMDataContainer({"method": "POST", "bulkId": "abc", "path": "/NiceResource"})]
    )

    assert issues.to_dict() == expected_issues


def test_parsing_bulk_request_operation_fails_if_no_data_for_patch():
    expected_issues = {"0": {"data": {"_errors": [{"code": 15}]}}}

    parsed, issues = request_operations.parse(
        [SCIMDataContainer({"method": "PATCH", "path": "/NiceResource/123"})]
    )

    assert issues.to_dict() == expected_issues


def test_parsing_bulk_request_operation_fails_if_no_data_for_put():
    expected_issues = {"0": {"data": {"_errors": [{"code": 15}]}}}

    parsed, issues = request_operations.parse(
        [SCIMDataContainer({"method": "PUT", "path": "/NiceResource/123"})]
    )

    assert issues.to_dict() == expected_issues


def test_parsing_bulk_request_operation_fails_if_path_missing():
    expected_issues = {"0": {"path": {"_errors": [{"code": 15}]}}}

    parsed, issues = request_operations.parse(
        [SCIMDataContainer({"method": "PUT", "data": {"a": 1}})]
    )

    assert issues.to_dict() == expected_issues


def test_parsing_bulk_request_operation_fails_if_bad_path_for_post():
    expected_issues = {"0": {"path": {"_errors": [{"code": 34}]}}}

    parsed, issues = request_operations.parse(
        [
            SCIMDataContainer(
                {"method": "POST", "bulkId": "abc", "data": {"a": 1}, "path": "/NiceResource/123"}
            )
        ]
    )

    assert issues.to_dict() == expected_issues


@pytest.mark.parametrize("method", ["GET", "PATCH", "PUT", "DELETE"])
def test_parsing_bulk_request_operation_fails_if_bad_path(method):
    expected_issues = {"0": {"path": {"_errors": [{"code": 35}]}}}

    parsed, issues = request_operations.parse(
        [
            SCIMDataContainer(
                {"method": method, "bulkId": "abc", "data": {"a": 1}, "path": "/NiceResource"}
            )
        ]
    )

    assert issues.to_dict() == expected_issues


@pytest.mark.parametrize("method", ["GET", "DELETE"])
def test_data_is_removed_when_parsing_bulk_request_get_or_delete_operation(method):
    parsed, issues = request_operations.parse(
        [SCIMDataContainer({"method": method, "data": {"a": 1}, "path": "/NiceResource/123"})]
    )

    assert issues.to_dict(msg=True) == {}
    assert "data" not in parsed[0].to_dict()


def test_parsing_bulk_request_post_operation_succeeds():
    parsed, issues = request_operations.parse(
        [
            SCIMDataContainer(
                {"method": "POST", "bulkId": "abc", "data": {"a": 1}, "path": "/NiceResource"}
            )
        ]
    )

    assert issues.to_dict(msg=True) == {}


def test_parsing_bulk_request_get_operation_succeeds():
    parsed, issues = request_operations.parse(
        [SCIMDataContainer({"method": "GET", "path": "/NiceResource/123"})]
    )

    assert issues.to_dict(msg=True) == {}


def test_parsing_bulk_request_put_operation_succeeds():
    parsed, issues = request_operations.parse(
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


def test_parsing_bulk_request_patch_operation_succeeds():
    parsed, issues = request_operations.parse(
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


def test_parsing_bulk_request_delete_operation_succeeds():
    parsed, issues = request_operations.parse(
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
