import re
from copy import deepcopy
from typing import Any, List

from src.data.attributes import Complex, ExternalReference, Integer, String, Unknown
from src.data.container import Missing, SCIMDataContainer
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


def validate_request_operations(value: List[SCIMDataContainer]) -> ValidationIssues:
    issues = ValidationIssues()
    for i, item in enumerate(value):
        method = item.get(_operation__method.rep)
        issues.merge(
            issues=_validate_operation_method_existence(method),
            location=(i, _operation__method.rep.attr),
        )
        bulk_id = item.get(_operation__bulk_id.rep)
        if method == "POST" and bulk_id in [None, Missing]:
            issues.add_error(
                issue=ValidationError.missing(),
                proceed=False,
                location=(i, _operation__bulk_id.rep.attr),
            )
        path = item.get(_operation__path.rep)
        if path in [None, Missing]:
            issues.add_error(
                issue=ValidationError.missing(),
                proceed=False,
                location=(i, _operation__path.rep.attr),
            )
        else:
            if method == "POST" and not _RESOURCE_TYPE_REGEX.fullmatch(path):
                issues.add_error(
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
                issues.add_error(
                    issue=ValidationError.resource_object_endpoint_required(),
                    proceed=False,
                    location=(i, _operation__path.rep.attr),
                )
        data = item.get(_operation__data.rep)
        if method in ["POST", "PUT", "PATCH"] and data in [None, Missing]:
            issues.add_error(
                issue=ValidationError.missing(),
                proceed=False,
                location=(i, _operation__data.rep.attr),
            )
    return issues


def parse_request_operations(value: List[SCIMDataContainer]) -> List[SCIMDataContainer]:
    value = deepcopy(value)
    for i, item in enumerate(value):
        method = item.get(_operation__method.rep)
        if method in ["GET", "DELETE"]:
            item.pop(_operation__data.rep)
    return value


_operation__method = String(
    name="method",
    required=True,
    canonical_values=["GET", "POST", "PATCH", "PUT", "DELETE"],
    restrict_canonical_values=True,
)

_operation__bulk_id = String("bulkId")

_operation__version = String("version")

_operation__path = String(
    name="path",
    required=True,
)

_operation__data = Unknown("data")


request_operations = Complex(
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

fail_on_errors = Integer("failOnErrors")


class BulkRequest(BaseSchema):
    def __init__(self):
        super().__init__(
            schema="urn:ietf:params:scim:api:messages:2.0:BulkRequest",
            attrs=[fail_on_errors, request_operations],
        )


def validate_response_operations(value: List[SCIMDataContainer]) -> ValidationIssues:
    issues = ValidationIssues()
    for i, item in enumerate(value):
        method = item.get(_operation__method.rep)
        issues.merge(
            issues=_validate_operation_method_existence(method),
            location=(i, _operation__method.rep.attr),
        )
        bulk_id = item.get(_operation__bulk_id.rep)
        if method == "POST" and bulk_id in [None, Missing]:
            issues.add_error(
                issue=ValidationError.missing(),
                proceed=False,
                location=(i, _operation__bulk_id.rep.attr),
            )
        status = item.get(_operation__status.rep)
        if method and status:
            location = item.get(_operation__location.rep)
            if location in [None, Missing] and method and (method != "POST" or int(status) < 300):
                issues.add_error(
                    issue=ValidationError.missing(),
                    proceed=False,
                    location=(i, _operation__location.rep.attr),
                )
            response = item.get(_operation__response.rep)
            if response in [None, Missing] and int(status) >= 300:
                issues.add_error(
                    issue=ValidationError.missing(),
                    proceed=False,
                    location=(i, _operation__response.rep.attr),
                )
        elif status in [None, Missing]:
            issues.add_error(
                issue=ValidationError.missing(),
                proceed=False,
                location=(i, _operation__status.rep.attr),
            )
    return issues


_operation__location = ExternalReference("location")

_operation__response = Unknown("response")


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


_operation__status = String(
    name="status",
    required=True,
    validators=[_validate_status],
)


response_operations = Complex(
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
