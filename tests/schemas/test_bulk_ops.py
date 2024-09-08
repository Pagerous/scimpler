import pytest

from scimpler.data import PatchPath
from scimpler.data.scim_data import ScimData
from scimpler.schemas import ErrorSchema, PatchOpSchema
from scimpler.schemas.bulk_ops import BulkRequestSchema, BulkResponseSchema


def test_validation_bulk_request_operation_fails_if_no_method():
    expected_issues = {"0": {"method": {"_errors": [{"code": 5}]}}}

    issues = (
        BulkRequestSchema(sub_schemas={})
        .attrs.get("operations")
        .validate([ScimData({"path": "/Users"})])
    )

    assert issues.to_dict() == expected_issues


def test_validation_bulk_request_operation_fails_if_unknown_method():
    expected_issues = {"0": {"method": {"_errors": [{"code": 9}]}}}

    issues = (
        BulkRequestSchema(sub_schemas={})
        .attrs.get("operations")
        .validate([ScimData({"method": "TERMINATE", "path": "/Users"})])
    )

    assert issues.to_dict() == expected_issues


def test_validation_bulk_request_operation_fails_if_no_bulk_id_for_post():
    expected_issues = {"0": {"bulkId": {"_errors": [{"code": 5}]}}}

    issues = (
        BulkRequestSchema(sub_schemas={})
        .attrs.get("operations")
        .validate([ScimData({"method": "POST", "data": {"a": 1, "b": 2}, "path": "/NiceResource"})])
    )

    assert issues.to_dict() == expected_issues


def test_validation_bulk_request_operation_fails_if_no_data_for_post():
    expected_issues = {"0": {"data": {"_errors": [{"code": 5}]}}}

    issues = (
        BulkRequestSchema(sub_schemas={})
        .attrs.get("operations")
        .validate([ScimData({"method": "POST", "bulkId": "abc", "path": "/NiceResource"})])
    )

    assert issues.to_dict() == expected_issues


def test_validation_bulk_request_operation_fails_if_no_data_for_patch():
    expected_issues = {"0": {"data": {"_errors": [{"code": 5}]}}}

    issues = (
        BulkRequestSchema(sub_schemas={})
        .attrs.get("operations")
        .validate([ScimData({"method": "PATCH", "path": "/NiceResource/123"})])
    )

    assert issues.to_dict() == expected_issues


def test_validation_bulk_request_operation_fails_if_no_data_for_put():
    expected_issues = {"0": {"data": {"_errors": [{"code": 5}]}}}

    issues = (
        BulkRequestSchema(sub_schemas={})
        .attrs.get("operations")
        .validate([ScimData({"method": "PUT", "path": "/NiceResource/123"})])
    )

    assert issues.to_dict() == expected_issues


def test_validation_bulk_request_operation_fails_if_path_missing():
    expected_issues = {"0": {"path": {"_errors": [{"code": 5}]}}}

    issues = (
        BulkRequestSchema(sub_schemas={})
        .attrs.get("operations")
        .validate([ScimData({"method": "PUT", "data": {"a": 1}})])
    )

    assert issues.to_dict() == expected_issues


def test_validation_bulk_request_operation_fails_if_bad_path_for_post():
    expected_issues = {"0": {"path": {"_errors": [{"code": 1}]}}}

    issues = (
        BulkRequestSchema(sub_schemas={})
        .attrs.get("operations")
        .validate(
            [
                ScimData(
                    {
                        "method": "POST",
                        "bulkId": "abc",
                        "data": {"a": 1},
                        "path": "/NiceResource/123",
                    }
                )
            ]
        )
    )

    assert issues.to_dict() == expected_issues


@pytest.mark.parametrize("method", ["GET", "PATCH", "PUT", "DELETE"])
def test_validation_bulk_request_operation_fails_if_bad_path(method):
    expected_issues = {"0": {"path": {"_errors": [{"code": 1}]}}}

    issues = (
        BulkRequestSchema(sub_schemas={})
        .attrs.get("operations")
        .validate(
            [
                ScimData(
                    {"method": method, "bulkId": "abc", "data": {"a": 1}, "path": "/NiceResource"}
                )
            ]
        )
    )

    assert issues.to_dict() == expected_issues


@pytest.mark.parametrize("method", ["GET", "DELETE"])
def test_data_is_removed_when_parsing_bulk_request_get_or_delete_operation(method):
    deserialized = (
        BulkRequestSchema(sub_schemas={})
        .attrs.get("operations")
        .deserialize(
            [
                ScimData({"method": method, "data": {"a": 1}, "path": "/NiceResource/123"}),
                ScimData({"method": "PUT", "data": {"a": 1}, "path": "/NiceResource/123"}),
            ]
        )
    )

    assert "data" not in deserialized[0].to_dict()
    assert "data" in deserialized[1].to_dict()


def test_validation_bulk_request_post_operation_succeeds():
    issues = (
        BulkRequestSchema(sub_schemas={})
        .attrs.get("operations")
        .validate(
            [
                ScimData(
                    {"method": "POST", "bulkId": "abc", "data": {"a": 1}, "path": "/NiceResource"}
                )
            ]
        )
    )

    assert issues.to_dict(msg=True) == {}


def test_validation_bulk_request_get_operation_succeeds():
    issues = (
        BulkRequestSchema(sub_schemas={})
        .attrs.get("operations")
        .validate([ScimData({"method": "GET", "path": "/NiceResource/123"})])
    )

    assert issues.to_dict(msg=True) == {}


def test_validation_bulk_request_put_operation_succeeds():
    issues = (
        BulkRequestSchema(sub_schemas={})
        .attrs.get("operations")
        .validate(
            [
                ScimData(
                    {
                        "method": "PUT",
                        "data": {"a": 1},
                        "version": 'W/"4weymrEsh5O6cAEK"',
                        "path": "/NiceResource/123",
                    }
                )
            ]
        )
    )

    assert issues.to_dict(msg=True) == {}


def test_validation_bulk_request_patch_operation_succeeds():
    issues = (
        BulkRequestSchema(sub_schemas={})
        .attrs.get("operations")
        .validate(
            [
                ScimData(
                    {
                        "method": "PATCH",
                        "data": {"a": 1},
                        "version": 'W/"4weymrEsh5O6cAEK"',
                        "path": "/NiceResource/123",
                    }
                )
            ]
        )
    )

    assert issues.to_dict(msg=True) == {}


def test_validation_bulk_request_delete_operation_succeeds():
    issues = (
        BulkRequestSchema(sub_schemas={})
        .attrs.get("operations")
        .validate(
            [
                ScimData(
                    {
                        "method": "DELETE",
                        "version": 'W/"4weymrEsh5O6cAEK"',
                        "path": "/NiceResource/123",
                    }
                )
            ]
        )
    )

    assert issues.to_dict(msg=True) == {}


def test_validation_bulk_response_operation_fails_if_no_method():
    expected_issues = {"0": {"method": {"_errors": [{"code": 5}]}}}

    issues = (
        BulkResponseSchema(sub_schemas={}, error_schema=ErrorSchema())
        .attrs.get("operations")
        .validate([ScimData({"status": "200"})])
    )

    assert issues.to_dict() == expected_issues


def test_validation_bulk_response_operation_fails_if_unknown_method():
    expected_issues = {"0": {"method": {"_errors": [{"code": 9}]}}}

    issues = (
        BulkResponseSchema(sub_schemas={}, error_schema=ErrorSchema())
        .attrs.get("operations")
        .validate(
            [
                ScimData(
                    {
                        "method": "TERMINATE",
                        "status": "200",
                        "location": (
                            "https://example.com/v2/Users/b7c14771-226c-4d05-8860-134711653041"
                        ),
                    }
                )
            ]
        )
    )

    assert issues.to_dict() == expected_issues


def test_validation_bulk_response_operation_fails_if_no_bulk_id_for_post():
    expected_issues = {"0": {"bulkId": {"_errors": [{"code": 5}]}}}

    issues = (
        BulkResponseSchema(sub_schemas={}, error_schema=ErrorSchema())
        .attrs.get("operations")
        .validate(
            [
                ScimData(
                    {
                        "method": "POST",
                        "status": "200",
                        "location": (
                            "https://example.com/v2/Users/b7c14771-226c-4d05-8860-134711653041"
                        ),
                    }
                )
            ]
        )
    )

    assert issues.to_dict() == expected_issues


def test_validation_bulk_response_operation_fails_if_no_status():
    expected_issues = {"0": {"status": {"_errors": [{"code": 5}]}}}

    issues = (
        BulkResponseSchema(sub_schemas={}, error_schema=ErrorSchema())
        .attrs.get("operations")
        .validate(
            [
                ScimData(
                    {
                        "method": "POST",
                        "bulkId": "qwerty",
                        "location": (
                            "https://example.com/v2/Users/b7c14771-226c-4d05-8860-134711653041"
                        ),
                    }
                )
            ]
        )
    )

    assert issues.to_dict() == expected_issues


def test_validation_bulk_response_operation_fails_if_no_location_for_normal_completion():
    expected_issues = {"0": {"location": {"_errors": [{"code": 5}]}}}

    issues = (
        BulkResponseSchema(sub_schemas={}, error_schema=ErrorSchema())
        .attrs.get("operations")
        .validate([ScimData({"method": "POST", "bulkId": "qwerty", "status": "200"})])
    )

    assert issues.to_dict() == expected_issues


def test_validation_bulk_response_operation_succeeds_if_no_location_for_post_failure():
    issues = (
        BulkResponseSchema(sub_schemas={}, error_schema=ErrorSchema())
        .attrs.get("operations")
        .validate(
            [
                ScimData(
                    {
                        "method": "POST",
                        "bulkId": "qwerty",
                        "status": "400",
                        "response": {
                            "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
                            "scimType": "invalidSyntax",
                            "detail": (
                                "Request is unparsable, syntactically incorrect, "
                                "or violates schema."
                            ),
                            "status": "401",
                        },
                    }
                )
            ]
        )
    )

    assert issues.to_dict(msg=True) == {}


def test_validation_bulk_response_operation_fails_if_no_response_for_failed_operation():
    expected_issues = {"0": {"response": {"_errors": [{"code": 5}]}}}

    issues = (
        BulkResponseSchema(sub_schemas={}, error_schema=ErrorSchema())
        .attrs.get("operations")
        .validate([ScimData({"method": "POST", "bulkId": "qwerty", "status": "401"})])
    )

    assert issues.to_dict() == expected_issues


def test_validation_bulk_response_operation_fails_if_bad_status_syntax():
    expected_issues = {"0": {"status": {"_errors": [{"code": 1}]}}}

    issues = (
        BulkResponseSchema(sub_schemas={}, error_schema=ErrorSchema())
        .attrs.get("operations")
        .validate([ScimData({"method": "POST", "bulkId": "qwerty", "status": "abc"})])
    )

    assert issues.to_dict() == expected_issues


def test_bulk_request_can_be_deserialized(user_schema):
    schema = BulkRequestSchema(
        sub_schemas={"PATCH": {user_schema.endpoint: PatchOpSchema(user_schema)}}
    )
    data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:BulkRequest"],
        "Operations": [
            {
                "method": "PATCH",
                "path": "/Users/123",
                "data": {
                    "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
                    "Operations": [
                        {
                            "op": "add",
                            "path": "emails",
                            "value": {"type": "work", "value": "work@example.com"},
                        }
                    ],
                },
            }
        ],
    }

    deserialized = schema.deserialize(data)

    assert isinstance(deserialized["Operations"][0]["data"]["Operations"][0]["path"], PatchPath)


def test_get_schema_for_bulk_request_returns_none_for_operation_with_unsupported_method(
    user_schema,
):
    schema = BulkRequestSchema(
        sub_schemas={"PATCH": {user_schema.endpoint: PatchOpSchema(user_schema)}}
    )
    operation = {
        "method": "GET",
        "path": "/Users/123",
    }

    assert schema.get_schema(operation) is None


def test_get_schema_for_bulk_request_returns_none_for_operation_if_no_slash_in_path(user_schema):
    schema = BulkRequestSchema(
        sub_schemas={"PATCH": {user_schema.endpoint: PatchOpSchema(user_schema)}}
    )
    operation = {
        "method": "PATCH",
        "path": "Users",
    }

    assert schema.get_schema(operation) is None


def test_get_schema_for_bulk_returns_returns_none_for_operation_with_no_status(user_schema):
    schema = BulkResponseSchema(
        sub_schemas={"PATCH": {user_schema.endpoint: user_schema}}, error_schema=ErrorSchema()
    )
    operation = {
        "method": "PATCH",
        "location": "/Users/123",
    }

    assert schema.get_schema(operation) is None
