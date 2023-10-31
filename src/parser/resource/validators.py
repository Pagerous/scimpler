from typing import Any, Dict, Iterable, List, Optional

from src.parser.attributes.attributes import AttributeName
from src.parser.attributes.common import schemas as schemas_attr
from src.parser.error import ValidationError, ValidationIssues
from src.parser.parameters.filter.filter import Filter
from src.parser.parameters.sorter.sorter import Sorter
from src.parser.resource.schemas import ERROR, LIST_RESPONSE, ResourceSchema, Schema


def validate_body_existence(body: Any) -> ValidationIssues:
    issues = ValidationIssues()
    if body is None:
        issues.add(
            issue=ValidationError.missing(),
            proceed=False,
        )
    return issues


def validate_body_type(body: Any) -> ValidationIssues:
    issues = ValidationIssues()
    if body is None:
        return issues

    if not isinstance(body, dict):
        issues.add(
            issue=ValidationError.bad_type(dict, type(body)),
            proceed=False,
        )
    return issues


def validate_body_schema(
    direction: str,
    body: Any,
    schema: Schema,
) -> ValidationIssues:
    issues = ValidationIssues()
    if not isinstance(body, Dict):
        return issues

    for attr_name in schema.top_level_attr_names:
        attr = schema.get_attr(attr_name)
        value = attr_name.extract(body)
        issues.merge(
            issues=attr.validate(value, direction),
            location=(attr_name.attr,),
        )
    return issues


def validate_schemas_field(
    body: Any,
    schema: Schema,
) -> ValidationIssues:
    issues = ValidationIssues()
    if not isinstance(body, Dict):
        return issues

    schemas_value = schema.get_attr_name(schemas_attr).extract(body)
    if not isinstance(schemas_value, List):
        return issues

    for schema_value in schemas_value:
        try:
            if schema_value.lower() not in schema.schemas:
                issues.add(
                    issue=ValidationError.schemas_mismatch(repr(schema)),
                    proceed=True,
                    location=(schemas_attr.name,),
                )
                break
        except AttributeError:
            pass
    return issues


class Error:
    def __init__(self):
        self._schema = ERROR

    def validate_response(
        self,
        *,
        status_code: int,
        response_body: Any,
    ) -> ValidationIssues:
        issues = ValidationIssues()
        body_location = ("response", "body")
        issues.merge(
            issues=validate_body_existence(response_body),
            location=body_location,
        )
        issues.merge(
            issues=validate_body_type(response_body),
            location=body_location,
        )
        issues.merge(
            issues=validate_body_schema("RESPONSE", response_body, self._schema),
            location=body_location,
        )
        issues.merge(
            issues=validate_schemas_field(response_body, self._schema),
            location=body_location,
        )
        issues.merge(issues=validate_error_status_code_consistency(response_body, status_code))
        issues.merge(issues=validate_error_status_code(status_code))
        return issues


def validate_error_status_code_consistency(
    body: Dict[str, Any],
    status_code: int,
) -> ValidationIssues:
    issues = ValidationIssues()
    if not isinstance(body, Dict):
        return issues

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


def validate_error_status_code(status_code: int) -> ValidationIssues:
    issues = ValidationIssues()
    if not 200 <= status_code < 600:
        issues.add(
            issue=ValidationError.bad_error_status(status_code),
            location=("response", "status"),
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
    body: Any,
    headers: Any,
) -> ValidationIssues:
    issues = ValidationIssues()
    if not isinstance(body, Dict) or not isinstance(headers, Dict):
        return issues

    meta_location = AttributeName(attr="meta", sub_attr="location").extract(body)
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


def validate_resource_type_consistency(
    body: Any,
    schema: ResourceSchema,
) -> ValidationIssues:
    issues = ValidationIssues()
    if not isinstance(body, Dict):
        return issues

    resource_type = AttributeName(attr="meta", sub_attr="resourcetype").extract(body)
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


class ResourceObjectGET:
    def __init__(self, schema: ResourceSchema):
        self._schema = schema

    def validate_response(
        self,
        *,
        status_code: int,
        response_body: Optional[Dict[str, Any]] = None,
        response_headers: Optional[Dict[str, Any]] = None,
    ) -> ValidationIssues:
        issues = ValidationIssues()
        body_location = ("response", "body")
        issues.merge(
            issues=validate_body_existence(response_body),
            location=body_location,
        )
        issues.merge(
            issues=validate_body_type(response_body),
            location=body_location,
        )
        issues.merge(
            issues=validate_body_schema("RESPONSE", response_body, self._schema),
            location=body_location,
        )
        issues.merge(
            issues=validate_schemas_field(response_body, self._schema),
            location=body_location,
        )
        issues.merge(
            issues=validate_resource_location_in_header(response_headers, False),
            location=("response", "headers"),
        )
        issues.merge(
            issues=validate_resource_type_consistency(response_body, self._schema),
            location=body_location,
        )
        issues.merge(
            issues=validate_resource_location_consistency(response_body, response_headers),
        )
        issues.merge(
            issues=validate_status_code(200, status_code),
            location=("response", "status"),
        )
        return issues


class ResourceTypePOST:
    def __init__(self, schema: ResourceSchema):
        self._schema = schema

    def validate_request(
        self,
        *,
        body: Optional[Dict[str, Any]] = None,
    ) -> ValidationIssues:
        issues = ValidationIssues()
        direction = "REQUEST"
        body_location = ("request", "body")
        issues.merge(
            issues=validate_body_existence(body),
            location=body_location,
        )
        issues.merge(
            issues=validate_body_type(body),
            location=body_location,
        )
        issues.merge(
            issues=validate_body_schema(direction, body, self._schema),
            location=body_location,
        )
        issues.merge(
            issues=validate_schemas_field(body, self._schema),
            location=body_location,
        )
        return issues

    def validate_response(
        self,
        *,
        status_code: int,
        response_body: Optional[Dict[str, Any]] = None,
        response_headers: Optional[Dict[str, Any]] = None,
    ) -> ValidationIssues:
        issues = ValidationIssues()
        if not response_body:
            return issues  # TODO: warn missing response body

        body_location = ("response", "body")
        issues.merge(
            issues=validate_body_type(response_body),
            location=body_location,
        )
        issues.merge(
            issues=validate_body_schema("RESPONSE", response_body, self._schema),
            location=body_location,
        )
        issues.merge(
            issues=validate_resource_location_in_header(response_headers, True),
            location=("response", "headers"),
        )
        issues.merge(
            issues=validate_resource_type_consistency(response_body, self._schema),
            location=body_location,
        )
        issues.merge(
            issues=validate_resource_location_consistency(response_body, response_headers),
        )
        issues.merge(
            issues=validate_status_code(201, status_code),
            location=("response", "status"),
        )
        issues.merge(
            issues=validate_schemas_field(response_body, self._schema),
            location=body_location,
        )
        return issues


def validate_request_sorting(
    query_string: Any,
    schema: Optional[Schema],
) -> ValidationIssues:
    issues = ValidationIssues()
    if not isinstance(query_string, Dict):
        return issues

    sort_by = query_string.get("sortBy")
    if not isinstance(sort_by, str):
        return issues

    sort_order = query_string.get("sortOrder", "ascending")
    if sort_order not in ["ascending", "descending"]:
        pass  # TODO add warning here

    _, issues_ = Sorter.parse(
        by=sort_by,
        schema=schema,
        asc=sort_order == "ascending",
        strict=True,
    )
    return issues_


def validate_request_filtering(
    query_string: Any,
    schema: Optional[Schema],
    strict: bool,
) -> ValidationIssues:
    issues = ValidationIssues()
    if not isinstance(query_string, Dict):
        return issues

    filter_exp = query_string.get("filter")
    if isinstance(filter_exp, str):
        _, issues_ = Filter.parse(filter_exp, schema, strict)
        issues = issues_
    return issues


def validate_resources_sorted(
    sorter: Sorter,
    response_body: Any,
) -> ValidationIssues:
    issues = ValidationIssues()
    if not isinstance(response_body, Dict):
        return issues

    resources = AttributeName(attr="resources").extract(response_body) or []
    if not isinstance(resources, List):
        return issues

    try:
        if resources != sorter(resources):
            issues.add(
                issue=ValidationError.resources_not_sorted(),
                proceed=True,
                location=("resources",),
            )
    except:  # noqa; error due to bad resources schema
        pass
    return issues


def validate_number_of_resources(
    count: Optional[int],
    response_body: Any,
) -> ValidationIssues:
    issues = ValidationIssues()
    if not isinstance(response_body, Dict):
        return issues

    total_results = AttributeName(attr="totalresults").extract(response_body)
    if not isinstance(total_results, int):
        return issues

    resources = AttributeName(attr="resources").extract(response_body) or []
    if not isinstance(resources, List):
        return issues

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


def validate_pagination_info(
    count: Optional[int],
    response_body: Any,
) -> ValidationIssues:
    issues = ValidationIssues()
    if not isinstance(response_body, Dict):
        return issues

    total_results = AttributeName(attr="totalresults").extract(response_body)
    if not isinstance(total_results, int):
        return issues

    resources = AttributeName(attr="resources").extract(response_body) or []
    if not isinstance(resources, List):
        return issues

    n_resources = len(resources)
    is_pagination = (count or 0) > 0 and total_results > n_resources
    if is_pagination:
        if AttributeName(attr="startindex").extract(response_body) is None:
            issues.add(
                issue=ValidationError.missing_required_attribute("startindex"),
                location=("startindex",),
                proceed=False,
            )
        if AttributeName(attr="itemsperpage").extract(response_body) is None:
            issues.add(
                issue=ValidationError.missing_required_attribute("itemsperpage"),
                location=("itemsperpage",),
                proceed=False,
            )
    return issues


def validate_start_index_consistency(
    start_index: int,
    response_body: Any,
) -> ValidationIssues:
    issues = ValidationIssues()

    if not isinstance(response_body, Dict):
        return issues

    start_index_body = AttributeName(attr="startindex").extract(response_body)
    if not isinstance(start_index_body, int):
        return issues

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


def validate_items_per_page_consistency(
    response_body: Any,
) -> ValidationIssues:
    issues = ValidationIssues()

    if not isinstance(response_body, Dict):
        return issues

    resources = AttributeName(attr="resources").extract(response_body)
    if not isinstance(resources, List):
        return issues

    items_per_page = AttributeName(attr="itemsperpage").extract(response_body)
    if not isinstance(items_per_page, int):
        return issues

    n_resources = len(resources)

    if items_per_page != n_resources:
        issues.add(
            issue=ValidationError.values_must_match(
                value_1="itemsperpage", value_2="numer of Resources"
            ),
            location=("itemsperpage",),
            proceed=True,
        )
        issues.add(
            issue=ValidationError.values_must_match(
                value_1="itemsperpage", value_2="numer of Resources"
            ),
            location=("resources",),
            proceed=True,
        )
    return issues


def validate_resources_schema(
    response_body: Any,
    schema: Schema,
) -> ValidationIssues:
    issues = ValidationIssues()
    if not isinstance(response_body, Dict):
        return issues

    resources = AttributeName(attr="resources").extract(response_body)
    if not isinstance(resources, List):
        return issues

    for i, resource in enumerate(resources):
        if not isinstance(resource, Dict):
            continue

        for attr_name in schema.top_level_attr_names:
            attr = schema.get_attr(attr_name)
            value = attr_name.extract(resource)
            issues.merge(
                issues=attr.validate(value, "RESPONSE"),
                location=("resources", i, attr.name),
            )
    return issues


def validate_resources_filtered(response_body: Any, filter_: Filter) -> ValidationIssues:
    issues = ValidationIssues()
    if not isinstance(response_body, Dict):
        return issues

    resources = AttributeName(attr="resources").extract(response_body) or []
    if not isinstance(resources, List):
        return issues

    for i, resource in enumerate(resources):
        if not isinstance(resource, Dict):
            continue

        if not filter_(resource):
            issues.add(
                issue=ValidationError.included_resource_does_not_match_filter(),
                proceed=True,
                location=("resources", i),
            )
    return issues


def validate_resources_schemas_field(response_body: Any, schema: Schema):
    issues = ValidationIssues()

    if not isinstance(response_body, Dict):
        return issues

    resources = AttributeName(attr="resources").extract(response_body)
    if not isinstance(resources, List):
        return issues

    for i, resource in enumerate(resources):
        issues.merge(
            issues=validate_schemas_field(resource, schema),
            location=("resources", i),
        )
    return issues


class ResourceTypeGET:
    def __init__(self, resource_schema: Schema):
        self._schema = LIST_RESPONSE
        self._resource_schema = resource_schema

    def validate_request(
        self,
        *,
        query_string: Any,
    ) -> ValidationIssues:
        issues = ValidationIssues()
        issues.merge(
            issues=validate_request_filtering(query_string, self._resource_schema, strict=False),
            location=("request", "query_string", "filter"),
        )
        issues.merge(
            issues=validate_request_sorting(query_string, self._resource_schema),
            location=("request", "query_string", "sortby"),
        )
        return issues

    def validate_response(
        self,
        *,
        status_code: int,
        response_body: Optional[Dict[str, Any]] = None,
        start_index: int = 1,
        count: Optional[int] = None,
        filter_: Optional[Filter] = None,
        sorter: Optional[Sorter] = None,
    ) -> ValidationIssues:
        issues = ValidationIssues()
        body_location = ("response", "body")
        issues.merge(
            issues=validate_body_existence(response_body),
            location=body_location,
        )
        issues.merge(
            issues=validate_body_type(response_body),
            location=body_location,
        )
        issues.merge(
            issues=validate_body_schema("RESPONSE", response_body, self._schema),
            location=body_location,
        )
        issues.merge(
            issues=validate_schemas_field(response_body, self._schema),
            location=body_location,
        )
        issues.merge(
            issues=validate_status_code(200, status_code),
            location=("response", "status"),
        )
        issues.merge(
            issues=validate_number_of_resources(count, response_body),
            location=body_location,
        )
        issues.merge(
            issues=validate_pagination_info(count, response_body),
            location=body_location,
        )
        issues.merge(
            issues=validate_start_index_consistency(start_index, response_body),
            location=body_location,
        )
        issues.merge(
            issues=validate_items_per_page_consistency(response_body),
            location=body_location,
        )
        issues.merge(
            issues=validate_resources_schema(response_body, self._resource_schema),
            location=body_location,
        )
        if filter_ is not None:
            issues.merge(
                issues=validate_resources_filtered(response_body, filter_),
                location=body_location,
            )
        issues.merge(
            issues=validate_resources_schemas_field(response_body, self._resource_schema),
            location=body_location,
        )
        if sorter is not None:
            issues.merge(
                issues=validate_resources_sorted(sorter, response_body),
                location=body_location,
            )
        return issues


def validate_resources_schemas_field_for_unknown_schema(
    response_body: Any,
    schemas: Iterable[Schema],
):
    issues = ValidationIssues()
    if not isinstance(response_body, Dict):
        return issues

    resources = AttributeName(attr="resources").extract(response_body) or []
    if not isinstance(resources, List):
        return issues

    all_schemas = []
    for schema in schemas:
        all_schemas.extend(schema.schemas)

    for i, resource in enumerate(resources):
        if not isinstance(resource, Dict):
            continue

        try:
            schemas_value = AttributeName(attr="schemas").extract(resource)
            for schema_value in schemas_value:
                if schema_value.lower() not in all_schemas:
                    issues.add(
                        issue=ValidationError.unknown_schema(schema_value),
                        proceed=True,
                        location=("resources", i, "schemas"),
                    )
        except (TypeError, AttributeError):
            pass

    return issues


class ServerRootResourceGET:
    def __init__(self, resource_schemas: Iterable[Schema]):
        self._schema = LIST_RESPONSE
        self._resource_schemas = resource_schemas

    def validate_request(
        self,
        *,
        query_string: Optional[Dict[str, Any]] = None,
    ) -> ValidationIssues:
        issues = ValidationIssues()
        issues.merge(
            issues=validate_request_filtering(query_string, schema=None, strict=False),
            location=("request", "query_string", "filter"),
        )
        issues.merge(
            issues=validate_request_sorting(query_string, None),
            location=("request", "query_string", "sortby"),
        )
        return issues

    def validate_response(
        self,
        *,
        status_code: int,
        response_body: Optional[Dict[str, Any]] = None,
        start_index: int = 1,
        count: Optional[int] = None,
        filter_: Optional[Filter] = None,
        sorter: Optional[Sorter] = None,
    ) -> ValidationIssues:
        issues = ValidationIssues()
        body_location = ("response", "body")
        issues.merge(
            issues=validate_body_existence(response_body),
            location=body_location,
        )
        issues.merge(
            issues=validate_body_type(response_body),
            location=body_location,
        )
        issues.merge(
            issues=validate_body_schema("RESPONSE", response_body, self._schema),
            location=body_location,
        )
        issues.merge(
            issues=validate_schemas_field(response_body, self._schema),
            location=body_location,
        )
        issues.merge(
            issues=validate_status_code(200, status_code),
            location=("response", "status"),
        )
        issues.merge(
            issues=validate_number_of_resources(count, response_body),
            location=body_location,
        )
        issues.merge(
            issues=validate_pagination_info(count, response_body),
            location=body_location,
        )
        issues.merge(
            issues=validate_start_index_consistency(start_index, response_body),
            location=body_location,
        )
        issues.merge(
            issues=validate_items_per_page_consistency(response_body),
            location=body_location,
        )
        if filter_ is not None:
            issues.merge(
                issues=validate_resources_filtered(response_body, filter_),
                location=body_location,
            )
        issues.merge(
            issues=validate_resources_schemas_field_for_unknown_schema(
                response_body, self._resource_schemas
            ),
            location=body_location,
        )
        if sorter is not None:
            issues.merge(
                issues=validate_resources_sorted(sorter, response_body),
                location=body_location,
            )
        return issues
