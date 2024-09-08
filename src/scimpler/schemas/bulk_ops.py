import re
from collections.abc import Mapping
from copy import deepcopy
from typing import Any, Optional

from scimpler.data.attrs import Complex, ExternalReference, Integer, String, Unknown
from scimpler.data.schemas import BaseSchema
from scimpler.data.scim_data import Invalid, Missing, ScimData
from scimpler.error import ValidationError, ValidationIssues
from scimpler.schemas.error import ErrorSchema

_RESOURCE_TYPE_REGEX = re.compile(r"/\w+")
_RESOURCE_OBJECT_REGEX = re.compile(r"/\w+/.*")


def validate_operation_method_existence(method: Any) -> ValidationIssues:
    issues = ValidationIssues()
    if method in [None, Missing]:
        issues.add_error(
            issue=ValidationError.missing(),
            proceed=False,
        )
    return issues


def validate_request_operations(value: list[ScimData]) -> ValidationIssues:
    issues = ValidationIssues()
    for i, item in enumerate(value):
        method = item.get("method")
        issues.merge(
            issues=validate_operation_method_existence(method),
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
                location=[i, "path"],
            )
        else:
            if method == "POST" and not _RESOURCE_TYPE_REGEX.fullmatch(path):
                issues.add_error(
                    issue=ValidationError.bad_value_syntax(),
                    proceed=False,
                    location=[i, "path"],
                )
                item["path"] = Invalid
            elif method in [
                "GET",
                "PATCH",
                "PUT",
                "DELETE",
            ] and not _RESOURCE_OBJECT_REGEX.fullmatch(path):
                issues.add_error(
                    issue=ValidationError.bad_value_syntax(),
                    proceed=False,
                    location=[i, "path"],
                )
                item["path"] = Invalid
        data = item.get("data")
        if method in ["POST", "PUT", "PATCH"] and data in [None, Missing]:
            issues.add_error(
                issue=ValidationError.missing(),
                proceed=False,
                location=(i, "data"),
            )
    return issues


def process_request_operations(value: list[ScimData]) -> list[ScimData]:
    value = deepcopy(value)
    for i, item in enumerate(value):
        method = item.get("method")
        if method in ["GET", "DELETE"]:
            item.pop("data")
    return value


class BulkRequestSchema(BaseSchema):
    """
    BulkRequest schema, identified by `urn:ietf:params:scim:api:messages:2.0:BulkRequest` URI.

    Provides data validation and checks if:

    - `method` is provided,
    - `bulkId` is provided for `POST` method,
    - `path` is provided,
    - `path` is valid, depending on the method type,
    - `path` specifies one of supported resources,
    - `data` is provided for `POST`, `PUT`, and `PATCH` methods.

    During (de)serialization, if method type is `GET` or `DELETE`, the `data` if provided,
    is dropped. For all other methods, the `data` is (de)serialized together with rest of the
    fields.
    """

    schema = "urn:ietf:params:scim:api:messages:2.0:BulkRequest"
    base_attrs = [
        Integer("failOnErrors"),
        Complex(
            name="Operations",
            required=True,
            multi_valued=True,
            validators=[validate_request_operations],
            deserializer=process_request_operations,
            serializer=process_request_operations,
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
        """
        Args:
            sub_schemas: Schemas supported by the bulk request, per resource type endpoint
                and method type.

        Examples:
            >>> from scimpler.schemas import UserSchema, GroupSchema, PatchOpSchema
            >>>
            >>> user, group = UserSchema(), GroupSchema()
            >>> user_patch = PatchOpSchema(user)
            >>> group_patch = PatchOpSchema(group)
            >>> BulkRequestSchema(
            >>>     {
            >>>         "GET": {
            >>>             user.endpoint: user,
            >>>             group.endpoint: group,
            >>>         },
            >>>         "PATCH": {
            >>>             user.endpoint: user_patch,
            >>>             group.endpoint: group_patch,
            >>>         }
            >>>     }
            >>> )
        """
        super().__init__()
        self._sub_schemas = sub_schemas

    def _deserialize(self, data: ScimData) -> ScimData:
        return self._process(data, "deserialize")

    def _serialize(self, data: ScimData) -> ScimData:
        return self._process(data, "serialize")

    def _validate(self, data: ScimData, **kwargs) -> ValidationIssues:
        issues = ValidationIssues()
        path_rep = self.attrs.operations__path
        paths = data.get(self.attrs.operations__path)
        methods = data.get(self.attrs.operations__method)
        if not all([paths, methods]):
            return issues

        for i, (path, data_item, method) in enumerate(zip(paths, data, methods)):
            if not all([path, method]):
                continue
            if method == "POST":
                resource_type_endpoint = path
            else:
                resource_type_endpoint = f"/{path.split('/', 2)[1]}"
            validator = self._sub_schemas[method].get(resource_type_endpoint)
            if validator is None:
                issues.add_error(
                    issue=ValidationError.unknown_operation_resource(),
                    proceed=False,
                    location=[path_rep.attr, i, path_rep.sub_attr],
                )
        return issues

    def _process(self, data: ScimData, method: str) -> ScimData:
        operations = data.get("Operations", [])
        processed = []
        for operation in operations:
            operation = ScimData(operation)
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
        """
        Returns one of the sub-schemas, depending on the provided `operation` data. Returns
        `None` if an operation's method is not supported, or path indicates unsupported resource
        type.
        """
        method = operation.get("method", "").upper()
        if method not in self._sub_schemas:
            return None
        path = operation.get("path", "")
        if "/" not in path:
            return None
        if method != "POST":
            path = f"/{path.split('/', 2)[1]}"
        return self._sub_schemas[method].get(path)


def validate_response_operations(value: list[ScimData]) -> ValidationIssues:
    issues = ValidationIssues()
    for i, item in enumerate(value):
        method = item.get("method")
        issues.merge(
            issues=validate_operation_method_existence(method),
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
            if location in [None, Missing] and (method != "POST" or int(status) < 300):
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


def validate_status(value: Any) -> ValidationIssues:
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
    """
    BulkResponse schema, identified by `urn:ietf:params:scim:api:messages:2.0:BulkResponse` URI.

    Provides data validation and checks if:

    - `method` is provided,
    - `bulkId` is provided for `POST` method,
    - `status` is provided,
    - `location` is provided for successful operations,
    - `location` specifies one of supported resources,
    - `response` is provided for unsuccessful operations.
    """

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
                    validators=[validate_status],
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
        """
        Args:
            sub_schemas: Schemas supported by the bulk response, per resource type endpoint
                and method type.

        Examples:
            >>> from scimpler.schemas import UserSchema, GroupSchema
            >>>
            >>> user, group = UserSchema(), GroupSchema()
            >>> BulkResponseSchema(
            >>>     {
            >>>         "GET": {
            >>>             user.endpoint: user,
            >>>             group.endpoint: group,
            >>>         },
            >>>         "PATCH": {
            >>>             user.endpoint: user,
            >>>             group.endpoint: group,
            >>>         }
            >>>     }
            >>> )
        """
        super().__init__()
        self._sub_schemas = sub_schemas
        self._error_schema = error_schema

    def _validate(self, data: ScimData, **kwargs) -> ValidationIssues:
        issues = ValidationIssues()
        locations = data.get(self.attrs.operations__location)
        methods = data.get(self.attrs.operations__method)
        if not all([locations, methods]):
            return issues

        for i, (method, location) in enumerate(zip(methods, locations)):
            if not method:
                continue
            if location:
                for endpoint, validator in self._sub_schemas[method].items():
                    if endpoint in location:
                        break
                else:
                    issues.add_error(
                        issue=ValidationError.unknown_operation_resource(),
                        proceed=False,
                        location=["Operations", i, "location"],
                    )
                    data["Operations"][i]["location"] = Invalid
        return issues

    def _deserialize(self, data: ScimData) -> ScimData:
        return self._process(data, "deserialize")

    def _serialize(self, data: ScimData) -> ScimData:
        return self._process(data, "serialize")

    def _process(self, data: ScimData, method: str) -> ScimData:
        operations = data.get("Operations", [])
        processed = []
        for operation in operations:
            operation = ScimData(operation)
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
        """
        Returns one of the sub-schemas, depending on the provided `operation` data. Returns
        `None` if `status` is not present in the `operation`, or if an operation's method
        is not supported, or location indicates unsupported resource type.
        """
        operation = ScimData(operation)
        status = operation.get("status")
        if status in [None, Missing]:
            return None
        if int(status) >= 300:
            return self._error_schema
        location = operation.get("location", "")
        for endpoint, schema in self._sub_schemas.get(
            operation.get("method", "").upper(), {}
        ).items():
            if endpoint in location:
                return schema
        return None
