from typing import Any, Dict, List, Optional, Sequence

from src.parser.attributes.attributes import extract
from src.parser.error import ValidationError, ValidationIssues
from src.parser.parameters.filter.filter import Filter
from src.parser.parameters.sorter import Sorter
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
    body: Any,
    schema: Schema,
) -> ValidationIssues:
    issues = ValidationIssues()
    if not isinstance(body, Dict):
        return issues

    for attr_name in schema.top_level_attr_names:
        attr = schema.get_attr(attr_name)
        value = extract(attr_name, body)
        issues.merge(
            issues=attr.validate(value),
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
    body = {k: v for k, v in body.items() if isinstance(k, str)}

    schemas_value = extract("schemas", body)
    if not isinstance(schemas_value, List):
        return issues

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

    def validate_response(
        self,
        *,
        status_code: int,
        body: Any,
    ) -> ValidationIssues:
        issues = ValidationIssues()
        body_location = ("response", "body")
        issues.merge(
            issues=validate_body_existence(body),
            location=body_location,
        )
        issues.merge(
            issues=validate_body_type(body),
            location=body_location,
        )
        issues.merge(
            issues=validate_body_schema(body, self._schema),
            location=body_location,
        )
        issues.merge(
            issues=validate_schemas_field(body, self._schema),
            location=body_location,
        )
        issues.merge(issues=validate_error_status_code_consistency(body, status_code))
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


class ResourceObjectGET:
    def __init__(self, schema: ResourceSchema):
        self._schema = schema

    def validate_response(
        self,
        *,
        status_code: int,
        body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
    ) -> ValidationIssues:
        issues = ValidationIssues()
        body_location = ("response", "body")
        issues.merge(
            issues=validate_body_existence(body),
            location=body_location,
        )
        issues.merge(
            issues=validate_body_type(body),
            location=body_location,
        )
        issues.merge(
            issues=validate_body_schema(body, self._schema),
            location=body_location,
        )
        issues.merge(
            issues=validate_schemas_field(body, self._schema),
            location=body_location,
        )
        issues.merge(
            issues=validate_resource_location_in_header(headers, False),
            location=("response", "headers"),
        )
        issues.merge(
            issues=validate_resource_type_consistency(body, self._schema),
            location=body_location,
        )
        issues.merge(
            issues=validate_resource_location_consistency(body, headers),
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
            issues=validate_body_schema(body, self._schema),
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
        body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
    ) -> ValidationIssues:
        issues = ValidationIssues()
        if not body:
            return issues  # TODO: warn missing response body

        body_location = ("response", "body")
        issues.merge(
            issues=validate_body_type(body),
            location=body_location,
        )
        issues.merge(
            issues=validate_body_schema(body, self._schema),
            location=body_location,
        )
        issues.merge(
            issues=validate_resource_location_in_header(headers, True),
            location=("response", "headers"),
        )
        issues.merge(
            issues=validate_resource_type_consistency(body, self._schema),
            location=body_location,
        )
        issues.merge(
            issues=validate_resource_location_consistency(body, headers),
        )
        issues.merge(
            issues=validate_status_code(201, status_code),
            location=("response", "status"),
        )
        issues.merge(
            issues=validate_schemas_field(body, self._schema),
            location=body_location,
        )
        return issues


def validate_request_sorting(query_string: Any) -> ValidationIssues:
    issues = ValidationIssues()
    if not isinstance(query_string, Dict):
        return issues

    sort_by = query_string.get("sortBy")
    if not isinstance(sort_by, str):
        return issues

    sort_order = query_string.get("sortOrder", "ascending")
    if sort_order not in ["ascending", "descending"]:
        pass  # TODO add warning here

    _, issues_ = Sorter.parse(by=sort_by, asc=sort_order == "ascending")
    return issues_


def validate_request_filtering(query_string: Any) -> ValidationIssues:
    issues = ValidationIssues()
    if not isinstance(query_string, Dict):
        return issues

    filter_exp = query_string.get("filter")
    if isinstance(filter_exp, str):
        _, issues_ = Filter.parse(filter_exp)
        issues = issues_
    return issues


def validate_resources_sorted(
    sorter: Sorter,
    body: Any,
    schemas: Sequence[Schema],
) -> ValidationIssues:
    issues = ValidationIssues()
    if not isinstance(body, Dict):
        return issues

    resources = extract("resources", body)
    if not isinstance(resources, List):
        return issues

    schema = schemas[0] if len(schemas) == 1 else None

    try:
        if schema is None:
            schema = [infer_schema_from_data(resource, schemas) for resource in resources]
            if not (schema and all(schema)):
                return issues

        if resources != sorter(resources, schema=schema):
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
    body: Any,
) -> ValidationIssues:
    issues = ValidationIssues()
    if not isinstance(body, Dict):
        return issues

    total_results = extract("totalresults", body)
    if not isinstance(total_results, int):
        return issues

    resources = extract("resources", body)
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
    body: Any,
) -> ValidationIssues:
    issues = ValidationIssues()
    if not isinstance(body, Dict):
        return issues

    total_results = extract("totalresults", body)
    if not isinstance(total_results, int):
        return issues

    resources = extract("resources", body)
    if not isinstance(resources, List):
        return issues

    n_resources = len(resources)
    is_pagination = (count or 0) > 0 and total_results > n_resources
    if is_pagination:
        if extract("startindex", body) is None:
            issues.add(
                issue=ValidationError.missing_required_attribute("startindex"),
                location=("startindex",),
                proceed=False,
            )
        if extract("itemsperpage", body) is None:
            issues.add(
                issue=ValidationError.missing_required_attribute("itemsperpage"),
                location=("itemsperpage",),
                proceed=False,
            )
    return issues


def validate_start_index_consistency(
    start_index: int,
    body: Any,
) -> ValidationIssues:
    issues = ValidationIssues()

    if not isinstance(body, Dict):
        return issues

    start_index_body = extract("startindex", body)
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
    body: Any,
) -> ValidationIssues:
    issues = ValidationIssues()

    if not isinstance(body, Dict):
        return issues

    resources = extract("resources", body)
    if not isinstance(resources, List):
        return issues

    items_per_page = extract("itemsperpage", body)
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
    body: Any,
    schemas: Sequence[Schema],
) -> ValidationIssues:
    issues = ValidationIssues()
    if not isinstance(body, Dict):
        return issues

    resources = extract("resources", body)
    if not isinstance(resources, List):
        return issues

    schema = schemas[0] if len(schemas) == 1 else None

    for i, resource in enumerate(resources):
        if not isinstance(resource, Dict):
            continue

        if schema is None:
            schema = infer_schema_from_data(resource, schemas)

        if schema is None:
            continue

        for attr_name in schema.top_level_attr_names:
            attr = schema.get_attr(attr_name)
            value = extract(attr_name, resource)
            issues.merge(
                issues=attr.validate(value),
                location=("resources", i, attr.name),
            )
    return issues


def validate_resources_filtered(
    body: Any, filter_: Filter, schemas: Sequence[Schema], strict: bool
) -> ValidationIssues:
    issues = ValidationIssues()
    if not isinstance(body, Dict):
        return issues

    resources = extract("resources", body)
    if not isinstance(resources, List):
        return issues

    schema = schemas[0] if len(schemas) == 1 else None

    for i, resource in enumerate(resources):
        if not isinstance(resource, Dict):
            continue

        if schema is None:
            schema = infer_schema_from_data(resource, schemas)

        if schema is None:
            continue

        if not filter_(resource, schema, strict):
            issues.add(
                issue=ValidationError.included_resource_does_not_match_filter(),
                proceed=True,
                location=("resources", i),
            )
    return issues


def validate_resources_schemas_field(body: Any, schemas: Sequence[Schema]):
    issues = ValidationIssues()

    if not isinstance(body, Dict):
        return issues

    resources = extract("resources", body)
    if not isinstance(resources, List):
        return issues

    schema = schemas[0] if len(schemas) == 1 else None

    for i, resource in enumerate(resources):
        if schema is None:
            schema = infer_schema_from_data(resource, schemas)

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
            issues=validate_request_filtering(query_string),
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
        body: Optional[Dict[str, Any]] = None,
        start_index: int = 1,
        count: Optional[int] = None,
        filter_: Optional[Filter] = None,
        sorter: Optional[Sorter] = None,
    ) -> ValidationIssues:
        issues = ValidationIssues()
        body_location = ("response", "body")
        issues.merge(
            issues=validate_body_existence(body),
            location=body_location,
        )
        issues.merge(
            issues=validate_body_type(body),
            location=body_location,
        )
        issues.merge(
            issues=validate_body_schema(body, self._schema),
            location=body_location,
        )
        issues.merge(
            issues=validate_schemas_field(body, self._schema),
            location=body_location,
        )
        issues.merge(
            issues=validate_status_code(200, status_code),
            location=("response", "status"),
        )
        issues.merge(
            issues=validate_number_of_resources(count, body),
            location=body_location,
        )
        issues.merge(
            issues=validate_pagination_info(count, body),
            location=body_location,
        )
        issues.merge(
            issues=validate_start_index_consistency(start_index, body),
            location=body_location,
        )
        issues.merge(
            issues=validate_items_per_page_consistency(body),
            location=body_location,
        )
        issues.merge(
            issues=validate_resources_schemas_field(body, [self._resource_schema]),
            location=body_location,
        )
        issues.merge(
            issues=validate_resources_schema(body, [self._resource_schema]),
            location=body_location,
        )
        if filter_ is not None:
            issues.merge(
                issues=validate_resources_filtered(body, filter_, [self._resource_schema], False),
                location=body_location,
            )
        if sorter is not None:
            issues.merge(
                issues=validate_resources_sorted(sorter, body, [self._resource_schema]),
                location=body_location,
            )
        return issues


def infer_schema_from_data(data: Dict[str, Any], schemas: Sequence[Schema]) -> Optional[Schema]:
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

    def validate_request(
        self,
        *,
        query_string: Optional[Dict[str, Any]] = None,
    ) -> ValidationIssues:
        issues = ValidationIssues()
        issues.merge(
            issues=validate_request_filtering(query_string),
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
        body: Optional[Dict[str, Any]] = None,
        start_index: int = 1,
        count: Optional[int] = None,
        filter_: Optional[Filter] = None,
        sorter: Optional[Sorter] = None,
    ) -> ValidationIssues:
        issues = ValidationIssues()
        body_location = ("response", "body")
        issues.merge(
            issues=validate_body_existence(body),
            location=body_location,
        )
        issues.merge(
            issues=validate_body_type(body),
            location=body_location,
        )
        issues.merge(
            issues=validate_body_schema(body, self._schema),
            location=body_location,
        )
        issues.merge(
            issues=validate_schemas_field(body, self._schema),
            location=body_location,
        )
        issues.merge(
            issues=validate_status_code(200, status_code),
            location=("response", "status"),
        )
        issues.merge(
            issues=validate_number_of_resources(count, body),
            location=body_location,
        )
        issues.merge(
            issues=validate_pagination_info(count, body),
            location=body_location,
        )
        issues.merge(
            issues=validate_start_index_consistency(start_index, body),
            location=body_location,
        )
        issues.merge(
            issues=validate_items_per_page_consistency(body),
            location=body_location,
        )
        issues.merge(
            issues=validate_resources_schemas_field(body, self._resource_schemas),
            location=body_location,
        )
        issues.merge(
            issues=validate_resources_schema(body, self._resource_schemas),
            location=body_location,
        )
        if filter_ is not None:
            issues.merge(
                issues=validate_resources_filtered(body, filter_, self._resource_schemas, False),
                location=body_location,
            )
        if sorter is not None:
            issues.merge(
                issues=validate_resources_sorted(sorter, body, self._resource_schemas),
                location=body_location,
            )
        return issues
