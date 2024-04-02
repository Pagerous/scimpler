import abc
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from src.assets.config import ServiceProviderConfig
from src.assets.schemas import bulk_ops, error, list_response, patch_op, search_request
from src.assets.schemas.resource_type import ResourceType
from src.assets.schemas.schema import Schema
from src.attributes_presence import AttributePresenceChecker
from src.data.attributes import (
    Attribute,
    AttributeIssuer,
    AttributeMutability,
    ComplexAttribute,
)
from src.data.container import AttrRep, Invalid, Missing, SCIMDataContainer
from src.data.schemas import BaseSchema, ResourceSchema
from src.data.type import get_scim_type
from src.error import ValidationError, ValidationIssues
from src.filter import Filter
from src.sorter import Sorter


@dataclass
class RequestData:
    body: Optional[SCIMDataContainer]
    options: Dict[str, Any]


@dataclass
class ResponseData:
    body: Optional[Dict[str, Any]]


class Validator(abc.ABC):
    def __init__(self, config: ServiceProviderConfig):
        self._config = config

    @property
    def config(self) -> ServiceProviderConfig:
        return self._config

    @property
    def request_schema(self) -> Union[BaseSchema, NotImplemented]:
        return NotImplemented

    @property
    def response_schema(self) -> Union[BaseSchema, NotImplemented]:
        return NotImplemented

    @abc.abstractmethod
    def parse_request(
        self, *, body: Any = None, query_string: Any = None
    ) -> Tuple[RequestData, ValidationIssues]:
        ...

    @abc.abstractmethod
    def dump_response(
        self,
        *,
        status_code: int,
        body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Tuple[ResponseData, ValidationIssues]:
        ...


class Error(Validator):
    def __init__(self, config: ServiceProviderConfig):
        super().__init__(config)
        self._schema = error.Error()

    @property
    def response_schema(self) -> error.Error:
        return self._schema

    def parse_request(self, *, body: Any = None, query_string: Any = None) -> RequestData:
        raise NotImplementedError

    def dump_response(
        self,
        *,
        status_code: int,
        body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Tuple[ResponseData, ValidationIssues]:
        body_location = ("body",)
        issues = ValidationIssues()
        body, issues_ = self._schema.dump(body)
        issues.merge(issues_, location=body_location)
        if issues.can_proceed(body_location):
            issues.merge(
                issues=AttributePresenceChecker()(body, self._schema.attrs, "RESPONSE"),
                location=body_location,
            )
        status_attr_rep = self._schema.attrs.status.rep
        if issues.can_proceed(body_location + _location(status_attr_rep)):
            issues.merge(
                validate_error_status_code_consistency(
                    status_code_attr_name=status_attr_rep.attr,
                    status_code_body=body[status_attr_rep],
                    status_code=status_code,
                )
            )
        issues.merge(validate_error_status_code(status_code))
        body = body.to_dict() if not issues.has_issues() else None
        return ResponseData(body=body), issues


def validate_error_status_code_consistency(
    status_code_attr_name: str,
    status_code_body: str,
    status_code: int,
) -> ValidationIssues:
    issues = ValidationIssues()
    if str(status_code) != status_code_body:
        issues.add(
            issue=ValidationError.error_status_mismatch(str(status_code), status_code_body),
            location=("body", status_code_attr_name),
            proceed=True,
        )
        issues.add(
            issue=ValidationError.error_status_mismatch(str(status_code), status_code_body),
            location=("status",),
            proceed=True,
        )
    return issues


def validate_error_status_code(status_code: int) -> ValidationIssues:
    issues = ValidationIssues()
    if not 200 <= status_code < 600:
        issues.add(
            issue=ValidationError.bad_error_status(status_code),
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
            issues.add(
                issue=ValidationError.missing_required_header("Location"),
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
        issues.add(
            issue=ValidationError.must_be_equal_to("'Location' header"),
            location=("body", "meta", "location"),
            proceed=True,
        )
        issues.add(
            issue=ValidationError.must_be_equal_to("'meta.location'"),
            location=("headers", "Location"),
            proceed=True,
        )
    return issues


def validate_status_code(expected: int, actual: int) -> ValidationIssues:
    issues = ValidationIssues()
    if expected != actual:
        issues.add(
            issue=ValidationError.bad_status_code(expected, actual),
            proceed=True,
        )
    return issues


def _parse_body(
    schema: BaseSchema,
    body: Any,
    required_attrs_to_ignore: Optional[Sequence[AttrRep]] = None,
) -> Tuple[Union[Invalid, SCIMDataContainer], ValidationIssues]:
    issues = ValidationIssues()
    body_location = ("body",)
    body, issues_ = schema.parse(body)
    issues.merge(issues_, location=body_location)
    if issues.can_proceed(body_location):
        issues.merge(
            issues=AttributePresenceChecker(ignore_required=required_attrs_to_ignore)(
                body, schema.attrs, "REQUEST"
            ),
            location=body_location,
        )
    return body, issues


def _dump_resource_output_body(
    schema: ResourceSchema,
    location_header_required: bool,
    expected_status_code: int,
    status_code: int,
    body: Any = None,
    headers: Any = None,
    presence_checker: Optional[AttributePresenceChecker] = None,
) -> Tuple[ResponseData, ValidationIssues]:
    issues = ValidationIssues()
    headers = headers or {}
    body_location = ("body",)
    body, issues_ = schema.dump(body)
    issues.merge(issues_, location=body_location)

    issues.merge(
        issues=validate_resource_location_in_header(headers, location_header_required),
        location=("headers",),
    )
    issues.merge(
        issues=validate_status_code(expected_status_code, status_code),
        location=("status",),
    )
    if issues.can_proceed(body_location):
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
                meta_location=body[meta_location],
                headers_location=location_header,
            ),
        )

    body = body.to_dict() if not issues.has_issues() else None
    return ResponseData(body=body), issues


class ResourceObjectGET(Validator):
    def __init__(self, config: ServiceProviderConfig, *, resource_schema: ResourceSchema):
        super().__init__(config)
        self._schema = resource_schema

    @property
    def response_schema(self) -> ResourceSchema:
        return self._schema

    def parse_request(
        self, *, body: Any = None, query_string: Any = None
    ) -> Tuple[RequestData, ValidationIssues]:
        issues, options = ValidationIssues(), {}
        if isinstance(query_string, Dict):
            checker, issues_ = parse_requested_attributes(query_string)
            issues.merge(issues=issues_, location=("query_string",))
            if checker:
                options["presence_checker"] = checker
        return RequestData(body=body, options=options), issues

    def dump_response(
        self,
        *,
        status_code: int,
        body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Tuple[ResponseData, ValidationIssues]:
        return _dump_resource_output_body(
            schema=self._schema,
            location_header_required=False,
            expected_status_code=200,
            status_code=status_code,
            body=body,
            headers=headers,
            presence_checker=kwargs.get("presence_checker"),
        )


class ResourceObjectPUT(Validator):
    def __init__(self, config: ServiceProviderConfig, *, resource_schema: ResourceSchema):
        super().__init__(config)
        self._schema = resource_schema

    @property
    def request_schema(self) -> ResourceSchema:
        return self._schema

    @property
    def response_schema(self) -> ResourceSchema:
        return self._schema

    def parse_request(
        self, *, body: Any = None, query_string: Any = None
    ) -> Tuple[RequestData, ValidationIssues]:
        issues, options = ValidationIssues(), {}
        if isinstance(query_string, Dict):
            checker, issues_ = parse_requested_attributes(query_string)
            issues.merge(issues=issues_, location=("query_string",))
            if checker:
                options["presence_checker"] = checker

        body, issues_ = _parse_body(schema=self._schema, body=body)
        issues.merge(issues=issues_)

        if issues.has_issues():
            body = None
        else:
            for attr in self._schema.attrs:
                if attr.mutability == AttributeMutability.READ_ONLY:
                    del body[attr.rep]

        return RequestData(body=body, options=options), issues

    def dump_response(
        self,
        *,
        status_code: int,
        body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Tuple[ResponseData, ValidationIssues]:
        return _dump_resource_output_body(
            schema=self._schema,
            location_header_required=False,
            expected_status_code=200,
            status_code=status_code,
            body=body,
            headers=headers,
            presence_checker=kwargs.get("presence_checker"),
        )


class ResourcesPOST(Validator):
    def __init__(self, config: ServiceProviderConfig, *, resource_schema: ResourceSchema):
        super().__init__(config)
        self._schema = resource_schema

    @property
    def request_schema(self) -> ResourceSchema:
        return self._schema

    @property
    def response_schema(self) -> ResourceSchema:
        return self._schema

    def parse_request(
        self, *, body: Any = None, query_string: Any = None
    ) -> Tuple[RequestData, ValidationIssues]:
        issues, options = ValidationIssues(), {}
        if isinstance(query_string, Dict):
            checker, issues_ = parse_requested_attributes(query_string)
            issues.merge(issues=issues_, location=("query_string",))
            if checker:
                options["presence_checker"] = checker

        required_to_ignore = []
        for attr in self._schema.attrs:
            if attr.required and attr.issuer == AttributeIssuer.SERVER:
                required_to_ignore.append(attr.rep)

        body, issues_ = _parse_body(self._schema, body, required_to_ignore)
        issues.merge(issues=issues_)
        if issues.has_issues():
            body = None
        return RequestData(body=body, options=options), issues

    def dump_response(
        self,
        *,
        status_code: int,
        body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Tuple[ResponseData, ValidationIssues]:
        issues = ValidationIssues()
        if not body:
            return ResponseData(body=None), issues  # TODO: warn missing body

        return _dump_resource_output_body(
            schema=self._schema,
            location_header_required=True,
            expected_status_code=201,
            status_code=status_code,
            body=body,
            headers=headers,
            presence_checker=kwargs.get("presence_checker"),
        )


def parse_request_sorting(query_string: Dict) -> Tuple[Union[Invalid, Sorter], ValidationIssues]:
    issues = ValidationIssues()

    sort_by = query_string.get("sortBy")
    if not isinstance(sort_by, str):
        if sort_by is not None:
            issues.add(
                issue=ValidationError.bad_type(get_scim_type(str), get_scim_type(type(sort_by))),
                proceed=False,
            )
        return Invalid, issues

    sort_order = query_string.get("sortOrder", "ascending")
    if sort_order not in ["ascending", "descending"]:
        pass  # TODO add warning here

    return Sorter.parse(by=sort_by, asc=sort_order == "ascending")


def parse_request_filtering(query_string: Dict) -> Tuple[Union[Invalid, Filter], ValidationIssues]:
    issues = ValidationIssues()
    filter_exp = query_string.get("filter")
    if not isinstance(filter_exp, str):
        if filter_exp is not None:
            issues.add(
                issue=ValidationError.bad_type(get_scim_type(str), get_scim_type(type(filter_exp))),
                proceed=False,
            )
        return Invalid, issues
    return Filter.parse(filter_exp)


def parse_requested_attributes(
    query_string: Dict[str, Any],
) -> Tuple[Union[None, Invalid, AttributePresenceChecker], ValidationIssues]:
    issues = ValidationIssues()
    to_include = query_string.get("attributes", [])
    if to_include and isinstance(to_include, str):
        to_include = to_include.split(",")
    to_exclude = query_string.get("excludeAttributes", [])
    if to_exclude and isinstance(to_exclude, str):
        to_exclude = to_exclude.split(",")

    if not (isinstance(to_include, List) and isinstance(to_exclude, List)):
        return Invalid, issues

    if not (to_include or to_exclude):
        return None, issues

    if to_include and to_exclude:
        issues.add(
            issue=ValidationError.can_not_be_used_together("excludeAttributes"),
            proceed=False,
            location=("attributes",),
        )
        issues.add(
            issue=ValidationError.can_not_be_used_together("attributes"),
            proceed=False,
            location=("excludeAttributes",),
        )
        return Invalid, issues

    attr_reps = to_include or to_exclude
    include = None if not any([to_include, to_exclude]) else bool(to_include)
    checker, issues_ = AttributePresenceChecker.parse(attr_reps, include)
    issues.merge(issues=issues_, location=("attributes" if include else "excludeAttributes",))
    return checker, issues


def validate_resources_sorted(
    sorter: Sorter,
    resources: List[Any],
    resource_schemas: Sequence[ResourceSchema],
) -> ValidationIssues:
    issues = ValidationIssues()
    if resources != sorter(resources, schema=resource_schemas):
        issues.add(
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
        issues.add(
            issue=ValidationError.total_results_mismatch(
                total_results=total_results, n_resources=n_resources
            ),
            proceed=True,
        )
    if count is None and total_results > n_resources:
        issues.add(
            issue=ValidationError.too_little_results(must="be equal to 'totalResults'"),
            proceed=True,
        )
    if count is not None and count < n_resources:
        issues.add(
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
            issues.add(
                issue=ValidationError.missing(),
                location=_location(schema.attrs.startindex.rep),
                proceed=False,
            )
        if items_per_page in [None, Missing]:
            issues.add(
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
        issues.add(
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
    resources: List[Any], filter_: Filter, resource_schemas: Sequence[ResourceSchema], strict: bool
) -> ValidationIssues:
    issues = ValidationIssues()
    for i, (resource, schema) in enumerate(zip(resources, resource_schemas)):
        if not filter_(resource, schema, strict):
            issues.add(
                issue=ValidationError.included_resource_does_not_match_filter(),
                proceed=True,
                location=(i,),
            )
    return issues


def _parse_resources_get_request(
    body: Any = None, query_string: Any = None
) -> Tuple[RequestData, ValidationIssues]:
    issues = ValidationIssues()
    options = {}
    query_string_location = ("query_string",)
    if query_string is None:
        issues.add(
            issue=ValidationError.missing(),
            proceed=False,
            location=query_string_location,
        )
    elif not isinstance(query_string, Dict):
        issues.add(
            issue=ValidationError.bad_type(dict.__name__, type(query_string_location).__name__),
            proceed=False,
            location=query_string_location,
        )

    if issues.has_issues():
        return RequestData(body=body, options=options), issues

    filter_, issues_ = parse_request_filtering(query_string)
    options["filter"] = filter_
    issues.merge(
        issues=issues_,
        location=("query_string", "filter"),
    )

    sorter, issues_ = parse_request_sorting(query_string)
    options["sorter"] = sorter
    issues.merge(
        issues=issues_,
        location=("query_string", "sortby"),
    )

    checker, issues_ = parse_requested_attributes(query_string)
    if not issues_.has_issues():
        options["presence_checker"] = checker
    issues.merge(
        issues=issues_,
        location=("query_string",),
    )

    count = query_string.get("count")
    if count is not None:
        try:
            options["count"] = int(count)
        except ValueError:
            issues.add(
                issue=ValidationError.bad_type(get_scim_type(int), get_scim_type(type(count))),
                location=("query_string", "count"),
                proceed=False,
            )

    start_index = query_string.get("startIndex")
    if start_index is not None:
        try:
            options["startIndex"] = int(start_index)
        except ValueError:
            issues.add(
                issue=ValidationError.bad_type(
                    get_scim_type(int), get_scim_type(type(start_index))
                ),
                location=("query_string", "startIndex"),
                proceed=False,
            )
    return RequestData(body=body, options=options), issues


def _dump_resources_get_response(
    schema: list_response.ListResponse,
    status_code: int,
    body: Any = None,
    start_index: int = 1,
    count: Optional[int] = None,
    filter_: Optional[Filter] = None,
    sorter: Optional[Sorter] = None,
    resource_presence_checker: Optional[AttributePresenceChecker] = None,
) -> Tuple[ResponseData, ValidationIssues]:
    issues = ValidationIssues()
    body_location = ("body",)
    resources_location = body_location + _location(schema.attrs.resources.rep)

    start_index_rep = schema.attrs.startindex.rep
    start_index_location = body_location + _location(start_index_rep)

    body, issues_ = schema.dump(body)
    issues.merge(issues_, location=body_location)
    if not issues.can_proceed(body_location):
        return ResponseData(body=None), issues

    issues.merge(
        issues=AttributePresenceChecker()(body, schema.attrs, "RESPONSE"),
        location=body_location,
    )
    issues.merge(
        issues=validate_status_code(200, status_code),
        location=("status",),
    )
    if issues.can_proceed(start_index_location):
        start_index_body = body[start_index_rep]
        if start_index_body:
            issues.merge(
                issues=validate_start_index_consistency(start_index, start_index_body),
                location=start_index_location,
            )

    if not issues.can_proceed(resources_location):
        return ResponseData(body=None), issues

    total_results_rep = schema.attrs.totalresults.rep
    total_results_location = body_location + _location(total_results_rep)

    items_per_page_rep = schema.attrs.itemsperpage.rep
    items_per_page_location = body_location + _location(items_per_page_rep)

    resources = body[schema.attrs.resources.rep]
    if resources is Missing:
        resources = []

    if issues.can_proceed(total_results_location):
        total_results = body[total_results_rep]
        issues.merge(
            issues=validate_number_of_resources(
                count=count,
                total_results=total_results,
                resources=resources,
            ),
            location=resources_location,
        )
        if issues.can_proceed(start_index_location, items_per_page_location):
            start_index_body = body[start_index_rep]
            items_per_page = body[items_per_page_rep]
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

    if issues.has_issues(resources_location):
        return ResponseData(body=None), issues

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

    return ResponseData(body=None if issues.has_issues() else body.to_dict()), issues


class ServerRootResourceGET(Validator):
    def __init__(
        self, config: ServiceProviderConfig, *, resource_schemas: Sequence[ResourceSchema]
    ):
        super().__init__(config)
        self._schema = list_response.ListResponse(resource_schemas)

    @property
    def response_schema(self) -> list_response.ListResponse:
        return self._schema

    def parse_request(
        self, *, body: Any = None, query_string: Any = None
    ) -> Tuple[RequestData, ValidationIssues]:
        return _parse_resources_get_request(body, query_string)

    def dump_response(
        self,
        *,
        status_code: int,
        body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Tuple[ResponseData, ValidationIssues]:
        return _dump_resources_get_response(
            schema=self._schema,
            status_code=status_code,
            body=body,
            start_index=kwargs.get("start_index", 1),
            count=kwargs.get("count"),
            filter_=kwargs.get("filter"),
            sorter=kwargs.get("sorter"),
            resource_presence_checker=kwargs.get("presence_checker"),
        )


class ResourcesGET(ServerRootResourceGET):
    def __init__(self, config: ServiceProviderConfig, *, resource_schema: ResourceSchema):
        super().__init__(config, resource_schemas=[resource_schema])


class SearchRequestPOST(Validator):
    def __init__(
        self, config: ServiceProviderConfig, *, resource_schemas: Sequence[ResourceSchema]
    ):
        super().__init__(config)
        self._schema = search_request.SearchRequest()
        self._list_response_schema = list_response.ListResponse(resource_schemas)

    @property
    def request_schema(self) -> search_request.SearchRequest:
        return self._schema

    @property
    def response_schema(self) -> list_response.ListResponse:
        return self._list_response_schema

    def parse_request(
        self, *, body: Any = None, headers: Any = None, query_string: Any = None
    ) -> Tuple[RequestData, ValidationIssues]:
        issues = ValidationIssues()
        body, issues_ = self._schema.parse(body)
        issues.merge(issues_, location=("body",))
        if issues_.has_issues():
            body = None
        return RequestData(body=body, options={}), issues

    def dump_response(
        self,
        *,
        status_code: int,
        body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Tuple[ResponseData, ValidationIssues]:
        return _dump_resources_get_response(
            schema=self._list_response_schema,
            status_code=status_code,
            body=body,
            start_index=kwargs.get("start_index", 1),
            count=kwargs.get("count"),
            filter_=kwargs.get("filter"),
            sorter=kwargs.get("sorter"),
            resource_presence_checker=kwargs.get("presence_checker"),
        )


class ResourceObjectPATCH(Validator):
    def __init__(self, config: ServiceProviderConfig, *, resource_schema: ResourceSchema):
        super().__init__(config)
        self._schema = patch_op.PatchOp(resource_schema)
        self._resource_schema = resource_schema

    @property
    def request_schema(self) -> patch_op.PatchOp:
        return self._schema

    @property
    def response_schema(self) -> ResourceSchema:
        return self._resource_schema

    def parse_request(
        self, *, body: Any = None, query_string: Any = None
    ) -> Tuple[RequestData, ValidationIssues]:
        issues, options = ValidationIssues(), {}
        if isinstance(query_string, Dict):
            checker, issues_ = parse_requested_attributes(query_string)
            issues.merge(issues=issues_, location=("query_string",))
            if checker:
                options["presence_checker"] = checker

        body, issues_ = _parse_body(self._schema, body)
        issues.merge(issues_)
        operations_location = ("body", *_location(self._schema.attrs.operations.rep))

        if not issues.can_proceed(operations_location):
            return RequestData(body=None, options=options), issues

        values = body[self._schema.attrs.operations__value.rep]
        paths = body[self._schema.attrs.operations__path.rep]
        ops = body[self._schema.attrs.operations__op.rep]

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
                        value=value[attr.rep],
                        value_location=value_location + _location(attr.rep),
                    )

            else:
                attr = self._resource_schema.attrs.get_by_path(path)
                self._check_complex_sub_attrs_presence(
                    issues=issues,
                    attr=attr,
                    value=value,
                    value_location=value_location,
                )

        if issues.has_issues():
            body = None
        return RequestData(body=body, options=options), issues

    @staticmethod
    def _check_complex_sub_attrs_presence(
        issues: ValidationIssues,
        attr: Attribute,
        value: Any,
        value_location,
    ) -> None:
        if not (isinstance(attr, ComplexAttribute) and attr.multi_valued) or value is Missing:
            return

        # checking if new item of complex attribute has all required fields
        ignore_required = []
        for sub_attr in attr.attrs:
            if sub_attr.required and sub_attr.issuer == AttributeIssuer.SERVER:
                ignore_required.append(sub_attr.rep)
        presence_checker = AttributePresenceChecker(ignore_required=ignore_required)
        for j, item in enumerate(value):
            item_location = value_location + (j,)
            if not issues.has_issues(item_location):
                issues.merge(
                    issues=presence_checker(
                        data=item,
                        direction="REQUEST",
                        attrs=attr.attrs,
                    ),
                    location=item_location,
                )

    def dump_response(
        self,
        *,
        status_code: int,
        body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Tuple[ResponseData, ValidationIssues]:
        issues = ValidationIssues()
        presence_checker = kwargs.get("presence_checker")
        if status_code == 204:
            if presence_checker is not None and presence_checker.attr_reps:
                issues.add(
                    issue=ValidationError.bad_status_code(200, status_code),
                    proceed=True,
                    location=("status",),
                )
            return ResponseData(body=None), issues
        return _dump_resource_output_body(
            schema=self._resource_schema,
            location_header_required=False,
            expected_status_code=200,
            status_code=status_code,
            body=body,
            headers=headers,
            presence_checker=presence_checker,
        )


class ResourceObjectDELETE(Validator):
    def parse_request(
        self, *, body: Any = None, query_string: Any = None
    ) -> Tuple[RequestData, ValidationIssues]:
        raise NotImplementedError

    def dump_response(
        self,
        *,
        status_code: int,
        body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Tuple[ResponseData, ValidationIssues]:
        issues = ValidationIssues()
        if status_code != 204:
            issues.add(
                issue=ValidationError.bad_status_code(204, status_code),
                proceed=True,
                location=("status",),
            )
        return ResponseData(body=None), issues


class BulkOperations(Validator):
    def __init__(
        self, config: ServiceProviderConfig, *, resource_schemas: Sequence[ResourceSchema]
    ):
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

    def parse_request(
        self, *, body: Any = None, query_string: Any = None
    ) -> Tuple[RequestData, ValidationIssues]:
        issues = ValidationIssues()
        body_location = ("body",)
        body, issues_ = self._request_schema.parse(body)
        issues.merge(issues_, location=body_location)
        issues.merge(
            issues=AttributePresenceChecker()(body, self._request_schema.attrs, "RESPONSE"),
            location=body_location,
        )
        if not issues_.can_proceed(
            body_location + _location(self._request_schema.attrs.operations.rep)
        ):
            return RequestData(body=None, options={}), issues

        path_rep = self._request_schema.attrs.operations__path.rep
        data_rep = self._request_schema.attrs.operations__data.rep
        method_rep = self._request_schema.attrs.operations__method.rep
        paths = body[path_rep]
        data = body[data_rep]
        methods = body[method_rep]
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
                    issues.add(
                        issue=ValidationError.unknown_resource(),
                        proceed=False,
                        location=path_location,
                    )
                    continue
                resource_data, issues_ = validator.parse_request(body=data_item)
                issues.merge(issues_.get(("body",)), location=data_item_location)
                body[self._request_schema.attrs.operations.rep][i][
                    data_rep.sub_attr
                ] = resource_data.body

        if len(body[self._request_schema.attrs.operations.rep]) > self.config.bulk.max_operations:
            issues.add(
                issue=ValidationError.too_many_operations(self.config.bulk.max_operations),
                proceed=True,
                location=body_location + _location(self._response_schema.attrs.operations.rep),
            )

        return RequestData(body=None if issues.has_issues() else body, options={}), issues

    def dump_response(
        self,
        *,
        status_code: int,
        body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        issues = ValidationIssues()
        body_location = ("body",)
        body, issues_ = self._response_schema.dump(body)
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
            return ResponseData(body=None), issues

        operations_location = body_location + _location(self._response_schema.attrs.operations.rep)
        status_rep = self._response_schema.attrs.operations__status.rep
        response_rep = self._response_schema.attrs.operations__response.rep
        location_rep = self._response_schema.attrs.operations__location.rep
        method_rep = self._request_schema.attrs.operations__method.rep
        version_rep = self._response_schema.attrs.operations__version.rep
        statuses = body[status_rep]
        responses = body[response_rep]
        locations = body[location_rep]
        methods = body[method_rep]
        versions = body[version_rep]
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
                    issues.add(
                        issue=ValidationError.unknown_resource(),
                        proceed=False,
                        location=location_location,
                    )

            if not (status and response):
                continue

            status = int(status)
            if status >= 300:
                n_errors += 1
                error_response, issues_ = self._error_validator.dump_response(
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
                body[self._request_schema.attrs.operations.rep][i][
                    response_rep.sub_attr
                ] = error_response.body
            elif all([location, method, resource_validator]):
                resource_data, issues_ = resource_validator.dump_response(
                    body=response,
                    status_code=status,
                    headers={"Location": location},
                )
                meta_location_missmatch = issues_.pop(("body", "meta", "location"), code=11)
                header_location_mismatch = issues_.pop(("headers", "Location"), code=11)
                issues.merge(issues_.get(("body",)), location=response_location)
                if meta_location_missmatch.has_issues() and header_location_mismatch.has_issues():
                    issues.add(
                        issue=ValidationError.must_be_equal_to("operation's location"),
                        proceed=True,
                        location=response_location + ("meta", "location"),
                    )
                    issues.add(
                        issue=ValidationError.must_be_equal_to("'response.meta.location'"),
                        proceed=True,
                        location=location_location,
                    )

                if resource_data.body is not None:
                    resource_body = SCIMDataContainer(resource_data.body)
                    resource_version = resource_body["meta.version"]
                    if version and resource_version and version != resource_version:
                        issues.add(
                            issue=ValidationError.must_be_equal_to("operation's version"),
                            proceed=True,
                            location=response_location + ("meta", "version"),
                        )
                        issues.add(
                            issue=ValidationError.must_be_equal_to("'response.meta.version'"),
                            proceed=True,
                            location=version_location,
                        )
                else:
                    resource_body = None

                body[self._request_schema.attrs.operations.rep][i][
                    response_rep.sub_attr
                ] = resource_body

        fail_on_errors = kwargs.get("fail_on_errors")
        if fail_on_errors is not None and n_errors > fail_on_errors:
            issues.add(
                issue=ValidationError.too_many_errors(fail_on_errors),
                proceed=True,
                location=body_location + _location(self._response_schema.attrs.operations.rep),
            )
        return ResponseData(body=body.to_dict()), issues


class _ServiceProviderConfig(ResourcesGET):
    def __init__(
        self, config: ServiceProviderConfig, *, resource_schema: Union[Schema, ResourceType]
    ):
        super().__init__(config, resource_schema=resource_schema)

    def parse_request(
        self, *, body: Any = None, query_string: Any = None
    ) -> Tuple[RequestData, ValidationIssues]:
        issues = ValidationIssues()
        if isinstance(query_string, Dict) and "filter" in query_string:
            issues.add(
                issue=ValidationError.not_supported(),
                proceed=False,
                location=("query_string", "filter"),
            )
        return RequestData(body=None, options={}), issues


class SchemasGET(_ServiceProviderConfig):
    def __init__(self, config: ServiceProviderConfig):
        super().__init__(config, resource_schema=Schema())


class ResourceTypesGET(_ServiceProviderConfig):
    def __init__(self, config: ServiceProviderConfig):
        super().__init__(config, resource_schema=ResourceType())


def _location(attr_rep: AttrRep) -> Union[Tuple[str], Tuple[str, str]]:
    if attr_rep.sub_attr:
        return attr_rep.attr, attr_rep.sub_attr
    return (attr_rep.attr,)
