from dataclasses import dataclass
from functools import wraps
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from src.attributes.attributes import (
    AttributeIssuer,
    AttributeMutability,
    AttributeName,
    ComplexAttribute,
    Missing,
    extract,
    insert,
)
from src.attributes_presence import AttributePresenceChecker
from src.error import ValidationError, ValidationIssues
from src.filter.filter import Filter
from src.patch import PatchPath
from src.resource.schemas import (
    ERROR,
    LIST_RESPONSE,
    PATCH_OP,
    SEARCH_REQUEST,
    ResourceSchema,
    Schema,
)
from src.sorter import Sorter


@dataclass
class RequestData:
    headers: Optional[Dict[str, Any]]
    query_string: Optional[Dict[str, Any]]
    body: Optional[Dict[str, Any]]


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


def filter_unknown_fields(
    schema: Schema,
    data: Dict[str, Any],
    drop_fields: Optional[Sequence[AttributeName]] = None,
) -> Dict[str, Any]:
    drop_fields = drop_fields or []
    output = {}
    for attr_name in schema.all_attr_names:
        if attr_name in drop_fields:
            continue

        value = extract(attr_name, data)
        if value is Missing:
            continue

        if not isinstance(schema.get_attr(attr_name), ComplexAttribute):
            insert(
                data=output,
                attr_name=attr_name,
                value=value,
                extension=(
                    attr_name.schema
                    and isinstance(schema, ResourceSchema)
                    and attr_name.schema in schema.schema_extensions
                ),
            )
    return output


def validate_existence(data: Any) -> ValidationIssues:
    issues = ValidationIssues()
    if data is None:
        issues.add(
            issue=ValidationError.missing(),
            proceed=False,
        )
    return issues


def validate_dict_type(data: Any) -> ValidationIssues:
    issues = ValidationIssues()
    if data is None:
        return issues

    if not isinstance(data, dict):
        issues.add(
            issue=ValidationError.bad_type(dict, type(data)),
            proceed=False,
        )
    return issues


def _process_body(
    body: Dict[str, Any],
    schema: Union[Schema, ResourceSchema],
    method: str,
) -> Tuple[Dict[str, Any], ValidationIssues]:
    issues = ValidationIssues()
    processed = {}
    for attr_name in schema.top_level_attr_names:
        attr = schema.get_attr(attr_name)
        value = extract(attr_name, body)
        if value is Missing:
            continue
        value, issues_ = getattr(attr, method)(value)
        issues.merge(
            issues=issues_,
            location=(attr_name.attr,),
        )
        extension = (
            isinstance(schema, ResourceSchema) and attr_name.schema in schema.schema_extensions
        )
        insert(processed, attr_name, value, extension)
    return processed, issues


def parse_body(
    body: Dict[str, Any],
    schema: Schema,
) -> Tuple[Dict[str, Any], ValidationIssues]:
    return _process_body(body, schema, "parse")


def dump_body(
    body: Dict[str, Any],
    schema: Schema,
) -> Tuple[Dict[str, Any], ValidationIssues]:
    return _process_body(body, schema, "dump")


@skip_if_bad_data
def validate_schemas_field(
    body: Dict[str, Any],
    schema: Schema,
) -> ValidationIssues:
    issues = ValidationIssues()
    body = {k: v for k, v in body.items() if isinstance(k, str)}
    schemas_value = extract("schemas", body)
    schemas_value = {item.lower() for item in schemas_value if isinstance(item, str)}
    main_schema_included = False
    mismatch = False
    for schema_value in schemas_value:
        if schema_value == schema.schema:
            main_schema_included = True

        elif schema_value not in schema.schemas and not mismatch:
            issues.add(
                issue=ValidationError.unknown_schema(),
                proceed=True,
                location=("schemas",),
            )
            mismatch = True

    if not main_schema_included:
        issues.add(issue=ValidationError.missing_main_schema(), proceed=True, location=("schemas",))

    for k, v in body.items():
        k_lower = k.lower()
        if k_lower in schema.schemas and k_lower not in schemas_value:
            issues.add(
                issue=ValidationError.missing_schema_extension(k),
                proceed=True,
                location=("schemas",),
            )
    return issues


class Error:
    def __init__(self):
        self._schema = ERROR

    def dump_response(
        self, *, status_code: int, body: Any = None, headers: Any = None
    ) -> Tuple[ResponseData, ValidationIssues]:
        issues = ValidationIssues()
        body_location = ("response", "body")
        issues.merge(
            issues=validate_existence(body),
            location=body_location,
        )
        issues.merge(
            issues=validate_dict_type(body),
            location=body_location,
        )
        if issues.can_proceed(body_location):
            body, issues_ = dump_body(body, self._schema)
            issues.merge(
                issues=issues_,
                location=body_location,
            )
            issues.merge(
                issues=validate_schemas_field(body, self._schema),
                location=body_location,
            )
            issues.merge(issues=validate_error_status_code_consistency(body, status_code))
            issues.merge(issues=validate_error_status_code(status_code))
            issues.merge(
                issues=AttributePresenceChecker()(body, self._schema, "RESPONSE"),
                location=body_location,
            )
        if not issues.has_issues(body_location):
            body = filter_unknown_fields(self._schema, body)
        else:
            body = None
        return ResponseData(headers=headers, body=body), issues


@skip_if_bad_data
def validate_error_status_code_consistency(
    body: Dict[str, Any],
    status_code: int,
) -> ValidationIssues:
    issues = ValidationIssues()
    status_in_body = body.get("status")
    if str(status_code) != status_in_body:
        issues.add(
            issue=ValidationError.error_status_mismatch(str(status_code), status_in_body),
            location=("response", "body", "status"),
            proceed=True,
        )
        issues.add(
            issue=ValidationError.error_status_mismatch(str(status_code), status_in_body),
            location=("response", "status"),
            proceed=True,
        )
    return issues


@skip_if_bad_data
def validate_error_status_code(status_code: int) -> ValidationIssues:
    issues = ValidationIssues()
    if not 200 <= status_code < 600:
        issues.add(
            issue=ValidationError.bad_error_status(status_code),
            location=("response", "status"),
            proceed=True,
        )
    return issues


@skip_if_bad_data
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


@skip_if_bad_data
def validate_resource_location_consistency(
    body: Dict[str, Any],
    headers: Dict[str, Any],
) -> ValidationIssues:
    issues = ValidationIssues()
    meta_location = extract("meta.location", body)
    if meta_location != headers.get("Location"):
        issues.add(
            issue=ValidationError.values_must_match(
                value_1="'Location' header",
                value_2="'meta.location' attribute",
            ),
            location=("response", "body", "meta", "location"),
            proceed=True,
        )
        issues.add(
            issue=ValidationError.values_must_match(
                value_1="'Location' header",
                value_2="'meta.location' attribute",
            ),
            location=("response", "headers", "Location"),
            proceed=True,
        )
    return issues


@skip_if_bad_data
def validate_status_code(
    expected_status_code: int,
    actual_status_code: int,
) -> ValidationIssues:
    issues = ValidationIssues()
    if actual_status_code != expected_status_code:
        issues.add(
            issue=ValidationError.bad_status_code(
                method="POST",
                expected=expected_status_code,
                provided=actual_status_code,
            ),
            proceed=True,
        )
    return issues


@skip_if_bad_data
def validate_resource_type_consistency(
    body: Any,
    schema: ResourceSchema,
) -> ValidationIssues:
    issues = ValidationIssues()
    resource_type = extract("meta.resourceType", body)
    if isinstance(resource_type, str) and resource_type != repr(schema):
        issues.add(
            issue=ValidationError.resource_type_mismatch(
                resource_type=repr(schema),
                provided=resource_type,
            ),
            proceed=True,
            location=("meta", "resourcetype"),
        )
    return issues


def parse_input_body(
    schema: Schema,
    body: Any = None,
    required_attrs_to_ignore: Optional[Sequence[AttributeName]] = None,
    drop_fields: Optional[Sequence[AttributeName]] = None,
) -> Tuple[Optional[Dict], ValidationIssues]:
    issues = ValidationIssues()
    body_location = ("request", "body")
    issues.merge(
        issues=validate_existence(body),
        location=body_location,
    )
    issues.merge(
        issues=validate_dict_type(body),
        location=body_location,
    )
    if issues.can_proceed(body_location):
        body, issues_ = parse_body(body, schema)
        issues.merge(
            issues=issues_,
            location=body_location,
        )
        issues.merge(
            issues=validate_schemas_field(body, schema),
            location=body_location,
        )
        issues.merge(
            issues=AttributePresenceChecker(ignore_required=required_attrs_to_ignore)(
                body, schema, "REQUEST"
            ),
            location=body_location,
        )
    if not issues:
        body = filter_unknown_fields(schema, body, drop_fields)
    else:
        body = None
    return body, issues


def dump_resource_output(
    schema: ResourceSchema,
    location_header_required: bool,
    expected_status_code: int,
    status_code: int,
    body: Any = None,
    headers: Any = None,
    presence_checker: Optional[AttributePresenceChecker] = None,
) -> Tuple[ResponseData, ValidationIssues]:
    issues = ValidationIssues()
    body_location = ("response", "body")
    issues.merge(
        issues=validate_existence(body),
        location=body_location,
    )
    issues.merge(
        issues=validate_dict_type(body),
        location=body_location,
    )
    if issues.can_proceed(body_location):
        body, issues_ = dump_body(body, schema)
        issues.merge(
            issues=issues_,
            location=body_location,
        )
        issues.merge(
            issues=validate_schemas_field(body, schema),
            location=body_location,
        )
        issues.merge(
            issues=validate_resource_location_in_header(headers, location_header_required),
            location=("response", "headers"),
        )
        issues.merge(
            issues=validate_resource_type_consistency(body, schema),
            location=body_location,
        )
        issues.merge(
            issues=validate_resource_location_consistency(body, headers),
        )
        issues.merge(
            issues=validate_status_code(expected_status_code, status_code),
            location=("response", "status"),
        )
        issues.merge(
            issues=(presence_checker or AttributePresenceChecker())(body, schema, "RESPONSE"),
            location=body_location,
        )
    if not issues.has_issues(body_location):
        body = filter_unknown_fields(schema, body)
    else:
        body = None
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
            issues.merge(issues=issues_, location=("request", "query_string"))
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
        return dump_resource_output(
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
            issues.merge(issues=issues_, location=("request", "query_string"))
            if not issues_:
                query_string["presence_checker"] = checker

        drop_fields = []
        for attr_name in self._schema.all_attr_names:
            attr = self._schema.get_attr(attr_name)
            if attr.mutability == AttributeMutability.READ_ONLY:
                drop_fields.append(attr_name)

        body, issues_ = parse_input_body(
            schema=self._schema,
            body=body,
            drop_fields=drop_fields,
        )
        issues.merge(issues=issues_)
        return RequestData(body=body, headers=headers, query_string=query_string), issues

    def dump_response(
        self,
        *,
        status_code: int,
        body: Any = None,
        headers: Any = None,
        presence_checker: Optional[AttributePresenceChecker] = None,
    ) -> Tuple[ResponseData, ValidationIssues]:
        return dump_resource_output(
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
            issues.merge(issues=issues_, location=("request", "query_string"))
            if not issues_:
                query_string["presence_checker"] = checker

        required_to_ignore = []
        for attr_name in self._schema.all_attr_names:
            attr = self._schema.get_attr(attr_name)
            if attr.required and attr.issuer == AttributeIssuer.SERVER:
                required_to_ignore.append(attr_name)

        body, issues_ = parse_input_body(self._schema, body, required_to_ignore)
        issues.merge(issues=issues_)
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

        return dump_resource_output(
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
                issue=ValidationError.bad_type(str, type(sort_by)),
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
                issue=ValidationError.bad_type(str, type(filter_exp)),
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

    if not isinstance(to_include, List) or not isinstance(to_exclude, List):
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

    attr_names = to_include or to_exclude
    include = None if not any([to_include, to_exclude]) else bool(to_include)
    checker, issues_ = AttributePresenceChecker.parse(attr_names, include)
    issues.merge(issues=issues_, location=("attributes" if include else "excludeAttributes",))
    return checker, issues


@skip_if_bad_data
def validate_resources_sorted(
    sorter: Sorter,
    resources: List[Any],
    schemas: Sequence[Schema],
) -> ValidationIssues:
    issues = ValidationIssues()
    if resources != sorter(resources, schema=schemas):
        issues.add(
            issue=ValidationError.resources_not_sorted(),
            proceed=True,
            location=("resources",),
        )
    return issues


@skip_if_bad_data
def validate_resources_attribute_presence(
    presence_checker: AttributePresenceChecker,
    resources: List[Any],
    schemas: Sequence[Schema],
) -> ValidationIssues:
    issues = ValidationIssues()
    for i, (resource, schema) in enumerate(zip(resources, schemas)):
        try:
            issues.merge(
                issues=presence_checker(resource, schema, "RESPONSE"),
                location=("resources", i),
            )
        except (AttributeError, TypeError):
            pass
    return issues


@skip_if_bad_data
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
            location=("totalresults",),
            proceed=True,
        )
        issues.add(
            issue=ValidationError.total_results_mismatch(
                total_results=total_results, n_resources=n_resources
            ),
            location=("resources",),
            proceed=True,
        )

    if count is None and total_results > n_resources:
        issues.add(
            issue=ValidationError.too_little_results(must="be equal to 'totalresults'"),
            location=("resources",),
            proceed=True,
        )

    if count is not None and count < n_resources:
        issues.add(
            issue=ValidationError.too_many_results(must="be lesser or equal to 'count' parameter"),
            location=("resources",),
            proceed=True,
        )

    return issues


@skip_if_bad_data
def validate_pagination_info(
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
                issue=ValidationError.missing_required_attribute("startindex"),
                location=("startindex",),
                proceed=False,
            )
        if items_per_page in [None, Missing]:
            issues.add(
                issue=ValidationError.missing_required_attribute("itemsperpage"),
                location=("itemsperpage",),
                proceed=False,
            )
    return issues


@skip_if_bad_data
def validate_start_index_consistency(
    start_index: int,
    body: Any,
) -> ValidationIssues:
    issues = ValidationIssues()
    start_index_body = extract("startindex", body)
    if start_index_body > start_index:
        issues.add(
            issue=ValidationError.response_value_does_not_correspond_to_parameter(
                response_key="startindex",
                response_value=start_index_body,
                query_param_name="startindex",
                query_param_value=start_index,
                reason="bigger value than requested",
            ),
            proceed=True,
            location=("startindex",),
        )
    return issues


@skip_if_bad_data
def validate_items_per_page_consistency(
    resources: List[Any], items_per_page: Any
) -> ValidationIssues:
    issues = ValidationIssues()
    if not isinstance(items_per_page, int):
        return issues

    n_resources = len(resources)
    if items_per_page != n_resources:
        issues.add(
            issue=ValidationError.values_must_match(
                value_1="itemsperpage", value_2="number of Resources"
            ),
            location=("itemsperpage",),
            proceed=True,
        )
        issues.add(
            issue=ValidationError.values_must_match(
                value_1="itemsperpage", value_2="number of Resources"
            ),
            location=("resources",),
            proceed=True,
        )
    return issues


def dump_resources(
    resources: List[Any],
    schemas: Sequence[Schema],
) -> Tuple[List[Dict], ValidationIssues]:
    issues = ValidationIssues()
    dumped_resources = []
    for i, (resource, schema) in enumerate(zip(resources, schemas)):
        if not isinstance(resource, Dict):
            issues.add(
                issue=ValidationError.bad_type(dict, type(resource)),
                location=("resources", i),
                proceed=False,
            )
            continue

        dumped_resource = {}
        for attr_name in schema.top_level_attr_names:
            attr = schema.get_attr(attr_name)
            value = extract(attr_name, resource)
            if value in [None, Missing]:
                continue
            value, issues_ = attr.dump(value)
            issues.merge(
                issues=issues_,
                location=("resources", i, attr_name.attr),
            )
            extension = (
                isinstance(schema, ResourceSchema) and attr_name.schema in schema.schema_extensions
            )
            insert(dumped_resource, attr_name, value, extension=extension)
        dumped_resources.append(dumped_resource)
    return dumped_resources, issues


@skip_if_bad_data
def validate_resources_filtered(
    resources: List[Any], filter_: Filter, schemas: Sequence[Schema], strict: bool
) -> ValidationIssues:
    issues = ValidationIssues()
    for i, (resource, schema) in enumerate(zip(resources, schemas)):
        if not filter_(resource, schema, strict):
            issues.add(
                issue=ValidationError.included_resource_does_not_match_filter(),
                proceed=True,
                location=("resources", i),
            )
    return issues


@skip_if_bad_data
def validate_resources_schemas_field(resources: Any, schemas: Sequence[Schema]):
    issues = ValidationIssues()
    for i, (resource, schema) in enumerate(zip(resources, schemas)):
        if schema is None:
            issues.add(
                issue=ValidationError.unknown_schema(),
                proceed=True,
                location=("resources", i),
            )
        else:
            issues.merge(
                issues=validate_schemas_field(resource, schema),
                location=("resources", i),
            )
    return issues


def _get_schemas_for_resources(
    resources: List[Any], available_schemas: Sequence[Schema]
) -> Optional[List[Schema]]:
    schemas = []
    n_schemas = len(available_schemas)
    for resource in resources:
        if n_schemas == 1:
            schemas.append(available_schemas[0])
        else:
            schemas.append(infer_schema_from_data(resource, available_schemas))
    return schemas


def _parse_resources_get_request(
    body: Any = None, headers: Any = None, query_string: Any = None
) -> Tuple[RequestData, ValidationIssues]:
    issues = ValidationIssues()
    issues.merge(issues=validate_dict_type(query_string), location=("request", "query_string"))
    if isinstance(query_string, Dict):
        filter_, issues_ = parse_request_filtering(query_string)
        query_string["filter"] = filter_
        issues.merge(
            issues=issues_,
            location=("request", "query_string", "filter"),
        )

        sorter, issues_ = parse_request_sorting(query_string)
        query_string["sorter"] = sorter
        issues.merge(
            issues=issues_,
            location=("request", "query_string", "sortby"),
        )

        checker, issues_ = parse_requested_attributes(query_string)
        if not issues_:
            query_string["presence_checker"] = checker
        issues.merge(
            issues=issues_,
            location=("request", "query_string"),
        )

        count = query_string.get("count")
        if count is not None:
            try:
                query_string["count"] = int(count)
            except ValueError:
                issues.add(
                    issue=ValidationError.bad_type(expected_type=int, provided_type=type(count)),
                    location=("request", "query_string", "count"),
                    proceed=False,
                )

        start_index = query_string.get("startIndex")
        if start_index is not None:
            try:
                query_string["startIndex"] = int(start_index)
            except ValueError:
                issues.add(
                    issue=ValidationError.bad_type(
                        expected_type=int, provided_type=type(start_index)
                    ),
                    location=("request", "query_string", "startindex"),
                    proceed=False,
                )
    return RequestData(headers=headers, query_string=query_string, body=body), issues


def _dump_resources_get_response(
    list_response_schema: Schema,
    resource_schemas: Sequence[Schema],
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
    body_location = ("response", "body")
    issues.merge(
        issues=validate_existence(body),
        location=body_location,
    )
    issues.merge(
        issues=validate_dict_type(body),
        location=body_location,
    )
    if issues:
        return ResponseData(headers=headers, body=None), issues

    body, issues_ = dump_body(body, list_response_schema)
    issues.merge(
        issues=issues_,
        location=body_location,
    )
    issues.merge(
        issues=validate_schemas_field(body, list_response_schema),
        location=body_location,
    )
    issues.merge(
        issues=validate_status_code(200, status_code),
        location=("response", "status"),
    )
    issues.merge(
        issues=validate_start_index_consistency(start_index, body),
        location=body_location,
    )
    issues.merge(
        issues=AttributePresenceChecker()(body, list_response_schema, "RESPONSE"),
        location=body_location,
    )

    schemas_for_resources = []
    resources = extract("resources", body)
    if not (resources is Missing or isinstance(resources, List)):
        issues.add(
            issue=ValidationError.bad_type(list, type(resources)),
            location=body_location + ("resources",),
            proceed=False,
        )

    if issues.can_proceed(body_location + ("resources",)):
        total_results = extract("totalresults", body)
        start_index_body = extract("startindex", body)
        items_per_page = extract("itemsperpage", body)
        issues.merge(
            issues=validate_number_of_resources(
                count=count,
                total_results=total_results,
                resources=resources,
            ),
            location=body_location,
        )
        issues.merge(
            issues=validate_pagination_info(
                count=count,
                total_results=total_results,
                resources=resources,
                start_index=start_index_body,
                items_per_page=items_per_page,
            ),
            location=body_location,
        )
        issues.merge(
            issues=validate_items_per_page_consistency(
                resources=resources,
                items_per_page=items_per_page,
            ),
            location=body_location,
        )
        if resources:
            schemas_for_resources = _get_schemas_for_resources(resources, resource_schemas)
            issues.merge(
                issues=validate_resources_schemas_field(resources, schemas_for_resources),
                location=body_location,
            )
            resources, issues_ = dump_resources(resources, schemas_for_resources)
            issues.merge(
                issues=issues_,
                location=body_location,
            )
            if filter_ is not None:
                issues.merge(
                    issues=validate_resources_filtered(
                        resources, filter_, schemas_for_resources, False
                    ),
                    location=body_location,
                )
            if sorter is not None:
                issues.merge(
                    issues=validate_resources_sorted(sorter, resources, schemas_for_resources),
                    location=body_location,
                )
            if resource_presence_checker is None:
                resource_presence_checker = AttributePresenceChecker()
            issues.merge(
                issues=validate_resources_attribute_presence(
                    resource_presence_checker, resources, schemas_for_resources
                ),
                location=body_location,
            )

    if issues:
        return ResponseData(headers=headers, body=None), issues

    if resources and schemas_for_resources:
        body = filter_unknown_fields(list_response_schema, body)
        body["resources"] = [
            filter_unknown_fields(schema, resource)
            for schema, resource in zip(schemas_for_resources, resources)
        ]

    return ResponseData(headers=headers, body=body), issues


class ResourceTypeGET:
    def __init__(self, resource_schema: Schema):
        self._schema = LIST_RESPONSE
        self._resource_schema = resource_schema

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
            list_response_schema=self._schema,
            resource_schemas=[self._resource_schema],
            status_code=status_code,
            body=body,
            headers=headers,
            start_index=start_index,
            count=count,
            filter_=filter_,
            sorter=sorter,
            resource_presence_checker=presence_checker,
        )


def infer_schema_from_data(data: Any, schemas: Sequence[Schema]) -> Optional[Schema]:
    if not isinstance(data, Dict):
        return None

    schemas_value = extract("schemas", data)
    if isinstance(schemas_value, List) and len(schemas_value) > 0:
        schemas_value = {item.lower() if isinstance(item, str) else item for item in schemas_value}
        for schema in schemas:
            if not schemas_value.difference(set(schema.schemas)):
                return schema
    return None


class ServerRootResourceGET:
    def __init__(self, resource_schemas: Sequence[Schema]):
        self._schema = LIST_RESPONSE
        self._resource_schemas = resource_schemas

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
            list_response_schema=self._schema,
            resource_schemas=self._resource_schemas,
            status_code=status_code,
            body=body,
            headers=headers,
            start_index=start_index,
            count=count,
            filter_=filter_,
            sorter=sorter,
            resource_presence_checker=presence_checker,
        )


class SearchRequestPOST:
    def __init__(self, resource_schemas: Sequence[Schema]):
        self._schema = SEARCH_REQUEST
        self._list_response_schema = LIST_RESPONSE
        self._resource_schemas = resource_schemas

    def parse_request(
        self, *, body: Any = None, headers: Any = None, query_string: Any = None
    ) -> Tuple[RequestData, ValidationIssues]:
        issues = ValidationIssues()
        body_location = ("request", "body")
        issues.merge(
            issues=validate_existence(body),
            location=body_location,
        )
        issues.merge(
            issues=validate_dict_type(body),
            location=body_location,
        )
        if issues.can_proceed(body_location):
            body, issues_ = parse_body(body, self._schema)
            issues.merge(
                issues=issues_,
                location=body_location,
            )

        to_include, to_exclude = None, None
        if issues.can_proceed(
            body_location + ("attributes",), body_location + ("excludeAttributes",)
        ):
            to_include = body.get("attributes")
            to_exclude = body.get("excludeattributes")
            if to_include and to_exclude:
                issues.add(
                    issue=ValidationError.can_not_be_used_together("excludeAttributes"),
                    proceed=False,
                    location=body_location + ("attributes",),
                )
                issues.add(
                    issue=ValidationError.can_not_be_used_together("attributes"),
                    proceed=False,
                    location=body_location + ("excludeAttributes",),
                )

        if not issues.has_issues(body_location):
            body = filter_unknown_fields(self._schema, body)

            if to_include or to_exclude:
                body["presence_checker"] = AttributePresenceChecker(
                    attr_names=to_include or to_exclude, include=bool(to_include)
                )
                body.pop("attributes", None)
                body.pop("excludeAttributes", None)

            if "sortby" in body:
                body["sorter"] = Sorter(
                    attr_name=body["sortby"], asc=body.get("sortorder") == "ascending"
                )
                body.pop("sortby")
                body.pop("sortorder")
        else:
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
            list_response_schema=self._list_response_schema,
            resource_schemas=self._resource_schemas,
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
        self._schema = PATCH_OP
        self._resource_schema = resource_schema

    def parse_request(  # noqa
        self, *, body: Any = None, headers: Any = None, query_string: Any = None
    ) -> Tuple[RequestData, ValidationIssues]:
        issues = ValidationIssues()
        if isinstance(query_string, Dict):
            checker, issues_ = parse_requested_attributes(query_string)
            issues.merge(issues=issues_, location=("request", "query_string"))
            if not issues_:
                query_string["presence_checker"] = checker

        body, issues_ = parse_input_body(self._schema, body)
        issues.merge(issues_)

        if issues:
            body = None
        else:
            operations = extract("operations", body)
            operations, issues_ = parse_operations(self._schema, operations)
            issues.merge(issues_, location=("request", "body", "operations"))

        if issues:
            body = None
        return RequestData(body=body, headers=headers, query_string=query_string), issues


def parse_operations(
    schema: ResourceSchema, data: List[Dict[str, Any]]
) -> Tuple[Optional[List[Dict[str, Any]]], ValidationIssues]:
    issues = ValidationIssues()
    parsed = []
    for i, item in enumerate(data):
        path = extract("path", item)
        if path not in [None, Missing]:
            issues_ = validate_operation_path(schema, path)
            if issues_:
                issues.merge(issues_, location=(i, "path"))
                parsed.append(None)
                continue

        type_ = extract("op", item)
        value = extract("value", item)
        if type_ == "add":
            value, issues_ = _parse_add_operation_value(schema, path, value)
            if issues_:
                issues.merge(issues_, location=(i, "value"))
                parsed.append(None)
            else:
                parsed.append(
                    {
                        "type": type_,
                        "path": path,
                        "value": value,
                    }
                )
    if issues:
        return None, issues
    return parsed, issues


def _parse_add_operation_value(
    schema: ResourceSchema, path: Optional[PatchPath], value: Any
) -> Tuple[Any, ValidationIssues]:
    if path in [None, Missing]:
        return _parse_add_operation_value_no_path(schema, value)

    # sub-attribute of filtered multivalued complex attribute
    if (
        isinstance(schema.get_attr(path.attr_name), ComplexAttribute)
        and path.complex_filter
        and path.complex_filter_attr_name
    ):
        return _parse_update_attr_value(schema, path.complex_filter_attr_name, value)
    return _parse_update_attr_value(schema, path.attr_name, value)


def _parse_add_operation_value_no_path(
    schema: ResourceSchema, value: Any
) -> Tuple[Any, ValidationIssues]:
    issues = ValidationIssues()
    issues.merge(validate_dict_type(value))
    if issues:
        return None, issues

    value_parsed = {}
    for k, v in value.items():
        if not isinstance(k, str):
            continue

        attr_name = AttributeName.parse(k)
        if attr_name is None:
            continue

        k = k.lower()
        if k in schema.schema_extensions:
            issues_ = validate_dict_type(v)
            if issues_:
                issues.merge(issues_, location=(k,))
                continue

            for k_, v_ in v.items():
                if not isinstance(k_, str):
                    continue
                sub_attr_name = AttributeName.parse(attr_name.full_attr + ":" + k_)
                if sub_attr_name is None:
                    continue
                parsed_v_, issues_ = _parse_update_attr_value(schema, sub_attr_name, v_)
                if issues_:
                    issues.merge(issues_, location=(k, k_))
                else:
                    if k not in value_parsed:
                        value_parsed[k] = {}
                    value_parsed[k][k_] = parsed_v_
        else:
            parsed_v, issues_ = _parse_update_attr_value(schema, attr_name, v)
            if issues_:
                issues.merge(issues_, location=(k,))
            else:
                value_parsed[k] = parsed_v

    if issues:
        return None, issues
    return value_parsed, issues


def _parse_update_attr_value(
    schema: Schema,
    attr_name: AttributeName,
    attr_value: Any,
) -> Tuple[Any, ValidationIssues]:
    issues = ValidationIssues()

    attr = schema.get_attr(attr_name)
    if attr is None:
        return None, issues

    if attr.mutability == AttributeMutability.READ_ONLY:
        issues.add(
            issue=ValidationError.read_only_attribute_can_not_be_updated(),
            proceed=False,
        )
        return None, issues

    parsed_attr_value, issues_ = attr.parse(attr_value)
    if issues_:
        issues.merge(issues_)
    elif isinstance(attr, ComplexAttribute):
        if attr.multi_valued:
            ignore_required = []
            for sub_attr in attr.sub_attributes:
                if sub_attr.required and sub_attr.issuer == AttributeIssuer.SERVER:
                    ignore_required.append(sub_attr.name)
            presence_checker = AttributePresenceChecker(ignore_required=ignore_required)
            for i, item in enumerate(parsed_attr_value):
                issues.merge(
                    issues=presence_checker(
                        data=item,
                        schema=schema,
                        direction="REQUEST",
                        attrs=attr.sub_attributes,
                    ),
                    location=(i,),
                )
        else:
            for sub_attr in attr.sub_attributes:
                if sub_attr.mutability != AttributeMutability.READ_ONLY:
                    # non-read-only attributes can be updated
                    continue
                v = extract(sub_attr.name, parsed_attr_value)
                if v is not Missing:
                    issues.add(
                        issue=ValidationError.read_only_attribute_can_not_be_updated(),
                        proceed=False,
                        location=(sub_attr.name.sub_attr,),
                    )

    if issues.has_issues():
        return None, issues
    return parsed_attr_value, issues


def validate_operation_path(schema: ResourceSchema, path: PatchPath) -> ValidationIssues():
    issues = ValidationIssues()
    if (
        schema.get_attr(path.attr_name) is None
        or (
            path.complex_filter_attr_name is not None
            and schema.get_attr(path.complex_filter_attr_name) is None
        )
        or (
            path.complex_filter is not None
            and schema.get_attr(path.complex_filter.attr_name) is None
        )
    ):
        issues.add(
            issue=ValidationError.unknown_update_target(),
            proceed=False,
        )
    return issues
