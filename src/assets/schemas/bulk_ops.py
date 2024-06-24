import re
from copy import deepcopy
from typing import Any

from src.container import Missing, SCIMData
from src.data.attrs import Complex, ExternalReference, Integer, String, Unknown
from src.data.schemas import BaseSchema
from src.error import ValidationError, ValidationIssues

_RESOURCE_TYPE_REGEX = re.compile(r"/\w+")
_RESOURCE_OBJECT_REGEX = re.compile(r"/\w+/.*")


def _validate_operation_method_existence(method: Any) -> ValidationIssues:
    issues = ValidationIssues()
    if method in [None, Missing]:
        issues.add_error(
            issue=ValidationError.missing(),
            proceed=False,
        )
    return issues


def validate_request_operations(value: list[SCIMData]) -> ValidationIssues:
    issues = ValidationIssues()
    for i, item in enumerate(value):
        method = item.get("method")
        issues.merge(
            issues=_validate_operation_method_existence(method),
            location=(i, "method"),
        )
        bulk_id = item.get("bulkId")
        if method == "POST" and bulk_id in [None, Missing]:
            issues.add_error(
                issue=ValidationError.missing(),
                proceed=False,
                location=(i, "bulkId"),
            )
        path = item.get("path")
        if path in [None, Missing]:
            issues.add_error(
                issue=ValidationError.missing(),
                proceed=False,
                location=(i, "path"),
            )
        else:
            if method == "POST" and not _RESOURCE_TYPE_REGEX.fullmatch(path):
                issues.add_error(
                    issue=ValidationError.bad_value_syntax(),
                    proceed=False,
                    location=(i, "path"),
                )
            elif method in [
                "GET",
                "PATCH",
                "PUT",
                "DELETE",
            ] and not _RESOURCE_OBJECT_REGEX.fullmatch(path):
                issues.add_error(
                    issue=ValidationError.bad_value_syntax(),
                    proceed=False,
                    location=(i, "path"),
                )
        data = item.get("data")
        if method in ["POST", "PUT", "PATCH"] and data in [None, Missing]:
            issues.add_error(
                issue=ValidationError.missing(),
                proceed=False,
                location=(i, "data"),
            )
    return issues


def deserialize_request_operations(value: list[SCIMData]) -> list[SCIMData]:
    value = deepcopy(value)
    for i, item in enumerate(value):
        method = item.get("method")
        if method in ["GET", "DELETE"]:
            item.pop("data")
    return value


class BulkRequest(BaseSchema):
    def __init__(self):
        super().__init__(
            schema="urn:ietf:params:scim:api:messages:2.0:BulkRequest",
            attrs=[
                Integer("failOnErrors"),
                Complex(
                    name="Operations",
                    required=True,
                    multi_valued=True,
                    validators=[validate_request_operations],
                    deserializer=deserialize_request_operations,
                    sub_attributes=[
                        String(
                            name="method",
                            required=True,
                            canonical_values=["GET", "POST", "PATCH", "PUT", "DELETE"],
                            restrict_canonical_values=True,
                        ),
                        String("bulkId"),
                        String("version"),
                        String(
                            name="path",
                            required=True,
                        ),
                        Unknown("data"),
                    ],
                ),
            ],
        )


def validate_response_operations(value: list[SCIMData]) -> ValidationIssues:
    issues = ValidationIssues()
    for i, item in enumerate(value):
        method = item.get("method")
        issues.merge(
            issues=_validate_operation_method_existence(method),
            location=(i, "method"),
        )
        bulk_id = item.get("bulkId")
        if method == "POST" and bulk_id in [None, Missing]:
            issues.add_error(
                issue=ValidationError.missing(),
                proceed=False,
                location=(i, "bulkId"),
            )
        status = item.get("status")
        if method and status:
            location = item.get("location")
            if location in [None, Missing] and method and (method != "POST" or int(status) < 300):
                issues.add_error(
                    issue=ValidationError.missing(),
                    proceed=False,
                    location=(i, "location"),
                )
            response = item.get("response")
            if response in [None, Missing] and int(status) >= 300:
                issues.add_error(
                    issue=ValidationError.missing(),
                    proceed=False,
                    location=(i, "response"),
                )
        elif status in [None, Missing]:
            issues.add_error(
                issue=ValidationError.missing(),
                proceed=False,
                location=(i, "status"),
            )
    return issues


def _validate_status(value: Any) -> ValidationIssues:
    issues = ValidationIssues()
    try:
        int(value)
    except ValueError:
        issues.add_error(
            issue=ValidationError.bad_value_syntax(),
            proceed=False,
        )
    return issues


class BulkResponse(BaseSchema):
    def __init__(self):
        super().__init__(
            schema="urn:ietf:params:scim:api:messages:2.0:BulkResponse",
            attrs=[
                Complex(
                    sub_attributes=[
                        String(
                            name="method",
                            required=True,
                            canonical_values=["GET", "POST", "PATCH", "PUT", "DELETE"],
                            restrict_canonical_values=True,
                        ),
                        String("bulkId"),
                        String("version"),
                        ExternalReference("location"),
                        String(
                            name="status",
                            required=True,
                            validators=[_validate_status],
                        ),
                        Unknown("response"),
                    ],
                    name="Operations",
                    required=True,
                    multi_valued=True,
                    validators=[validate_response_operations],
                )
            ],
        )
