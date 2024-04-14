import re
from copy import deepcopy
from typing import Any, List

from src.data import type as type_
from src.data.attributes import Attribute, ComplexAttribute
from src.data.container import Missing, SCIMDataContainer
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


def validate_request_operations(value: List[SCIMDataContainer]) -> ValidationIssues:
    issues = ValidationIssues()
    for i, item in enumerate(value):
        method = item[_operation__method.rep]
        issues.merge(
            issues=_validate_operation_method_existence(method),
            location=(i, _operation__method.rep.attr),
        )
        bulk_id = item[_operation__bulk_id.rep]
        if method == "POST" and bulk_id in [None, Missing]:
            issues.add(
                issue=ValidationError.missing(),
                proceed=False,
                location=(i, _operation__bulk_id.rep.attr),
            )
        path = item[_operation__path.rep]
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
        data = item[_operation__data.rep]
        if method in ["POST", "PUT", "PATCH"] and data in [None, Missing]:
            issues.add(
                issue=ValidationError.missing(),
                proceed=False,
                location=(i, _operation__data.rep.attr),
            )
    return issues


def parse_request_operations(value: List[SCIMDataContainer]) -> List[SCIMDataContainer]:
    value = deepcopy(value)
    for i, item in enumerate(value):
        method = item[_operation__method.rep]
        if method in ["GET", "DELETE"]:
            item.pop(_operation__data.rep)
    return value


_operation__method = Attribute(
    name="method",
    type_=type_.String,
    required=True,
    canonical_values=["GET", "POST", "PATCH", "PUT", "DELETE"],
    validate_canonical_values=True,
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
    validators=[validate_request_operations],
    parser=parse_request_operations,
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


def validate_response_operations(value: List[SCIMDataContainer]) -> ValidationIssues:
    issues = ValidationIssues()
    for i, item in enumerate(value):
        method = item[_operation__method.rep]
        issues.merge(
            issues=_validate_operation_method_existence(method),
            location=(i, _operation__method.rep.attr),
        )
        bulk_id = item[_operation__bulk_id.rep]
        if method == "POST" and bulk_id in [None, Missing]:
            issues.add(
                issue=ValidationError.missing(),
                proceed=False,
                location=(i, _operation__bulk_id.rep.attr),
            )
        status = item[_operation__status.rep]
        if status:
            location = item[_operation__location.rep]
            if location in [None, Missing] and method and (method != "POST" or int(status) < 300):
                issues.add(
                    issue=ValidationError.missing(),
                    proceed=False,
                    location=(i, _operation__location.rep.attr),
                )
            response = item[_operation__response.rep]
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
    return issues


_operation__location = Attribute(
    name="location",
    type_=type_.ExternalReference,
)

_operation__response = Attribute(
    name="response",
    type_=type_.Unknown,
)


def _validate_status(value: Any) -> ValidationIssues:
    issues = ValidationIssues()
    try:
        int(value)
    except ValueError:
        issues.add(
            issue=ValidationError.bad_value_syntax(),
            proceed=False,
        )
    return issues


_operation__status = Attribute(
    name="status",
    type_=type_.String,
    required=True,
    validators=[_validate_status],
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
    validators=[validate_response_operations],
)


class BulkResponse(BaseSchema):
    def __init__(self):
        super().__init__(
            schema="urn:ietf:params:scim:api:messages:2.0:BulkResponse", attrs=[response_operations]
        )
