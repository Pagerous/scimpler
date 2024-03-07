import re
from typing import List, Tuple

from src.data import type as type_
from src.data.attributes import Attribute, ComplexAttribute
from src.data.container import Missing, SCIMDataContainer
from src.error import ValidationError, ValidationIssues
from src.schemas import BaseSchema

_RESOURCE_TYPE_REGEX = re.compile(r"/\w+")
_RESOURCE_OBJECT_REGEX = re.compile(r"/\w+/.*")


def validate_request_operations(
    operations_data: List[SCIMDataContainer],
) -> Tuple[List[SCIMDataContainer], ValidationIssues]:
    issues = ValidationIssues()
    allowed_methods = ["GET", "POST", "PATCH", "PUT", "DELETE"]
    for i, operation_data in enumerate(operations_data):
        method = operation_data[_operation__method.rep]
        if method in [None, Missing]:
            issues.add(
                issue=ValidationError.missing(),
                proceed=False,
                location=(i, _operation__method.rep.attr),
            )
        elif method not in allowed_methods:
            issues.add(
                issue=ValidationError.must_be_one_of(allowed_methods, method),
                proceed=True,
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

_operation__location = Attribute(
    name="location",
    type_=type_.ExternalReference,
    required=True,
)

_operation__response = Attribute(
    name="response",
    type_=type_.Unknown,
)

_operation__status = Attribute(
    name="status",
    type_=type_.String,
    required=True,
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

response_operations = ComplexAttribute(
    sub_attributes=[
        _operation__method,
        _operation__bulk_id,
        _operation__version,
        _operation__location,
        _operation__status,
    ],
    name="Operations",
    required=True,
    multi_valued=True,
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

    def __repr__(self) -> str:
        return "BulkRequest"


class BulkResponse(BaseSchema):
    def __init__(self):
        super().__init__(
            schema="urn:ietf:params:scim:api:messages:2.0:BulkResponse", attrs=[response_operations]
        )

    def __repr__(self) -> str:
        return "BulkResponse"
