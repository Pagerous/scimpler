import re
from typing import Any, List, Tuple, Union

from src.data import type as type_
from src.data.attributes import Attribute, ComplexAttribute
from src.data.container import Invalid, Missing, SCIMDataContainer
from src.data.schemas import BaseSchema
from src.error import ValidationError, ValidationIssues

_RESOURCE_TYPE_REGEX = re.compile(r"/\w+")
_RESOURCE_OBJECT_REGEX = re.compile(r"/\w+/.*")


def _validate_operation_method_existence(method: Any) -> ValidationIssues:
    issues = ValidationIssues()
    if method in [None, Missing]:
        issues.add(
            issue=ValidationError.missing(),
            proceed=False,
        )

    return issues


def _validate_operation_method_value(method: Any) -> Tuple[Union[Invalid, str], ValidationIssues]:
    issues = ValidationIssues()
    allowed = ["GET", "POST", "PATCH", "PUT", "DELETE"]
    if method not in allowed:
        issues.add(
            issue=ValidationError.must_be_one_of(allowed, method),
            proceed=False,
        )
        method = Invalid
    return method, issues


def validate_request_operations(
    operations_data: List[SCIMDataContainer],
) -> Tuple[List[SCIMDataContainer], ValidationIssues]:
    issues = ValidationIssues()
    for i, operation_data in enumerate(operations_data):
        method = operation_data[_operation__method.rep]
        issues.merge(
            issues=_validate_operation_method_existence(method),
            location=(i, _operation__method.rep.attr),
        )
        bulk_id = operation_data[_operation__bulk_id.rep]
        if method == "POST" and bulk_id in [None, Missing]:
            issues.add(
                issue=ValidationError.missing(),
                proceed=False,
                location=(i, _operation__bulk_id.rep.attr),
            )
        if method in ["GET", "DELETE"]:
            del operation_data[_operation__data.rep]
        path = operation_data[_operation__path.rep]
        if path in [None, Missing]:
            issues.add(
                issue=ValidationError.missing(),
                proceed=False,
                location=(i, _operation__path.rep.attr),
            )
        else:
            if method == "POST" and not _RESOURCE_TYPE_REGEX.fullmatch(path):
                issues.add(
                    issue=ValidationError.resource_type_endpoint_required(),
                    proceed=False,
                    location=(i, _operation__path.rep.attr),
                )
            elif method in [
                "GET",
                "PATCH",
                "PUT",
                "DELETE",
            ] and not _RESOURCE_OBJECT_REGEX.fullmatch(path):
                issues.add(
                    issue=ValidationError.resource_object_endpoint_required(),
                    proceed=False,
                    location=(i, _operation__path.rep.attr),
                )
        data = operation_data[_operation__data.rep]
        if method in ["POST", "PUT", "PATCH"] and data in [None, Missing]:
            issues.add(
                issue=ValidationError.missing(),
                proceed=False,
                location=(i, _operation__data.rep.attr),
            )
    return operations_data, issues


_operation__method = Attribute(
    name="method",
    type_=type_.String,
    required=True,
    canonical_values=["GET", "POST", "PATCH", "PUT", "DELETE"],
    parsers=[_validate_operation_method_value],
    dumpers=[_validate_operation_method_value],
)

_operation__bulk_id = Attribute(
    name="bulkId",
    type_=type_.String,
)

_operation__version = Attribute(
    name="version",
    type_=type_.String,
)

_operation__path = Attribute(
    name="path",
    type_=type_.String,
    required=True,
)

_operation__data = Attribute(
    name="data",
    type_=type_.Unknown,
)


request_operations = ComplexAttribute(
    sub_attributes=[
        _operation__method,
        _operation__bulk_id,
        _operation__version,
        _operation__path,
        _operation__data,
    ],
    name="Operations",
    required=True,
    multi_valued=True,
    complex_parsers=[validate_request_operations],
)

fail_on_errors = Attribute(
    name="failOnErrors",
    type_=type_.Integer,
)


class BulkRequest(BaseSchema):
    def __init__(self):
        super().__init__(
            schema="urn:ietf:params:scim:api:messages:2.0:BulkRequest",
            attrs=[fail_on_errors, request_operations],
        )


def validate_response_operations(
    operations_data: List[SCIMDataContainer],
) -> Tuple[List[SCIMDataContainer], ValidationIssues]:
    issues = ValidationIssues()
    for i, operation_data in enumerate(operations_data):
        method = operation_data[_operation__method.rep]
        issues.merge(
            issues=_validate_operation_method_existence(method),
            location=(i, _operation__method.rep.attr),
        )
        bulk_id = operation_data[_operation__bulk_id.rep]
        if method == "POST" and bulk_id in [None, Missing]:
            issues.add(
                issue=ValidationError.missing(),
                proceed=False,
                location=(i, _operation__bulk_id.rep.attr),
            )
        status = operation_data[_operation__status.rep]
        if status:
            location = operation_data[_operation__location.rep]
            if location in [None, Missing] and method and (method != "POST" or int(status) < 300):
                issues.add(
                    issue=ValidationError.missing(),
                    proceed=False,
                    location=(i, _operation__location.rep.attr),
                )
            response = operation_data[_operation__response.rep]
            if response in [None, Missing] and int(status) >= 300:
                issues.add(
                    issue=ValidationError.missing(),
                    proceed=False,
                    location=(i, _operation__response.rep.attr),
                )
        elif status in [None, Missing]:
            issues.add(
                issue=ValidationError.missing(),
                proceed=False,
                location=(i, _operation__status.rep.attr),
            )
    return operations_data, issues


_operation__location = Attribute(
    name="location",
    type_=type_.ExternalReference,
)

_operation__response = Attribute(
    name="response",
    type_=type_.Unknown,
)


def _validate_status(value: Any) -> Tuple[Union[Invalid, str], ValidationIssues]:
    issues = ValidationIssues()
    try:
        int(value)
    except ValueError:
        issues.add(
            issue=ValidationError.bad_value_syntax(),
            proceed=False,
        )
        value = Invalid
    return value, issues


_operation__status = Attribute(
    name="status",
    type_=type_.String,
    required=True,
    dumpers=[_validate_status],
)


response_operations = ComplexAttribute(
    sub_attributes=[
        _operation__method,
        _operation__bulk_id,
        _operation__version,
        _operation__location,
        _operation__status,
        _operation__response,
    ],
    name="Operations",
    required=True,
    multi_valued=True,
    complex_dumpers=[validate_response_operations],
)


class BulkResponse(BaseSchema):
    def __init__(self):
        super().__init__(
            schema="urn:ietf:params:scim:api:messages:2.0:BulkResponse", attrs=[response_operations]
        )
