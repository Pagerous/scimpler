import abc
from typing import Any, Optional, Sequence, Union, cast

from src import registry
from src.assets.schemas import bulk_ops, error, list_response, patch_op, search_request
from src.assets.schemas.resource_type import ResourceType
from src.assets.schemas.schema import Schema
from src.assets.schemas.search_request import create_search_request_schema
from src.config import ServiceProviderConfig
from src.container import AttrRep, BoundedAttrRep, Missing, SCIMDataContainer
from src.data.attr_presence import AttrPresenceConfig
from src.data.attrs import (
    Attribute,
    AttributeIssuer,
    AttributeMutability,
    AttributeReturn,
)
from src.data.filter import Filter
from src.data.schemas import BaseResourceSchema, BaseSchema, ResourceSchema
from src.data.sorter import Sorter
from src.error import ValidationError, ValidationIssues, ValidationWarning


class Validator(abc.ABC):
    def __init__(self, config: Optional[ServiceProviderConfig] = None):
        self.config = config or registry.service_provider_config

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
        body: Optional[dict[str, Any]] = None,
        query_string: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, Any]] = None,
    ) -> ValidationIssues:
        """Docs placeholder."""

    @abc.abstractmethod
    def validate_response(
        self,
        *,
        status_code: int,
        body: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, Any]] = None,
        **kwargs,
    ) -> ValidationIssues:
        """Docs placeholder."""


class Error(Validator):
    def __init__(self, config: Optional[ServiceProviderConfig] = None):
        super().__init__(config)
        self._schema = error.Error

    @property
    def response_schema(self) -> error.ErrorSchema:
        return self._schema

    def validate_request(
        self,
        *,
        body: Optional[dict[str, Any]] = None,
        query_string: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, Any]] = None,
    ) -> ValidationIssues:
        raise NotImplementedError

    def validate_response(
        self,
        *,
        status_code: int,
        body: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, Any]] = None,
        **kwargs,
    ) -> ValidationIssues:
        body_location = ("body",)
        issues = ValidationIssues()
        normalized = SCIMDataContainer(body or {})
        issues.merge(
            self.response_schema.validate(normalized, AttrPresenceConfig("RESPONSE")),
            location=body_location,
        )
        status_attr_rep = self.response_schema.attrs.status
        status_location = body_location + status_attr_rep.location
        if (status_in_body := normalized.get(status_attr_rep)) and str(
            status_code
        ) != status_in_body:
            issues.add_error(
                issue=ValidationError.must_be_equal_to("response status code"),
                location=status_location,
                proceed=True,
            )
            issues.add_error(
                issue=ValidationError.must_be_equal_to("'status' attribute"),
                location=["status"],
                proceed=True,
            )
        if not 200 <= status_code < 600:
            issues.add_error(
                issue=ValidationError.bad_value_content(),
                location=["status"],
                proceed=True,
            )
        return issues


def _validate_resource_location_consistency(
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


def _validate_status_code(expected: int, actual: int) -> ValidationIssues:
    issues = ValidationIssues()
    if expected != actual:
        issues.add_error(
            issue=ValidationError.bad_status_code(expected),
            proceed=True,
        )
    return issues


def _validate_resource_output_body(
    schema: BaseResourceSchema,
    config: ServiceProviderConfig,
    location_header_required: bool,
    expected_status_code: int,
    status_code: int,
    body: SCIMDataContainer,
    headers: dict[str, Any],
    presence_config: Optional[AttrPresenceConfig],
) -> ValidationIssues:
    issues = ValidationIssues()
    body_location = ("body",)
    issues.merge(
        schema.validate(
            data=body,
            presence_config=presence_config or AttrPresenceConfig("RESPONSE"),
        ),
        location=body_location,
    )

    if "Location" not in headers and location_header_required:
        issues.add_error(
            issue=ValidationError.missing(),
            proceed=False,
            location=("headers", "Location"),
        )
    issues.merge(
        issues=_validate_status_code(expected_status_code, status_code),
        location=["status"],
    )
    meta_rep = schema.attrs.meta__location
    location_header = headers.get("Location")
    if (
        issues.can_proceed(body_location + meta_rep.location, ("headers", "Location"))
        and location_header is not None
    ):
        issues.merge(
            issues=_validate_resource_location_consistency(
                meta_location=body.get(meta_rep),
                headers_location=location_header,
            ),
        )

    etag = headers.get("ETag")
    version_rep = schema.attrs.meta__version
    version = body.get(version_rep)
    if all([etag, version]) and etag != version:
        issues.add_error(
            issue=ValidationError.must_be_equal_to("'ETag' header"),
            proceed=True,
            location=body_location + version_rep.location,
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
                location=body_location + version_rep.location,
            )
    return issues


class ResourceObjectGET(Validator):
    def __init__(
        self, config: Optional[ServiceProviderConfig] = None, *, resource_schema: BaseResourceSchema
    ):
        super().__init__(config)
        self._schema = resource_schema
        self._response_schema = resource_schema.clone(_resource_output_filter)

    @property
    def response_schema(self) -> BaseResourceSchema:
        return self._response_schema

    def validate_request(
        self,
        *,
        body: Optional[dict[str, Any]] = None,
        query_string: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, Any]] = None,
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
        body: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, Any]] = None,
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
            presence_config=kwargs.get("presence_config"),
        )


class ServiceResourceObjectGET(ResourceObjectGET):
    def validate_request(
        self,
        *,
        body: Optional[dict[str, Any]] = None,
        query_string: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, Any]] = None,
    ) -> ValidationIssues:
        return ValidationIssues()


class ResourceObjectPUT(Validator):
    def __init__(
        self, config: Optional[ServiceProviderConfig] = None, *, resource_schema: ResourceSchema
    ):
        super().__init__(config)
        self._request_schema = resource_schema.clone(
            lambda attr: attr.mutability != AttributeMutability.READ_ONLY or attr.required
        )
        self._response_schema = resource_schema.clone(_resource_output_filter)
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
        body: Optional[dict[str, Any]] = None,
        query_string: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, Any]] = None,
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
            location=["query_string"],
        )
        issues.merge(
            issues=self._schema.validate(
                data=body or {},
                presence_config=AttrPresenceConfig(
                    "REQUEST",
                    ignore_issuer=[
                        attr_rep for attr_rep, attr in self._schema.attrs if attr.required
                    ],
                ),
            ),
            location=["body"],
        )
        return issues

    def validate_response(
        self,
        *,
        status_code: int,
        body: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, Any]] = None,
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
            presence_config=kwargs.get("presence_config"),
        )


class ResourcesPOST(Validator):
    def __init__(
        self, config: Optional[ServiceProviderConfig] = None, *, resource_schema: ResourceSchema
    ):
        super().__init__(config)
        self._schema = resource_schema
        self._request_schema = resource_schema.clone(
            lambda attr: (
                (
                    attr.mutability != AttributeMutability.READ_ONLY
                    and attr.issuer != AttributeIssuer.SERVER
                )
                or attr.name == "schemas"
            )
        )
        self._response_schema = resource_schema.clone(_resource_output_filter)

    @property
    def request_schema(self) -> ResourceSchema:
        return self._request_schema

    @property
    def response_schema(self) -> ResourceSchema:
        return self._response_schema

    def validate_request(
        self,
        *,
        body: Optional[dict[str, Any]] = None,
        query_string: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, Any]] = None,
    ) -> ValidationIssues:
        issues = ValidationIssues()
        normalized, query_string = SCIMDataContainer(body or {}), query_string or {}
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
            issues=self._schema.validate(normalized, AttrPresenceConfig("REQUEST")),
            location=("body",),
        )
        return issues

    def validate_response(
        self,
        *,
        status_code: int,
        body: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, Any]] = None,
        **kwargs,
    ) -> ValidationIssues:
        issues = ValidationIssues()
        if not body:
            issues.add_warning(issue=ValidationWarning.missing(), location=["body"])
            return issues

        normalized = SCIMDataContainer(body)
        issues = _validate_resource_output_body(
            schema=self._schema,
            config=self.config,
            location_header_required=True,
            expected_status_code=201,
            status_code=status_code,
            body=normalized,
            headers=headers or {},
            presence_config=kwargs.get("presence_config"),
        )
        if normalized.get(self._schema.attrs.meta__created) != normalized.get(
            self._schema.attrs.meta__lastModified
        ):
            issues.add_error(
                issue=ValidationError.must_be_equal_to("'meta.created'"),
                proceed=True,
                location=("body", *self._schema.attrs.meta__lastModified.location),
            )
        return issues


def _validate_resources_sorted(
    sorter: Sorter,
    resources: list[SCIMDataContainer],
    resource_schemas: Sequence[BaseResourceSchema],
) -> ValidationIssues:
    issues = ValidationIssues()
    if resources != sorter(resources, resource_schemas):
        issues.add_error(
            issue=ValidationError.resources_not_sorted(),
            proceed=True,
        )
    return issues


def _validate_number_of_resources(
    count: Optional[int],
    total_results: int,
    resources: list[Any],
) -> ValidationIssues:
    issues = ValidationIssues()
    n_resources = len(resources)
    if total_results < n_resources:
        issues.add_error(
            issue=ValidationError.bad_number_of_resources(
                "must not be greater than 'totalResults'"
            ),
            proceed=True,
        )
    elif count is None and total_results > n_resources:
        issues.add_error(
            issue=ValidationError.bad_number_of_resources("must be equal to 'totalResults'"),
            proceed=True,
        )
    if count is not None and count < n_resources:
        issues.add_error(
            issue=ValidationError.bad_number_of_resources(
                "must be lesser or equal to 'count' parameter"
            ),
            proceed=True,
        )
    return issues


def _validate_pagination_info(
    schema: list_response.ListResponse,
    count: Optional[int],
    total_results: Any,
    resources: list[Any],
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
                location=schema.attrs.startindex.location,
                proceed=False,
            )
        if items_per_page in [None, Missing]:
            issues.add_error(
                issue=ValidationError.missing(),
                location=schema.attrs.itemsperpage.location,
                proceed=False,
            )
    return issues


def _validate_resources_filtered(
    filter_: Filter,
    resources: list[Any],
    resource_schemas: Sequence[BaseResourceSchema],
) -> ValidationIssues:
    issues = ValidationIssues()
    for i, (resource, schema) in enumerate(zip(resources, resource_schemas)):
        if not filter_(resource, schema):
            issues.add_error(
                issue=ValidationError.resources_not_filtered(),
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
    resource_presence_config: Optional[AttrPresenceConfig] = None,
) -> ValidationIssues:
    issues = ValidationIssues()
    body_location = ("body",)
    resources_location = body_location + schema.attrs.resources.location

    start_index_rep = schema.attrs.startindex
    start_index_location = body_location + start_index_rep.location

    resource_presence_config = resource_presence_config or AttrPresenceConfig("RESPONSE")
    issues_ = schema.validate(
        data=body,
        presence_config=AttrPresenceConfig("RESPONSE"),
        resource_presence_config=resource_presence_config,
    )
    issues.merge(issues_, location=body_location)
    issues.merge(
        issues=_validate_status_code(200, status_code),
        location=("status",),
    )
    if issues.can_proceed(start_index_location):
        start_index_body = body.get(start_index_rep)
        if start_index_body and start_index_body > start_index:
            issues.add_error(
                issue=ValidationError.bad_value_content(),
                proceed=True,
                location=start_index_location,
            )

    if not issues.can_proceed(resources_location):
        return issues

    total_results_rep = schema.attrs.totalresults
    total_results_location = body_location + total_results_rep.location

    items_per_page_rep = schema.attrs.itemsperpage
    items_per_page_location = body_location + items_per_page_rep.location

    resources = body.get(schema.attrs.resources)
    if resources is Missing:
        resources = []

    if issues.can_proceed(total_results_location):
        total_results = body.get(total_results_rep)
        issues.merge(
            issues=_validate_number_of_resources(
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
                issues=_validate_pagination_info(
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

    resource_schemas = cast(Sequence[BaseResourceSchema], schema.get_schemas(resources))
    if filter_ is not None and can_validate_filtering(filter_, resource_presence_config):
        issues.merge(
            issues=_validate_resources_filtered(filter_, resources, resource_schemas),
            location=resources_location,
        )
    if sorter is not None and can_validate_sorting(sorter, resource_presence_config):
        issues.merge(
            issues=_validate_resources_sorted(sorter, resources, resource_schemas),
            location=resources_location,
        )
    return issues


def _is_contained(attr_rep: AttrRep, attr_reps: list[AttrRep]) -> bool:
    return attr_rep in attr_reps


def _is_parent_contained(attr_rep, attr_reps) -> bool:
    return bool(
        attr_rep.is_sub_attr
        and (
            (
                BoundedAttrRep(schema=attr_rep.schema, attr=attr_rep.attr)
                if isinstance(attr_rep, BoundedAttrRep)
                else AttrRep(attr=attr_rep.attr)
            )
            in attr_reps
        )
    )


def _is_child_contained(attr_rep: AttrRep, attr_reps: list[AttrRep]) -> bool:
    for rep in attr_reps:
        if not rep.is_sub_attr:
            continue

        if isinstance(attr_rep, BoundedAttrRep) and isinstance(rep, BoundedAttrRep):
            if attr_rep.schema == rep.schema and attr_rep.attr == rep.attr:
                return True
            return False
        return True

    return False


def can_validate_filtering(filter_: Filter, presence_config: AttrPresenceConfig) -> bool:
    if presence_config.include is None:
        return True

    filter_attr_reps = filter_.attr_reps
    if presence_config.include:
        for attr_rep in filter_attr_reps:
            if not (
                _is_contained(attr_rep, presence_config.attr_reps)
                or _is_parent_contained(attr_rep, presence_config.attr_reps)
                or _is_child_contained(attr_rep, presence_config.attr_reps)
            ):
                return False
        return True

    for attr_rep in presence_config.attr_reps:
        if _is_contained(attr_rep, filter_attr_reps) or _is_child_contained(
            attr_rep, filter_attr_reps
        ):
            return False
    return True


def can_validate_sorting(sorter: Sorter, presence_config: AttrPresenceConfig) -> bool:
    if not presence_config.attr_reps:
        return True

    is_contained = _is_contained(
        sorter.attr_rep, presence_config.attr_reps
    ) or _is_parent_contained(sorter.attr_rep, presence_config.attr_reps)
    if presence_config.include and not is_contained or not presence_config.include and is_contained:
        return False
    return True


class ServerRootResourcesGET(Validator):
    def __init__(
        self,
        config: Optional[ServiceProviderConfig] = None,
        *,
        resource_schemas: Sequence[BaseResourceSchema],
    ):
        super().__init__(config)
        self._request_query_validation_schema = create_search_request_schema(self.config)
        self._response_validation_schema = list_response.ListResponse(resource_schemas)
        self._response_schema = list_response.ListResponse(
            [resource_schema.clone(_resource_output_filter) for resource_schema in resource_schemas]
        )

    @property
    def response_schema(self) -> list_response.ListResponse:
        return self._response_schema

    def validate_request(
        self,
        *,
        body: Optional[dict[str, Any]] = None,
        query_string: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, Any]] = None,
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
        body: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, Any]] = None,
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
            resource_presence_config=kwargs.get("presence_config"),
        )


class ResourcesGET(ServerRootResourcesGET):
    def __init__(
        self, config: Optional[ServiceProviderConfig] = None, *, resource_schema: BaseResourceSchema
    ):
        super().__init__(config, resource_schemas=[resource_schema])


class SearchRequestPOST(Validator):
    def __init__(
        self,
        config: Optional[ServiceProviderConfig] = None,
        *,
        resource_schemas: Sequence[ResourceSchema],
    ):
        super().__init__(config)
        self._request_validation_schema = create_search_request_schema(config)
        self._response_validation_schema = list_response.ListResponse(resource_schemas)
        self._response_schema = list_response.ListResponse(
            [resource_schema.clone(_resource_output_filter) for resource_schema in resource_schemas]
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
        body: Optional[dict[str, Any]] = None,
        query_string: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, Any]] = None,
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
        body: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, Any]] = None,
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
            resource_presence_config=kwargs.get("presence_config"),
        )


class ResourceObjectPATCH(Validator):
    def __init__(
        self, config: Optional[ServiceProviderConfig] = None, *, resource_schema: ResourceSchema
    ):
        super().__init__(config)
        if not self.config.patch.supported:
            raise RuntimeError("patch operation is not configured")
        self._schema = patch_op.PatchOp(resource_schema)
        self._request_schema = patch_op.PatchOp(
            resource_schema.clone(lambda attr: attr.mutability != AttributeMutability.READ_ONLY)
        )
        self._resource_schema = resource_schema
        self._response_schema = resource_schema.clone(_resource_output_filter)

    @property
    def request_schema(self) -> patch_op.PatchOp:
        return self._request_schema

    @property
    def response_schema(self) -> ResourceSchema:
        return self._response_schema

    def validate_request(
        self,
        *,
        body: Optional[dict[str, Any]] = None,
        query_string: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, Any]] = None,
    ) -> ValidationIssues:
        issues = ValidationIssues()
        normalized, query_string = SCIMDataContainer(body or {}), query_string or {}
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
            self._schema.validate(normalized, AttrPresenceConfig("REQUEST")),
            location=["body"],
        )
        return issues

    def validate_response(
        self,
        *,
        status_code: int,
        body: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, Any]] = None,
        **kwargs,
    ) -> ValidationIssues:
        issues = ValidationIssues()
        presence_config = kwargs.get("presence_config")
        if status_code == 204:
            if presence_config is not None and presence_config.attr_reps:
                issues.add_error(
                    issue=ValidationError.bad_status_code(200),
                    proceed=True,
                    location=("status",),
                )
            return issues
        normalized = SCIMDataContainer(body or {})
        issues = _validate_resource_output_body(
            schema=self._resource_schema,
            config=self.config,
            location_header_required=False,
            expected_status_code=200,
            status_code=status_code,
            body=normalized,
            headers=headers or {},
            presence_config=presence_config,
        )
        meta_version_rep = self.response_schema.attrs.meta__version
        if normalized.get(meta_version_rep) is Missing:
            issues.pop_errors([5, 8], ("body", *meta_version_rep.location))
            issues.pop_errors([8], ("headers", "ETag"))
        return issues


class ResourceObjectDELETE(Validator):
    def validate_request(
        self,
        *,
        body: Optional[dict[str, Any]] = None,
        query_string: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, Any]] = None,
    ) -> ValidationIssues:
        return ValidationIssues()

    def validate_response(
        self,
        *,
        status_code: int,
        body: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, Any]] = None,
        **kwargs,
    ) -> ValidationIssues:
        issues = ValidationIssues()
        if status_code != 204:
            issues.add_error(
                issue=ValidationError.bad_status_code(204),
                proceed=True,
                location=("status",),
            )
        return issues


class BulkOperations(Validator):
    def __init__(
        self,
        config: Optional[ServiceProviderConfig] = None,
        *,
        resource_schemas: Sequence[ResourceSchema],
    ):
        super().__init__(config)
        if not self.config.bulk.supported:
            raise RuntimeError("bulk operations are not configured")
        self._validators: dict[str, dict[str, Validator]] = {
            "GET": {},
            "POST": {},
            "PUT": {},
            "PATCH": {},
            "DELETE": {},
        }
        for resource_schema in resource_schemas:
            self._validators["GET"][resource_schema.plural_name] = ResourceObjectGET(
                self.config, resource_schema=resource_schema
            )
            self._validators["POST"][resource_schema.plural_name] = ResourcesPOST(
                self.config, resource_schema=resource_schema
            )
            self._validators["PUT"][resource_schema.plural_name] = ResourceObjectPUT(
                self.config, resource_schema=resource_schema
            )
            self._validators["PATCH"][resource_schema.plural_name] = ResourceObjectPATCH(
                self.config, resource_schema=resource_schema
            )
            self._validators["DELETE"][resource_schema.plural_name] = ResourceObjectDELETE(
                self.config
            )

        self._request_schema = bulk_ops.BulkRequest()
        self._response_schema = bulk_ops.BulkResponse()
        self._error_validator = Error(self.config)

    @property
    def error_validator(self) -> Error:
        return self._error_validator

    @property
    def sub_validators(self) -> dict[str, dict[str, Validator]]:
        return self._validators

    @property
    def request_schema(self) -> bulk_ops.BulkRequest:
        return self._request_schema

    @property
    def response_schema(self) -> bulk_ops.BulkResponse:
        return self._response_schema

    def validate_request(
        self,
        *,
        body: Optional[dict[str, Any]] = None,
        query_string: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, Any]] = None,
    ) -> ValidationIssues:
        issues = ValidationIssues()
        body_location = ("body",)
        normalized = SCIMDataContainer(body or {})
        issues.merge(
            self._request_schema.validate(normalized, AttrPresenceConfig("REQUEST")),
            location=body_location,
        )
        if not issues.can_proceed(body_location + self._request_schema.attrs.operations.location):
            return issues

        path_rep = self._request_schema.attrs.operations__path
        data_rep = self._request_schema.attrs.operations__data
        method_rep = self._request_schema.attrs.operations__method
        paths = normalized.get(path_rep)
        data = normalized.get(data_rep)
        methods = normalized.get(method_rep)
        for i, (path, data_item, method) in enumerate(zip(paths, data, methods)):
            path_location = body_location + (path_rep.attr, i, path_rep.sub_attr)
            data_item_location = body_location + (data_rep.attr, i, data_rep.sub_attr)
            method_location = body_location + (method_rep.attr, i, method_rep.sub_attr)
            if issues.can_proceed(path_location, method_location):
                if method == "DELETE":
                    continue

                if method == "POST":
                    resource_name = path.split("/", 1)[1]
                else:
                    resource_name = path.split("/", 2)[1]
                validator = self._validators[method].get(resource_name)
                if validator is None:
                    issues.add_error(
                        issue=ValidationError.unknown_operation_resource(),
                        proceed=False,
                        location=path_location,
                    )
                    continue
                issues_ = validator.validate_request(body=data_item)
                issues.merge(issues_.get(location=["body"]), location=data_item_location)
        if (
            isinstance(self.config.bulk.max_operations, int)
            and len(normalized.get(self._request_schema.attrs.operations))
            > self.config.bulk.max_operations
        ):
            issues.add_error(
                issue=ValidationError.too_many_bulk_operations(self.config.bulk.max_operations),
                proceed=True,
                location=body_location + self._response_schema.attrs.operations.location,
            )

        return issues

    def validate_response(
        self,
        *,
        status_code: int,
        body: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, Any]] = None,
        **kwargs,
    ) -> ValidationIssues:
        issues = ValidationIssues()
        normalized = SCIMDataContainer(body or {})
        body_location = ("body",)
        issues.merge(
            self._response_schema.validate(normalized, AttrPresenceConfig("RESPONSE")),
            location=body_location,
        )
        issues.merge(
            issues=_validate_status_code(200, status_code),
            location=["status"],
        )
        operations_location = body_location + self._response_schema.attrs.operations.location
        if not issues.can_proceed(operations_location):
            return issues

        status_rep = self._response_schema.attrs.operations__status
        response_rep = self._response_schema.attrs.operations__response
        location_rep = self._response_schema.attrs.operations__location
        method_rep = self._request_schema.attrs.operations__method
        version_rep = self._response_schema.attrs.operations__version
        statuses = normalized.get(status_rep)
        responses = normalized.get(response_rep)
        locations = normalized.get(location_rep)
        methods = normalized.get(method_rep)
        versions = normalized.get(version_rep)
        n_errors = 0
        for i, (method, status, response, location, version) in enumerate(
            zip(methods, statuses, responses, locations, versions)
        ):
            if not method:
                continue

            response_location: tuple[Union[str, int], ...] = (
                *operations_location,
                i,
                response_rep.sub_attr,
            )
            status_location: tuple[Union[str, int], ...] = (
                *operations_location,
                i,
                status_rep.sub_attr,
            )
            location_location: tuple[Union[str, int], ...] = (
                *operations_location,
                i,
                location_rep.sub_attr,
            )
            version_location: tuple[Union[str, int], ...] = (
                *operations_location,
                i,
                version_rep.sub_attr,
            )

            resource_validator = None
            if location:
                for resource_plural_name, validator in self._validators[method].items():
                    if f"/{resource_plural_name}/" in location:
                        resource_validator = validator
                        break
                else:
                    issues.add_error(
                        issue=ValidationError.unknown_operation_resource(),
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
                    issues=issues_.get(location=["body"]),
                    location=response_location,
                )
                issues.merge(
                    issues=issues_.get(location=["status"]),
                    location=status_location,
                )
            elif location and isinstance(resource_validator, Validator):
                resource_version = response.get("meta.version")
                issues_ = resource_validator.validate_response(
                    body=response,
                    status_code=status,
                    headers={"Location": location, "ETag": resource_version},
                )
                meta_location_missmatch = issues_.pop_errors([8], ("body", "meta", "location"))
                header_location_mismatch = issues_.pop_errors([8], ("headers", "Location"))
                issues.merge(issues_.get(location=["body"]), location=response_location)
                issues.merge(issues_.get(location=["status"]), location=status_location)
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
                issue=ValidationError.too_many_errors_in_bulk(fail_on_errors),
                proceed=True,
                location=operations_location,
            )
        return issues


class _ServiceProviderConfig(ResourcesGET):
    def __init__(
        self,
        config: Optional[ServiceProviderConfig] = None,
        *,
        resource_schema: BaseResourceSchema,
    ):
        super().__init__(config, resource_schema=resource_schema)

    def validate_request(
        self,
        *,
        body: Optional[dict[str, Any]] = None,
        query_string: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, Any]] = None,
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
    def __init__(self, config: Optional[ServiceProviderConfig] = None):
        super().__init__(config, resource_schema=Schema)


class ResourceTypesGET(_ServiceProviderConfig):
    def __init__(self, config: Optional[ServiceProviderConfig] = None):
        super().__init__(config, resource_schema=ResourceType)


def _resource_output_filter(attr: Attribute) -> bool:
    return bool(
        attr.returned != AttributeReturn.NEVER and attr.mutability != AttributeMutability.WRITE_ONLY
    )
