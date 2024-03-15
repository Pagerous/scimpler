import pytest

from src.assets.schemas.bulk_ops import request_operations, response_operations
from src.assets.schemas.patch_op import operations
from src.assets.schemas.schema import attributes
from src.data.container import SCIMDataContainer


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


def test_dumping_bulk_response_operation_fails_if_no_method():
    expected_issues = {"0": {"method": {"_errors": [{"code": 15}]}}}

    parsed, issues = response_operations.dump([SCIMDataContainer({"status": "200"})])

    assert issues.to_dict() == expected_issues


def test_dumping_bulk_response_operation_fails_if_unknown_method():
    expected_issues = {"0": {"method": {"_errors": [{"code": 14}]}}}

    parsed, issues = response_operations.dump(
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


def test_dumping_bulk_response_operation_fails_if_no_bulk_id_for_post():
    expected_issues = {"0": {"bulkId": {"_errors": [{"code": 15}]}}}

    parsed, issues = response_operations.dump(
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


def test_dumping_bulk_response_operation_fails_if_no_status():
    expected_issues = {"0": {"status": {"_errors": [{"code": 15}]}}}

    parsed, issues = response_operations.dump(
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


def test_dumping_bulk_response_operation_fails_if_no_location_for_normal_completion():
    expected_issues = {"0": {"location": {"_errors": [{"code": 15}]}}}

    parsed, issues = response_operations.dump(
        [SCIMDataContainer({"method": "POST", "bulkId": "qwerty", "status": "200"})]
    )

    assert issues.to_dict() == expected_issues


def test_dumping_bulk_response_operation_succeeds_if_no_location_for_post_failure():
    parsed, issues = response_operations.dump(
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


def test_dumping_bulk_response_operation_fails_if_no_response_for_failed_operation():
    expected_issues = {"0": {"response": {"_errors": [{"code": 15}]}}}

    parsed, issues = response_operations.dump(
        [SCIMDataContainer({"method": "POST", "bulkId": "qwerty", "status": "401"})]
    )

    assert issues.to_dict() == expected_issues


def test_dumping_bulk_response_operation_fails_if_bad_status_syntax():
    expected_issues = {"0": {"status": {"_errors": [{"code": 1}]}}}

    parsed, issues = response_operations.dump(
        [SCIMDataContainer({"method": "POST", "bulkId": "qwerty", "status": "abc"})]
    )

    assert issues.to_dict() == expected_issues


def test_dumping_attributes_field_fails_for_bad_sub_attributes():
    expected_issues = {
        "0": {
            "subAttributes": {
                "0": {"type": {"_errors": [{"code": 14}]}, "caseExact": {"_errors": [{"code": 2}]}}
            }
        }
    }

    parsed, issues = attributes.dump(
        value=[
            SCIMDataContainer(
                {
                    "name": "emails",
                    "type": "complex",
                    "multiValued": True,
                    "required": False,
                    "subAttributes": [
                        {
                            "name": "value",
                            "type": "unknown",
                            "multiValued": False,
                            "required": False,
                            "caseExact": 123,
                            "mutability": "readWrite",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                        {
                            "name": "display",
                            "type": "string",
                            "multiValued": False,
                            "required": False,
                            "caseExact": False,
                            "mutability": "readWrite",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                        {
                            "name": "type",
                            "type": "string",
                            "multiValued": False,
                            "required": False,
                            "caseExact": False,
                            "canonicalValues": ["work", "home", "other"],
                            "mutability": "readWrite",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                        {
                            "name": "primary",
                            "type": "boolean",
                            "multiValued": False,
                            "required": False,
                            "mutability": "readWrite",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                    ],
                }
            )
        ]
    )

    assert issues.to_dict() == expected_issues


def test_case_exact_is_removed_from_non_string_attrs_while_dumping_attributes():
    parsed, issues = attributes.dump(
        value=[
            SCIMDataContainer(
                {
                    "name": "value",
                    "type": "integer",
                    "multiValued": True,
                    "caseExact": True,
                    "required": False,
                }
            )
        ]
    )

    assert issues.to_dict(msg=True) == {}
    assert "caseExact" not in parsed[0].to_dict()


def test_sub_attributes_are_removed_from_non_complex_attrs_while_dumping_attributes():
    parsed, issues = attributes.dump(
        value=[
            SCIMDataContainer(
                {
                    "name": "value",
                    "type": "integer",
                    "multiValued": True,
                    "subAttributes": [],
                    "required": False,
                }
            )
        ]
    )

    assert issues.to_dict(msg=True) == {}
    assert "subAttributes" not in parsed[0].to_dict()
