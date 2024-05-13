import abc
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from src.assets.config import ServiceProviderConfig
from src.assets.schemas import bulk_ops, error, list_response, patch_op, search_request
from src.assets.schemas.resource_type import ResourceType
from src.assets.schemas.schema import Schema
from src.assets.schemas.search_request import get_search_request_schema
from src.attributes import Attribute, AttributeMutability, AttributeReturn, Complex
from src.attributes_presence import AttributePresenceChecker
from src.container import BoundedAttrRep, Missing, SCIMDataContainer
from src.error import ValidationError, ValidationIssues, ValidationWarning
from src.filter import Filter
from src.path import PatchPath
from src.schemas import BaseResourceSchema, BaseSchema, ResourceSchema
from src.sorter import Sorter


class Validator(abc.ABC):
    def __init__(self, config: ServiceProviderConfig):
        self._config = config

    @property
    def config(self) -> ServiceProviderConfig:
        return self._config

    @property
    def request_schema(self) -> BaseSchema:
        raise NotImplementedError

    @property
    def response_schema(self) -> BaseSchema:
        raise NotImplementedError

    @abc.abstractmethod
    def validate_request(
        self,
        *,
        body: Optional[Dict[str, Any]] = None,
        query_string: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
    ) -> ValidationIssues:
        ...

    @abc.abstractmethod
    def validate_response(
        self,
        *,
        status_code: int,
        body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> ValidationIssues:
        ...


class Error(Validator):
    def __init__(self, config: ServiceProviderConfig):
        super().__init__(config)
        self._schema = error.Error()

    @property
    def response_schema(self) -> error.Error:
        return self._schema

    def validate_request(
        self,
        *,
        body: Optional[Dict[str, Any]] = None,
        query_string: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
    ) -> ValidationIssues:
        raise NotImplementedError

    def validate_response(
        self,
        *,
        status_code: int,
        body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> ValidationIssues:
        body_location = ("body",)
        issues = ValidationIssues()
        body = SCIMDataContainer(body or {})
        issues_ = self._schema.validate(body)
        issues.merge(issues_, location=body_location)
        if not issues.can_proceed(body_location):
            return issues

        issues.merge(
            issues=AttributePresenceChecker()(body, self._schema.attrs, "RESPONSE"),
            location=body_location,
        )
        status_attr_rep = self._schema.attrs.status.rep
        if issues.can_proceed(body_location + _location(status_attr_rep)):
            issues.merge(
                validate_error_status_code_consistency(
                    status_code_attr_name=status_attr_rep.attr,
                    status_code_body=body.get(status_attr_rep),
                    status_code=status_code,
                )
            )
        issues.merge(validate_error_status_code(status_code))
        return issues


def validate_error_status_code_consistency(
    status_code_attr_name: str,
    status_code_body: str,
    status_code: int,
) -> ValidationIssues:
    issues = ValidationIssues()
    if str(status_code) != status_code_body:
        issues.add_error(
            issue=ValidationError.error_status_mismatch(str(status_code), status_code_body),
            location=("body", status_code_attr_name),
            proceed=True,
        )
        issues.add_error(
            issue=ValidationError.error_status_mismatch(str(status_code), status_code_body),
            location=("status",),
            proceed=True,
        )
    return issues


def validate_error_status_code(status_code: int) -> ValidationIssues:
    issues = ValidationIssues()
    if not 200 <= status_code < 600:
        issues.add_error(
            issue=ValidationError.bad_value_syntax(),
            location=("status",),
            proceed=True,
        )
    return issues


def validate_resource_location_in_header(
    headers: Any,
    header_required: bool,
) -> ValidationIssues:
    issues = ValidationIssues()
    headers = headers or {}
    if not isinstance(headers, Dict) or "Location" not in (headers or {}):
        if header_required:
            issues.add_error(
                issue=ValidationError.missing(),
                proceed=False,
                location=("Location",),
            )
    return issues


def validate_resource_location_consistency(
    meta_location: str,
    headers_location: str,
) -> ValidationIssues:
    issues = ValidationIssues()
    if meta_location != headers_location:
        issues.add_error(
            issue=ValidationError.must_be_equal_to("'Location' header"),
            location=("body", "meta", "location"),
            proceed=True,
        )
        issues.add_error(
            issue=ValidationError.must_be_equal_to("'meta.location'"),
            location=("headers", "Location"),
            proceed=True,
        )
    return issues


def validate_status_code(expected: int, actual: int) -> ValidationIssues:
    issues = ValidationIssues()
    if expected != actual:
        issues.add_error(
            issue=ValidationError.bad_status_code(expected, actual),
            proceed=True,
        )
    return issues


def _validate_body(schema: BaseSchema, body: SCIMDataContainer, **kwargs) -> ValidationIssues:
    issues = schema.validate(body)
    if issues.can_proceed():
        issues.merge(
            issues=AttributePresenceChecker(**kwargs)(body, schema.attrs, "REQUEST"),
        )
    return issues


def _validate_resource_output_body(
    schema: BaseResourceSchema,
    config: ServiceProviderConfig,
    location_header_required: bool,
    expected_status_code: int,
    status_code: int,
    body: SCIMDataContainer,
    headers: Dict[str, Any],
    presence_checker: Optional[AttributePresenceChecker],
) -> ValidationIssues:
    issues = ValidationIssues()
    body_location = ("body",)
    issues.merge(schema.validate(body), location=body_location)

    issues.merge(
        issues=validate_resource_location_in_header(headers, location_header_required),
        location=("headers",),
    )
    issues.merge(
        issues=validate_status_code(expected_status_code, status_code),
        location=("status",),
    )
    issues.merge(
        issues=(presence_checker or AttributePresenceChecker())(
            data=body,
            attrs=schema.attrs,
            direction="RESPONSE",
        ),
        location=body_location,
    )
    meta_location = schema.attrs.meta__location.rep
    location_header = headers.get("Location")
    if (
        issues.can_proceed(body_location + _location(meta_location), ("headers", "Location"))
        and location_header is not None
    ):
        issues.merge(
            issues=validate_resource_location_consistency(
                meta_location=body.get(meta_location),
                headers_location=location_header,
            ),
        )

    etag = headers.get("ETag")
    version_rep = schema.attrs.meta__version.rep
    version = body.get(version_rep)
    if all([etag, version]) and etag != version:
        issues.add_error(
            issue=ValidationError.must_be_equal_to("'ETag' header"),
            proceed=True,
            location=body_location + _location(version_rep),
        )
        issues.add_error(
            issue=ValidationError.must_be_equal_to("'meta.version'"),
            proceed=True,
            location=("headers", "ETag"),
        )
    elif config.etag.supported:
        if etag is None:
            issues.add_error(
                issue=ValidationError.missing(),
                location=("headers", "ETag"),
                proceed=False,
            )

        if version in [None, Missing]:
            issues.add_error(
                issue=ValidationError.missing(),
                proceed=False,
                location=body_location + _location(version_rep),
            )
    return issues


class ResourceObjectGET(Validator):
    def __init__(self, config: ServiceProviderConfig, *, resource_schema: BaseResourceSchema):
        super().__init__(config)
        self._schema = resource_schema
        self._response_schema = resource_schema.clone(
            lambda attr: attr.returned != AttributeReturn.NEVER
        )

    @property
    def response_schema(self) -> BaseResourceSchema:
        return self._response_schema

    def validate_request(
        self,
        *,
        body: Optional[Dict[str, Any]] = None,
        query_string: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
    ) -> ValidationIssues:
        issues = ValidationIssues()
        query_string = query_string or {}
        issues.merge(
            search_request.SearchRequest().validate(
                {
                    "attributes": query_string.get("attributes"),
                    "excludeAttributes": query_string.get("excludeAttributes"),
                }
            ),
            location=("query_string",),
        )
        return issues

    def validate_response(
        self,
        *,
        status_code: int,
        body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> ValidationIssues:
        return _validate_resource_output_body(
            schema=self._schema,
            config=self.config,
            location_header_required=False,
            expected_status_code=200,
            status_code=status_code,
            body=SCIMDataContainer(body or {}),
            headers=headers or {},
            presence_checker=kwargs.get("presence_checker"),
        )


class ServiceResourceObjectGET(ResourceObjectGET):
    def validate_request(
        self,
        *,
        body: Optional[Dict[str, Any]] = None,
        query_string: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
    ) -> ValidationIssues:
        return ValidationIssues()


class ResourceObjectPUT(Validator):
    def __init__(self, config: ServiceProviderConfig, *, resource_schema: ResourceSchema):
        super().__init__(config)
        self._request_schema = resource_schema.clone(
            lambda attr: attr.mutability != AttributeMutability.READ_ONLY or attr.required
        )
        self._response_schema = resource_schema.clone(
            lambda attr: attr.returned != AttributeReturn.NEVER
        )
        self._schema = resource_schema

    @property
    def request_schema(self) -> ResourceSchema:
        return self._request_schema

    @property
    def response_schema(self) -> ResourceSchema:
        return self._schema

    def validate_request(
        self,
        *,
        body: Optional[Dict[str, Any]] = None,
        query_string: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
    ) -> ValidationIssues:
        issues = ValidationIssues()
        query_string = query_string or {}
        issues.merge(
            search_request.SearchRequest().validate(
                {
                    "attributes": query_string.get("attributes"),
                    "excludeAttributes": query_string.get("excludeAttributes"),
                }
            ),
            location=("query_string",),
        )
        issues.merge(
            issues=_validate_body(
                schema=self._schema,
                body=SCIMDataContainer(body or {}),
                ignore_issuer=[self._schema.attrs.id],
            ),
            location=("body",),
        )
        return issues

    def validate_response(
        self,
        *,
        status_code: int,
        body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> ValidationIssues:
        return _validate_resource_output_body(
            schema=self._schema,
            config=self.config,
            location_header_required=False,
            expected_status_code=200,
            status_code=status_code,
            body=SCIMDataContainer(body or {}),
            headers=headers or {},
            presence_checker=kwargs.get("presence_checker"),
        )


class ResourcesPOST(Validator):
    def __init__(self, config: ServiceProviderConfig, *, resource_schema: ResourceSchema):
        super().__init__(config)
        self._schema = resource_schema
        self._request_schema = resource_schema.clone(
            lambda attr: attr.mutability != AttributeMutability.READ_ONLY
        )
        self._response_schema = resource_schema.clone(
            lambda attr: attr.returned != AttributeReturn.NEVER
        )

    @property
    def request_schema(self) -> ResourceSchema:
        return self._request_schema

    @property
    def response_schema(self) -> ResourceSchema:
        return self._response_schema

    def validate_request(
        self,
        *,
        body: Optional[Dict[str, Any]] = None,
        query_string: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
    ) -> ValidationIssues:
        issues = ValidationIssues()
        body, query_string = SCIMDataContainer(body or {}), query_string or {}
        issues.merge(
            search_request.SearchRequest().validate(
                {
                    "attributes": query_string.get("attributes"),
                    "excludeAttributes": query_string.get("excludeAttributes"),
                }
            ),
            location=("query_string",),
        )
        issues.merge(
            issues=_validate_body(self._schema, body),
            location=("body",),
        )
        return issues

    def validate_response(
        self,
        *,
        status_code: int,
        body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> ValidationIssues:
        issues = ValidationIssues()
        if not body:
            issues.add_warning(issue=ValidationWarning.missing(), location=("body",))
            return issues

        body = SCIMDataContainer(body)
        issues = _validate_resource_output_body(
            schema=self._schema,
            config=self.config,
            location_header_required=True,
            expected_status_code=201,
            status_code=status_code,
            body=body,
            headers=headers or {},
            presence_checker=kwargs.get("presence_checker"),
        )
        if body.get(self.response_schema.attrs.meta__created.rep) != body.get(
            self.response_schema.attrs.meta__lastModified.rep
        ):
            issues.add_error(
                issue=ValidationError.must_be_equal_to("'meta.created'"),
                proceed=True,
                location=("body", *_location(self._schema.attrs.meta__lastModified.rep)),
            )
        return issues


def validate_resources_sorted(
    sorter: Sorter,
    resources: List[Any],
    resource_schemas: Sequence[ResourceSchema],
) -> ValidationIssues:
    issues = ValidationIssues()
    if resources != sorter(resources, schema=resource_schemas):
        issues.add_error(
            issue=ValidationError.resources_not_sorted(),
            proceed=True,
        )
    return issues


def validate_resources_attributes_presence(
    presence_checker: AttributePresenceChecker,
    resources: List[SCIMDataContainer],
    resource_schemas: Sequence[ResourceSchema],
) -> ValidationIssues:
    issues = ValidationIssues()
    for i, (resource, schema) in enumerate(zip(resources, resource_schemas)):
        issues.merge(
            issues=presence_checker(resource, schema.attrs, "RESPONSE"),
            location=(i,),
        )
    return issues


def validate_number_of_resources(
    count: Optional[int],
    total_results: Any,
    resources: List[Any],
) -> ValidationIssues:
    issues = ValidationIssues()
    n_resources = len(resources)
    if total_results < n_resources:
        issues.add_error(
            issue=ValidationError.total_results_mismatch(
                total_results=total_results, n_resources=n_resources
            ),
            proceed=True,
        )
    if count is None and total_results > n_resources:
        issues.add_error(
            issue=ValidationError.too_little_results(must="be equal to 'totalResults'"),
            proceed=True,
        )
    if count is not None and count < n_resources:
        issues.add_error(
            issue=ValidationError.too_many_results(must="be lesser or equal to 'count' parameter"),
            proceed=True,
        )
    return issues


def validate_pagination_info(
    schema: list_response.ListResponse,
    count: Optional[int],
    total_results: Any,
    resources: List[Any],
    start_index: Any,
    items_per_page: Any,
) -> ValidationIssues:
    issues = ValidationIssues()
    n_resources = len(resources)
    is_pagination = (count or 0) > 0 and total_results > n_resources
    if is_pagination:
        if start_index in [None, Missing]:
            issues.add_error(
                issue=ValidationError.missing(),
                location=_location(schema.attrs.startindex.rep),
                proceed=False,
            )
        if items_per_page in [None, Missing]:
            issues.add_error(
                issue=ValidationError.missing(),
                location=_location(schema.attrs.itemsperpage.rep),
                proceed=False,
            )
    return issues


def validate_start_index_consistency(
    start_index: int,
    start_index_body: int,
) -> ValidationIssues:
    issues = ValidationIssues()
    if start_index_body > start_index:
        issues.add_error(
            issue=ValidationError.response_value_does_not_correspond_to_parameter(
                response_key="startIndex",
                response_value=start_index_body,
                query_param_name="startIndex",
                query_param_value=start_index,
                reason="bigger value than requested",
            ),
            proceed=True,
        )
    return issues


def validate_resources_filtered(
    resources: List[Any], filter_: Filter, resource_schemas: Sequence[ResourceSchema]
) -> ValidationIssues:
    issues = ValidationIssues()
    for i, (resource, schema) in enumerate(zip(resources, resource_schemas)):
        if not filter_(resource, schema):
            issues.add_error(
                issue=ValidationError.included_resource_does_not_match_filter(),
                proceed=True,
                location=(i,),
            )
    return issues


def _validate_resources_get_response(
    schema: list_response.ListResponse,
    status_code: int,
    body: SCIMDataContainer,
    start_index: int = 1,
    count: Optional[int] = None,
    filter_: Optional[Filter] = None,
    sorter: Optional[Sorter] = None,
    resource_presence_checker: Optional[AttributePresenceChecker] = None,
) -> ValidationIssues:
    issues = ValidationIssues()
    body_location = ("body",)
    resources_location = body_location + _location(schema.attrs.resources.rep)

    start_index_rep = schema.attrs.startindex.rep
    start_index_location = body_location + _location(start_index_rep)

    issues_ = schema.validate(body)
    issues.merge(issues_, location=body_location)
    issues.merge(
        issues=AttributePresenceChecker()(body, schema.attrs, "RESPONSE"),
        location=body_location,
    )
    issues.merge(
        issues=validate_status_code(200, status_code),
        location=("status",),
    )
    if issues.can_proceed(start_index_location):
        start_index_body = body.get(start_index_rep)
        if start_index_body:
            issues.merge(
                issues=validate_start_index_consistency(start_index, start_index_body),
                location=start_index_location,
            )

    if not issues.can_proceed(resources_location):
        return issues

    total_results_rep = schema.attrs.totalresults.rep
    total_results_location = body_location + _location(total_results_rep)

    items_per_page_rep = schema.attrs.itemsperpage.rep
    items_per_page_location = body_location + _location(items_per_page_rep)

    resources = body.get(schema.attrs.resources.rep)
    if resources is Missing:
        resources = []

    if issues.can_proceed(total_results_location):
        total_results = body.get(total_results_rep)
        issues.merge(
            issues=validate_number_of_resources(
                count=count,
                total_results=total_results,
                resources=resources,
            ),
            location=resources_location,
        )
        if issues.can_proceed(start_index_location, items_per_page_location):
            start_index_body = body.get(start_index_rep)
            items_per_page = body.get(items_per_page_rep)
            issues.merge(
                issues=validate_pagination_info(
                    schema=schema,
                    count=count,
                    total_results=total_results,
                    resources=resources,
                    start_index=start_index_body,
                    items_per_page=items_per_page,
                ),
                location=body_location,
            )

    if issues.has_errors(resources_location):
        return issues

    resource_schemas = schema.get_schemas_for_resources(resources)
    if filter_ is not None:
        issues.merge(
            issues=validate_resources_filtered(resources, filter_, resource_schemas, False),
            location=resources_location,
        )
    if sorter is not None:
        issues.merge(
            issues=validate_resources_sorted(sorter, resources, resource_schemas),
            location=resources_location,
        )
    if resource_presence_checker is None:
        resource_presence_checker = AttributePresenceChecker()
    issues.merge(
        issues=validate_resources_attributes_presence(
            resource_presence_checker, resources, resource_schemas
        ),
        location=resources_location,
    )

    return issues


class ServerRootResourcesGET(Validator):
    def __init__(
        self, config: ServiceProviderConfig, *, resource_schemas: Sequence[ResourceSchema]
    ):
        super().__init__(config)
        self._request_query_validation_schema = get_search_request_schema(config)
        self._response_validation_schema = list_response.ListResponse(resource_schemas)
        self._response_schema = list_response.ListResponse(
            [
                resource_schema.clone(lambda attr: attr.returned != AttributeReturn.NEVER)
                for resource_schema in resource_schemas
            ]
        )

    @property
    def response_schema(self) -> list_response.ListResponse:
        return self._response_schema

    def validate_request(
        self,
        *,
        body: Optional[Dict[str, Any]] = None,
        query_string: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
    ) -> ValidationIssues:
        issues = ValidationIssues()
        query_string = query_string or {}
        issues.merge(
            self._request_query_validation_schema.validate(query_string),
            location=("query_string",),
        )
        return issues

    def validate_response(
        self,
        *,
        status_code: int,
        body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> ValidationIssues:
        return _validate_resources_get_response(
            schema=self._response_validation_schema,
            status_code=status_code,
            body=SCIMDataContainer(body or {}),
            start_index=kwargs.get("start_index", 1),
            count=kwargs.get("count"),
            filter_=kwargs.get("filter"),
            sorter=kwargs.get("sorter"),
            resource_presence_checker=kwargs.get("presence_checker"),
        )


class ResourcesGET(ServerRootResourcesGET):
    def __init__(self, config: ServiceProviderConfig, *, resource_schema: ResourceSchema):
        super().__init__(config, resource_schemas=[resource_schema])


class SearchRequestPOST(Validator):
    def __init__(
        self, config: ServiceProviderConfig, *, resource_schemas: Sequence[ResourceSchema]
    ):
        super().__init__(config)
        self._request_validation_schema = get_search_request_schema(config)
        self._response_validation_schema = list_response.ListResponse(resource_schemas)
        self._response_schema = list_response.ListResponse(
            [
                resource_schema.clone(lambda attr: attr.returned != AttributeReturn.NEVER)
                for resource_schema in resource_schemas
            ]
        )

    @property
    def request_schema(self) -> search_request.SearchRequest:
        return self._request_validation_schema

    @property
    def response_schema(self) -> list_response.ListResponse:
        return self._response_schema

    def validate_request(
        self,
        *,
        body: Optional[Dict[str, Any]] = None,
        query_string: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
    ) -> ValidationIssues:
        issues = ValidationIssues()
        issues.merge(
            self._request_validation_schema.validate(SCIMDataContainer(body or {})),
            location=("body",),
        )
        return issues

    def validate_response(
        self,
        *,
        status_code: int,
        body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> ValidationIssues:
        return _validate_resources_get_response(
            schema=self._response_validation_schema,
            status_code=status_code,
            body=SCIMDataContainer(body or {}),
            start_index=kwargs.get("start_index", 1),
            count=kwargs.get("count"),
            filter_=kwargs.get("filter"),
            sorter=kwargs.get("sorter"),
            resource_presence_checker=kwargs.get("presence_checker"),
        )


class ResourceObjectPATCH(Validator):
    def __init__(self, config: ServiceProviderConfig, *, resource_schema: ResourceSchema):
        if not config.patch.supported:
            raise RuntimeError("patch operation is not configured")

        super().__init__(config)
        self._schema = patch_op.PatchOp(resource_schema)
        self._resource_schema = resource_schema

    @property
    def request_schema(self) -> patch_op.PatchOp:
        return self._schema

    @property
    def response_schema(self) -> ResourceSchema:
        return self._resource_schema

    def validate_request(
        self,
        *,
        body: Optional[Dict[str, Any]] = None,
        query_string: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
    ) -> ValidationIssues:
        issues = ValidationIssues()
        body, query_string = SCIMDataContainer(body or {}), query_string or {}
        issues.merge(
            search_request.SearchRequest().validate(
                {
                    "attributes": query_string.get("attributes"),
                    "excludeAttributes": query_string.get("excludeAttributes"),
                }
            ),
            location=("query_string",),
        )

        issues.merge(_validate_body(self._schema, body), location=("body",))
        operations_location = ("body", *_location(self._schema.attrs.operations.rep))

        if not issues.can_proceed(operations_location):
            return issues

        values = body.get(self._schema.attrs.operations__value.rep)
        paths = body.get(self._schema.attrs.operations__path.rep)
        ops = body.get(self._schema.attrs.operations__op.rep)

        for i, (op, value, path) in enumerate(zip(ops, values, paths)):
            if op == "remove":
                continue

            value_location = operations_location + (
                i,
                self._schema.attrs.operations__value.rep.sub_attr,
            )
            if path in [None, Missing]:
                for attr in self._resource_schema.attrs:
                    self._check_complex_sub_attrs_presence(
                        issues=issues,
                        attr=attr,
                        value=value.get(attr.rep),
                        value_location=value_location + _location(attr.rep),
                    )

            else:
                attr = self._resource_schema.attrs.get_by_path(PatchPath.deserialize(path))
                self._check_complex_sub_attrs_presence(
                    issues=issues,
                    attr=attr,
                    value=value,
                    value_location=value_location,
                )
        return issues

    @staticmethod
    def _check_complex_sub_attrs_presence(
        issues: ValidationIssues,
        attr: Attribute,
        value: Any,
        value_location,
    ) -> None:
        if not (isinstance(attr, Complex) and attr.multi_valued) or value is Missing:
            return

        presence_checker = AttributePresenceChecker()
        for j, item in enumerate(value):
            item_location = value_location + (j,)
            if not issues.has_errors(item_location):
                issues.merge(
                    issues=presence_checker(
                        data=item,
                        direction="REQUEST",
                        attrs=attr.attrs,
                    ),
                    location=item_location,
                )

    def validate_response(
        self,
        *,
        status_code: int,
        body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> ValidationIssues:
        issues = ValidationIssues()
        presence_checker = kwargs.get("presence_checker")
        if status_code == 204:
            if presence_checker is not None and presence_checker.attr_reps:
                issues.add_error(
                    issue=ValidationError.bad_status_code(200, status_code),
                    proceed=True,
                    location=("status",),
                )
            return issues
        body = SCIMDataContainer(body or {})
        issues = _validate_resource_output_body(
            schema=self._resource_schema,
            config=self.config,
            location_header_required=False,
            expected_status_code=200,
            status_code=status_code,
            body=body,
            headers=headers or {},
            presence_checker=presence_checker,
        )
        meta_location = self.response_schema.attrs.meta__version.rep
        if body.get(meta_location) is Missing:
            issues.pop_error(("body", *_location(meta_location)), 11)
            issues.pop_error(("body", *_location(meta_location)), 15)
            issues.pop_error(("headers", "ETag"), 11)
        return issues


class ResourceObjectDELETE(Validator):
    def validate_request(
        self,
        *,
        body: Optional[Dict[str, Any]] = None,
        query_string: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
    ) -> ValidationIssues:
        return ValidationIssues()

    def validate_response(
        self,
        *,
        status_code: int,
        body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> ValidationIssues:
        issues = ValidationIssues()
        if status_code != 204:
            issues.add_error(
                issue=ValidationError.bad_status_code(204, status_code),
                proceed=True,
                location=("status",),
            )
        return issues


class BulkOperations(Validator):
    def __init__(
        self, config: ServiceProviderConfig, *, resource_schemas: Sequence[ResourceSchema]
    ):
        if not config.bulk.supported:
            raise RuntimeError("bulk operations are not configured")

        super().__init__(config)
        self._validators = {
            "GET": {},
            "POST": {},
            "PUT": {},
            "PATCH": {},
            "DELETE": {},
        }
        for resource_schema in resource_schemas:
            self._validators["GET"][resource_schema.plural_name] = ResourceObjectGET(
                config, resource_schema=resource_schema
            )
            self._validators["POST"][resource_schema.plural_name] = ResourcesPOST(
                config, resource_schema=resource_schema
            )
            self._validators["PUT"][resource_schema.plural_name] = ResourceObjectPUT(
                config, resource_schema=resource_schema
            )
            self._validators["PATCH"][resource_schema.plural_name] = ResourceObjectPATCH(
                config, resource_schema=resource_schema
            )
            self._validators["DELETE"][resource_schema.plural_name] = ResourceObjectDELETE(config)

        self._request_schema = bulk_ops.BulkRequest()
        self._response_schema = bulk_ops.BulkResponse()
        self._error_validator = Error(config)

    @property
    def request_schema(self) -> bulk_ops.BulkRequest:
        return self._request_schema

    @property
    def response_schema(self) -> bulk_ops.BulkResponse:
        return self._response_schema

    def validate_request(
        self,
        *,
        body: Optional[Dict[str, Any]] = None,
        query_string: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
    ) -> ValidationIssues:
        issues = ValidationIssues()
        body_location = ("body",)
        body = SCIMDataContainer(body or {})
        issues_ = self._request_schema.validate(body)
        issues.merge(issues_, location=body_location)
        issues.merge(
            issues=AttributePresenceChecker()(body, self._request_schema.attrs, "RESPONSE"),
            location=body_location,
        )
        if not issues_.can_proceed(
            body_location + _location(self._request_schema.attrs.operations.rep)
        ):
            return issues

        path_rep = self._request_schema.attrs.operations__path.rep
        data_rep = self._request_schema.attrs.operations__data.rep
        method_rep = self._request_schema.attrs.operations__method.rep
        paths = body.get(path_rep)
        data = body.get(data_rep)
        methods = body.get(method_rep)
        for i, (path, data_item, method) in enumerate(zip(paths, data, methods)):
            path_location = body_location + (path_rep.attr, i, path_rep.sub_attr)
            data_item_location = body_location + (data_rep.attr, i, data_rep.sub_attr)
            if issues.can_proceed(
                path_location,
                data_item_location,
                (method_rep.attr, i, method_rep.sub_attr),
            ):
                if method == "DELETE":
                    continue

                if method == "POST":
                    resource_name = path.split("/", 1)[1]
                else:
                    resource_name = path.split("/", 2)[1]
                validator = self._validators[method].get(resource_name)
                if validator is None:
                    issues.add_error(
                        issue=ValidationError.unknown_resource(),
                        proceed=False,
                        location=path_location,
                    )
                    continue
                issues_ = validator.validate_request(body=data_item)
                issues.merge(issues_.get(("body",)), location=data_item_location)
        if (
            len(body.get(self._request_schema.attrs.operations.rep))
            > self.config.bulk.max_operations
        ):
            issues.add_error(
                issue=ValidationError.too_many_operations(self.config.bulk.max_operations),
                proceed=True,
                location=body_location + _location(self._response_schema.attrs.operations.rep),
            )

        return issues

    def validate_response(
        self,
        *,
        status_code: int,
        body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> ValidationIssues:
        issues = ValidationIssues()
        body = SCIMDataContainer(body or {})
        body_location = ("body",)
        issues_ = self._response_schema.validate(body)
        issues.merge(issues_, location=body_location)
        issues.merge(
            issues=AttributePresenceChecker()(body, self._response_schema.attrs, "RESPONSE"),
            location=body_location,
        )
        issues.merge(
            issues=validate_status_code(200, status_code),
            location=("status",),
        )
        if not issues.can_proceed(
            body_location + _location(self._response_schema.attrs.operations.rep)
        ):
            return issues

        operations_location = body_location + _location(self._response_schema.attrs.operations.rep)
        status_rep = self._response_schema.attrs.operations__status.rep
        response_rep = self._response_schema.attrs.operations__response.rep
        location_rep = self._response_schema.attrs.operations__location.rep
        method_rep = self._request_schema.attrs.operations__method.rep
        version_rep = self._response_schema.attrs.operations__version.rep
        statuses = body.get(status_rep)
        responses = body.get(response_rep)
        locations = body.get(location_rep)
        methods = body.get(method_rep)
        versions = body.get(version_rep)
        n_errors = 0
        for i, (method, status, response, location, version) in enumerate(
            zip(methods, statuses, responses, locations, versions)
        ):
            if not method:
                continue

            response_location = operations_location + (i, response_rep.sub_attr)
            status_location = operations_location + (i, status_rep.sub_attr)
            location_location = operations_location + (i, location_rep.sub_attr)
            version_location = operations_location + (i, version_rep.sub_attr)

            resource_validator = None
            if location:
                for resource_plural_name, resource_validator in self._validators[method].items():
                    if f"/{resource_plural_name}/" in location:
                        resource_validator = resource_validator
                        break
                else:
                    issues.add_error(
                        issue=ValidationError.unknown_resource(),
                        proceed=False,
                        location=location_location,
                    )

            if not (status and response):
                continue

            status = int(status)
            if status >= 300:
                n_errors += 1
                issues_ = self._error_validator.validate_response(
                    status_code=status,
                    body=response,
                )
                issues.merge(
                    issues=issues_.get(("body",)),
                    location=response_location,
                )
                issues.merge(
                    issues=issues_.get(("status",)),
                    location=status_location,
                )
            elif all([location, method, resource_validator]):
                issues_ = resource_validator.validate_response(
                    body=response,
                    status_code=status,
                    headers={"Location": location},
                )
                meta_location_missmatch = issues_.pop_error(("body", "meta", "location"), code=11)
                header_location_mismatch = issues_.pop_error(("headers", "Location"), code=11)
                issues.merge(issues_.get(("body",)), location=response_location)
                if meta_location_missmatch.has_errors() and header_location_mismatch.has_errors():
                    issues.add_error(
                        issue=ValidationError.must_be_equal_to("operation's location"),
                        proceed=True,
                        location=response_location + ("meta", "location"),
                    )
                    issues.add_error(
                        issue=ValidationError.must_be_equal_to("'response.meta.location'"),
                        proceed=True,
                        location=location_location,
                    )

                if response:
                    resource_version = response.get("meta.version")
                    if version and resource_version and version != resource_version:
                        issues.add_error(
                            issue=ValidationError.must_be_equal_to("operation's version"),
                            proceed=True,
                            location=response_location + ("meta", "version"),
                        )
                        issues.add_error(
                            issue=ValidationError.must_be_equal_to("'response.meta.version'"),
                            proceed=True,
                            location=version_location,
                        )

        fail_on_errors = kwargs.get("fail_on_errors")
        if fail_on_errors is not None and n_errors > fail_on_errors:
            issues.add_error(
                issue=ValidationError.too_many_errors(fail_on_errors),
                proceed=True,
                location=body_location + _location(self._response_schema.attrs.operations.rep),
            )
        return issues


class _ServiceProviderConfig(ResourcesGET):
    def __init__(
        self, config: ServiceProviderConfig, *, resource_schema: Union[Schema, ResourceType]
    ):
        super().__init__(config, resource_schema=resource_schema)

    def validate_request(
        self,
        *,
        body: Optional[Dict[str, Any]] = None,
        query_string: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
    ) -> ValidationIssues:
        issues = ValidationIssues()
        query_string = query_string or {}
        if "filter" in query_string:
            issues.add_error(
                issue=ValidationError.not_supported(),
                proceed=False,
                location=("query_string", "filter"),
            )
        return issues


class SchemasGET(_ServiceProviderConfig):
    def __init__(self, config: ServiceProviderConfig):
        super().__init__(config, resource_schema=Schema)


class ResourceTypesGET(_ServiceProviderConfig):
    def __init__(self, config: ServiceProviderConfig):
        super().__init__(config, resource_schema=ResourceType)


def _location(attr_rep: BoundedAttrRep) -> Union[Tuple[str], Tuple[str, str]]:
    if attr_rep.sub_attr:
        return attr_rep.attr, attr_rep.sub_attr
    return (attr_rep.attr,)
