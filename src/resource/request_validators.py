from dataclasses import dataclass
from functools import wraps
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from src.attributes_presence import AttributePresenceChecker
from src.data.attributes import (
    Attribute,
    AttributeIssuer,
    AttributeMutability,
    ComplexAttribute,
)
from src.data.container import AttrRep, Missing, SCIMDataContainer
from src.data.type import get_scim_type
from src.error import ValidationError, ValidationIssues
from src.filter import Filter
from src.resource.schemas import error, list_response, patch_op, search_request
from src.schemas import BaseSchema, ResourceSchema
from src.sorter import Sorter


@dataclass
class RequestData:
    headers: Optional[Dict[str, Any]]
    query_string: Optional[Dict[str, Any]]
    body: Optional[SCIMDataContainer]


@dataclass
class ResponseData:
    headers: Optional[Dict[str, Any]]
    body: Optional[Dict[str, Any]]


def skip_if_bad_data(func):
    @wraps(func)
    def wrapper(*args, **kwargs) -> ValidationIssues():
        try:
            return func(*args, **kwargs)
        except (TypeError, AttributeError, IndexError, ValueError):
            return ValidationIssues()

    return wrapper


class Error:
    def __init__(self):
        self._schema = error.Error()

    def dump_response(
        self, *, status_code: int, body: Any = None, headers: Any = None
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

        if issues:
            body = None

        return ResponseData(headers=headers, body=body.to_dict()), issues


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
) -> Tuple[Optional[Dict], ValidationIssues]:
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

    body = body.to_dict() if not issues else None
    return ResponseData(headers=headers, body=body), issues


class ResourceObjectGET:
    def __init__(self, schema: ResourceSchema):
        self._schema = schema

    def parse_request(  # noqa
        self, *, body: Any = None, headers: Any = None, query_string: Any = None
    ) -> Tuple[RequestData, ValidationIssues]:
        issues = ValidationIssues()
        if isinstance(query_string, Dict):
            checker, issues_ = parse_requested_attributes(query_string)
            issues.merge(issues=issues_, location=("query_string",))
            if not issues_:
                query_string["presence_checker"] = checker
        return RequestData(body=body, headers=headers, query_string=query_string), issues

    def dump_response(
        self,
        *,
        status_code: int,
        body: Any = None,
        headers: Any = None,
        presence_checker: Optional[AttributePresenceChecker] = None,
    ) -> Tuple[ResponseData, ValidationIssues]:
        return _dump_resource_output_body(
            schema=self._schema,
            location_header_required=True,
            expected_status_code=200,
            status_code=status_code,
            body=body,
            headers=headers,
            presence_checker=presence_checker,
        )


class ResourceObjectPUT:
    def __init__(self, schema: ResourceSchema):
        self._schema = schema

    def parse_request(
        self, *, body: Any = None, headers: Any = None, query_string: Any = None
    ) -> Tuple[RequestData, ValidationIssues]:
        issues = ValidationIssues()
        if isinstance(query_string, Dict):
            checker, issues_ = parse_requested_attributes(query_string)
            issues.merge(issues=issues_, location=("query_string",))
            if not issues_:
                query_string["presence_checker"] = checker

        body, issues_ = _parse_body(schema=self._schema, body=body)
        issues.merge(issues=issues_)

        if issues:
            body = None
        else:
            for attr in self._schema.attrs:
                if attr.mutability == AttributeMutability.READ_ONLY:
                    del body[attr.rep]

        return RequestData(body=body, headers=headers, query_string=query_string), issues

    def dump_response(
        self,
        *,
        status_code: int,
        body: Any = None,
        headers: Any = None,
        presence_checker: Optional[AttributePresenceChecker] = None,
    ) -> Tuple[ResponseData, ValidationIssues]:
        return _dump_resource_output_body(
            schema=self._schema,
            location_header_required=False,
            expected_status_code=200,
            status_code=status_code,
            body=body,
            headers=headers,
            presence_checker=presence_checker,
        )


class ResourceTypePOST:
    def __init__(self, schema: ResourceSchema):
        self._schema = schema

    def parse_request(
        self, *, body: Any = None, headers: Any = None, query_string: Any = None
    ) -> Tuple[RequestData, ValidationIssues]:
        issues = ValidationIssues()
        if isinstance(query_string, Dict):
            checker, issues_ = parse_requested_attributes(query_string)
            issues.merge(issues=issues_, location=("query_string",))
            if not issues_:
                query_string["presence_checker"] = checker

        required_to_ignore = []
        for attr in self._schema.attrs:
            if attr.required and attr.issuer == AttributeIssuer.SERVER:
                required_to_ignore.append(attr.rep)

        body, issues_ = _parse_body(self._schema, body, required_to_ignore)
        issues.merge(issues=issues_)
        if issues:
            body = None
        return RequestData(body=body, headers=headers, query_string=query_string), issues

    def dump_response(
        self,
        *,
        status_code: int,
        body: Any = None,
        headers: Any = None,
        presence_checker: Optional[AttributePresenceChecker] = None,
    ) -> Tuple[ResponseData, ValidationIssues]:
        issues = ValidationIssues()
        if not body:
            return ResponseData(headers=headers, body=None), issues  # TODO: warn missing body

        return _dump_resource_output_body(
            schema=self._schema,
            location_header_required=True,
            expected_status_code=201,
            status_code=status_code,
            body=body,
            headers=headers,
            presence_checker=presence_checker,
        )


def parse_request_sorting(query_string: Dict) -> Tuple[Optional[Sorter], ValidationIssues]:
    issues = ValidationIssues()

    sort_by = query_string.get("sortBy")
    if not isinstance(sort_by, str):
        if sort_by is not None:
            issues.add(
                issue=ValidationError.bad_type(get_scim_type(str), get_scim_type(type(sort_by))),
                proceed=False,
            )
        return None, issues

    sort_order = query_string.get("sortOrder", "ascending")
    if sort_order not in ["ascending", "descending"]:
        pass  # TODO add warning here

    return Sorter.parse(by=sort_by, asc=sort_order == "ascending")


def parse_request_filtering(query_string: Dict) -> Tuple[Optional[Filter], ValidationIssues]:
    issues = ValidationIssues()
    filter_exp = query_string.get("filter")
    if not isinstance(filter_exp, str):
        if filter_exp is not None:
            issues.add(
                issue=ValidationError.bad_type(get_scim_type(str), get_scim_type(type(filter_exp))),
                proceed=False,
            )
        return None, issues
    return Filter.parse(filter_exp)


def parse_requested_attributes(
    query_string: Dict[str, Any],
) -> Tuple[Optional[AttributePresenceChecker], ValidationIssues]:
    issues = ValidationIssues()
    to_include = query_string.get("attributes", [])
    if to_include and isinstance(to_include, str):
        to_include = to_include.split(",")
    to_exclude = query_string.get("excludeAttributes", [])
    if to_exclude and isinstance(to_exclude, str):
        to_exclude = to_exclude.split(",")

    if not (isinstance(to_include, List) and isinstance(to_exclude, List)) or not (
        to_include or to_exclude
    ):
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
        return None, issues

    attr_reps = to_include or to_exclude
    include = None if not any([to_include, to_exclude]) else bool(to_include)
    checker, issues_ = AttributePresenceChecker.parse(attr_reps, include)
    issues.merge(issues=issues_, location=("attributes" if include else "excludeAttributes",))
    return checker, issues


@skip_if_bad_data
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


@skip_if_bad_data
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


@skip_if_bad_data
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
    body: Any = None, headers: Any = None, query_string: Any = None
) -> Tuple[RequestData, ValidationIssues]:
    issues = ValidationIssues()
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

    if issues:
        return RequestData(headers=headers, query_string=query_string, body=body), issues

    filter_, issues_ = parse_request_filtering(query_string)
    query_string["filter"] = filter_
    issues.merge(
        issues=issues_,
        location=("query_string", "filter"),
    )

    sorter, issues_ = parse_request_sorting(query_string)
    query_string["sorter"] = sorter
    issues.merge(
        issues=issues_,
        location=("query_string", "sortby"),
    )

    checker, issues_ = parse_requested_attributes(query_string)
    if not issues_:
        query_string["presence_checker"] = checker
    issues.merge(
        issues=issues_,
        location=("query_string",),
    )

    count = query_string.get("count")
    if count is not None:
        try:
            query_string["count"] = int(count)
        except ValueError:
            issues.add(
                issue=ValidationError.bad_type(get_scim_type(int), get_scim_type(type(count))),
                location=("query_string", "count"),
                proceed=False,
            )

    start_index = query_string.get("startIndex")
    if start_index is not None:
        try:
            query_string["startIndex"] = int(start_index)
        except ValueError:
            issues.add(
                issue=ValidationError.bad_type(
                    get_scim_type(int), get_scim_type(type(start_index))
                ),
                location=("query_string", "startIndex"),
                proceed=False,
            )
    return RequestData(headers=headers, query_string=query_string, body=body), issues


def _dump_resources_get_response(
    schema: list_response.ListResponse,
    status_code: int,
    body: Any = None,
    headers: Any = None,
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
        return ResponseData(headers=headers, body=None), issues

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
        return ResponseData(headers=headers, body=None), issues

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
        return ResponseData(headers=headers, body=None), issues

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

    if issues:
        return ResponseData(headers=headers, body=None), issues

    return ResponseData(headers=headers, body=body.to_dict()), issues


class ServerRootResourceGET:
    def __init__(self, resource_schemas: Sequence[ResourceSchema]):
        self._schema = list_response.ListResponse(resource_schemas)

    def parse_request(  # noqa
        self, *, body: Any = None, headers: Any = None, query_string: Any = None
    ) -> Tuple[RequestData, ValidationIssues]:
        return _parse_resources_get_request(body, headers, query_string)

    def dump_response(
        self,
        *,
        status_code: int,
        body: Any = None,
        headers: Any = None,
        start_index: int = 1,
        count: Optional[int] = None,
        filter_: Optional[Filter] = None,
        sorter: Optional[Sorter] = None,
        presence_checker: Optional[AttributePresenceChecker] = None,
    ) -> Tuple[ResponseData, ValidationIssues]:
        return _dump_resources_get_response(
            schema=self._schema,
            status_code=status_code,
            body=body,
            headers=headers,
            start_index=start_index,
            count=count,
            filter_=filter_,
            sorter=sorter,
            resource_presence_checker=presence_checker,
        )


class ResourceTypeGET(ServerRootResourceGET):
    def __init__(self, resource_schema: ResourceSchema):
        super().__init__([resource_schema])


class SearchRequestPOST:
    def __init__(self, resource_schemas: Sequence[ResourceSchema]):
        self._schema = search_request.SearchRequest()
        self._list_response_schema = list_response.ListResponse(resource_schemas)

    def parse_request(
        self, *, body: Any = None, headers: Any = None, query_string: Any = None
    ) -> Tuple[RequestData, ValidationIssues]:
        issues = ValidationIssues()
        body, issues_ = self._schema.parse(body)
        issues.merge(issues_, location=("body",))
        if issues_:
            body = None
        return RequestData(headers=headers, query_string=query_string, body=body), issues

    def dump_response(
        self,
        *,
        status_code: int,
        body: Any = None,
        headers: Any = None,
        start_index: int = 1,
        count: Optional[int] = None,
        filter_: Optional[Filter] = None,
        sorter: Optional[Sorter] = None,
        presence_checker: Optional[AttributePresenceChecker] = None,
    ) -> Tuple[ResponseData, ValidationIssues]:
        return _dump_resources_get_response(
            schema=self._list_response_schema,
            status_code=status_code,
            body=body,
            headers=headers,
            start_index=start_index,
            count=count,
            filter_=filter_,
            sorter=sorter,
            resource_presence_checker=presence_checker,
        )


class ResourceObjectPATCH:
    def __init__(self, resource_schema: ResourceSchema):
        self._schema = patch_op.PatchOp(resource_schema)
        self._resource_schema = resource_schema

    def parse_request(  # noqa
        self, *, body: Any = None, headers: Any = None, query_string: Any = None
    ) -> Tuple[RequestData, ValidationIssues]:
        issues = ValidationIssues()

        if isinstance(query_string, Dict):
            checker, issues_ = parse_requested_attributes(query_string)
            issues.merge(issues=issues_, location=("query_string",))
            if not issues_:
                query_string["presence_checker"] = checker

        body, issues_ = _parse_body(self._schema, body)
        issues.merge(issues_)
        operations_location = ("body", *_location(self._schema.attrs.operations.rep))

        if not issues.can_proceed(operations_location):
            return RequestData(body=None, headers=headers, query_string=query_string), issues

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

        if issues:
            body = None
        return RequestData(body=body, headers=headers, query_string=query_string), issues

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
        body: Any = None,
        headers: Any = None,
        presence_checker: Optional[AttributePresenceChecker] = None,
    ) -> Tuple[ResponseData, ValidationIssues]:
        issues = ValidationIssues()
        if status_code == 204:
            if presence_checker is not None and presence_checker.attr_reps:
                issues.add(
                    issue=ValidationError.bad_status_code(200, status_code),
                    proceed=True,
                    location=("status",),
                )
            return ResponseData(headers=headers, body=None), issues
        return _dump_resource_output_body(
            schema=self._resource_schema,
            location_header_required=False,
            expected_status_code=200,
            status_code=status_code,
            body=body,
            headers=headers,
            presence_checker=presence_checker,
        )


class ResourceObjectDELETE:
    @staticmethod
    def dump_response(
        *,
        status_code: int,
        headers: Any = None,
    ) -> Tuple[ResponseData, ValidationIssues]:
        issues = ValidationIssues()
        if status_code != 204:
            issues.add(
                issue=ValidationError.bad_status_code(204, status_code),
                proceed=True,
                location=("status",),
            )
        return ResponseData(headers=headers, body=None), issues


def _location(attr_rep: AttrRep) -> Union[Tuple[str], Tuple[str, str]]:
    if attr_rep.sub_attr:
        return attr_rep.attr, attr_rep.sub_attr
    return (attr_rep.attr,)
