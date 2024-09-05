import re
from collections.abc import Mapping
from copy import deepcopy
from typing import Any, Optional

from scimpler.data.attrs import Complex, ExternalReference, Integer, String, Unknown
from scimpler.data.schemas import BaseSchema
from scimpler.data.scim_data import Missing, SCIMData
from scimpler.error import ValidationError, ValidationIssues
from scimpler.schemas.error import ErrorSchema

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


class BulkRequestSchema(BaseSchema):
    schema = "urn:ietf:params:scim:api:messages:2.0:BulkRequest"
    base_attrs = [
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
    ]

    def __init__(
        self,
        sub_schemas: Mapping[str, Mapping[str, Optional[BaseSchema]]],
    ):
        super().__init__()
        self._sub_schemas = sub_schemas

    def _deserialize(self, data: SCIMData) -> SCIMData:
        return self._process(data, "deserialize")

    def _serialize(self, data: SCIMData) -> SCIMData:
        return self._process(data, "serialize")

    def _process(self, data: SCIMData, method: str) -> SCIMData:
        operations = data.get("Operations", [])
        processed = []
        for operation in operations:
            operation = SCIMData(operation)
            schema = self.get_schema(operation)
            if schema is None:
                processed.append(operation)
                continue
            request = operation.get("data")
            if not request:
                processed.append(operation)
                continue
            operation.set("data", getattr(schema, method)(request))
            processed.append(operation)
        data["Operations"] = processed
        return data

    def get_schema(self, operation: Mapping) -> Optional[BaseSchema]:
        method = operation.get("method", "").upper()
        if method not in self._sub_schemas:
            return None
        if method == "POST":
            path_parts = operation.get("path", "").split("/", 1)
        else:
            path_parts = operation.get("path", "").split("/", 2)
        if len(path_parts) < 2:
            return None
        return self._sub_schemas[method].get(path_parts[1])


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


class BulkResponseSchema(BaseSchema):
    schema = "urn:ietf:params:scim:api:messages:2.0:BulkResponse"
    base_attrs = [
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
    ]

    def __init__(
        self,
        sub_schemas: Mapping[str, Mapping[str, Optional[BaseSchema]]],
        error_schema: ErrorSchema,
    ):
        super().__init__()
        self._sub_schemas = sub_schemas
        self._error_schema = error_schema

    def _deserialize(self, data: SCIMData) -> SCIMData:
        return self._process(data, "deserialize")

    def _serialize(self, data: SCIMData) -> SCIMData:
        return self._process(data, "serialize")

    def _process(self, data: SCIMData, method: str) -> SCIMData:
        operations = data.get("Operations", [])
        processed = []
        for operation in operations:
            operation = SCIMData(operation)
            schema = self.get_schema(operation)
            if schema is None:
                processed.append(operation)
                continue
            response = operation.get("response")
            if not response:
                processed.append(operation)
                continue
            operation.set("response", getattr(schema, method)(response))
            processed.append(operation)
        data["Operations"] = processed
        return data

    def get_schema(self, operation: Mapping) -> Optional[BaseSchema]:
        operation = SCIMData(operation)
        status = operation.get("status")
        if status in [None, Missing]:
            return None
        if int(status) >= 300:
            return self._error_schema
        location = operation.get("location", "")
        for resource_name, schema in self._sub_schemas.get(
            operation.get("method", "").upper(), {}
        ).items():
            if f"/{resource_name}/" in location:
                return schema
        return None
