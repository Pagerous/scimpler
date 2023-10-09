from typing import Any, Dict, Iterable, Optional

from src.parser.error import ValidationError, ValidationIssues
from src.parser.resource.validators.validator import (
    EndpointValidator,
    EndpointValidatorGET, preprocess_response_validation,
    preprocess_request_validation,
)
from src.parser.resource.schemas import ListResponseSchema, ResourceSchema, Schema


def _validate_resource_location_header(
    response_body: Dict[str, Any],
    response_headers: Optional[Dict[str, Any]],
    header_optional: bool
) -> ValidationIssues:
    issues = ValidationIssues()
    meta = response_body.get("meta")
    if isinstance(meta, dict):
        meta_location = meta.get("location")
    else:
        meta_location = None
    if "Location" not in (response_headers or {}):
        if not header_optional:
            issues.add(
                issue=ValidationError.missing_required_header("Location"),
                location=("response", "headers", "Location"),
                proceed=False,
            )

    elif meta_location != response_headers["Location"]:
        issues.add(
            issue=ValidationError.values_must_match(
                value_1="'Location' header", value_2="'meta.location' attribute",
            ),
            location=("response", "body", "meta", "location"),
            proceed=True,
        )
        issues.add(
            issue=ValidationError.values_must_match(
                value_1="'Location' header", value_2="'meta.location' attribute",
            ),
            location=("response", "headers", "Location"),
            proceed=True,
        )
    return issues


def _validate_resource_object_response(
    issues: ValidationIssues,
    schema: ResourceSchema,
    expected_status_code,
    actual_status_code: int,
    response_body: Dict[str, Any],
    response_headers: Dict[str, Any],
    is_location_header_optional: bool,
) -> ValidationIssues:
    meta = response_body.get("meta", {})
    if isinstance(meta, dict):
        resource_type = meta.get("resourcetype")
        if resource_type is not None and resource_type != repr(schema):
            issues.add(
                issue=ValidationError.resource_type_mismatch(
                    resource_type=repr(schema),
                    provided=resource_type,
                ),
                location=("response", "body", "meta", "resourceType"),
                proceed=True,
            )

    if issues.can_proceed(location=("response", "headers")):
        issues.merge(
            issues=_validate_resource_location_header(
                response_body=response_body,
                response_headers=response_headers,
                header_optional=is_location_header_optional,
            )
        )

    if actual_status_code != expected_status_code:
        issues.add(
            issue=ValidationError.bad_status_code(
                method="POST",
                expected=expected_status_code,
                provided=actual_status_code,
            ),
            location=("response", "status"),
            proceed=True,
        )

    return issues


class ResourceObjectGET(EndpointValidatorGET):
    def __init__(self, schema: ResourceSchema):
        super().__init__(schema)

    @preprocess_request_validation
    def validate_request(
        self,
        *,
        query_string: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
    ) -> ValidationIssues:
        return ValidationIssues()

    @preprocess_response_validation
    def validate_response(
        self,
        *,
        status_code: int,
        request_query_string: Optional[Dict[str, Any]] = None,
        request_body: Optional[Dict[str, Any]] = None,
        request_headers: Optional[Dict[str, Any]] = None,
        response_body: Optional[Dict[str, Any]] = None,
        response_headers: Optional[Dict[str, Any]] = None,
    ) -> ValidationIssues:
        issues = super().validate_response(
            status_code=status_code,
            request_query_string=request_query_string,
            request_body=request_body,
            request_headers=request_headers,
            response_body=response_body,
            response_headers=response_headers,
        )
        if issues.can_proceed(location=("response", "body")):
            _validate_resource_object_response(
                issues=issues,
                schema=self._schema,
                expected_status_code=200,
                actual_status_code=status_code,
                response_body=response_body,
                response_headers=response_headers,
                is_location_header_optional=True,
            )
        return issues


class ResourceTypePOST(EndpointValidator):
    def __init__(self, schema: ResourceSchema):
        super().__init__(schema)

    @preprocess_request_validation
    def validate_request(
        self,
        *,
        query_string: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
    ) -> ValidationIssues:
        issues = ValidationIssues()
        if not body:
            issues.add(
                location=("request", "body"),
                issue=ValidationError.missing("body"),
                proceed=False,
            )
        elif not isinstance(body, dict):
            issues.add(
                location=("request", "body"),
                issue=ValidationError.bad_type(expected_type=dict, provided_type=type(body)),
                proceed=False,
            )
        if issues.can_proceed(location=("request", "body")):
            for attr_name, attr in self._schema.attributes.items():
                issues.merge(
                    issues=attr.validate(body.get(attr_name), "REQUEST"),
                    location=("request", "body", attr.name)
                )
        return issues

    @preprocess_response_validation
    def validate_response(
        self,
        *,
        status_code: int,
        request_query_string: Optional[Dict[str, Any]] = None,
        request_body: Optional[Dict[str, Any]] = None,
        request_headers: Optional[Dict[str, Any]] = None,
        response_body: Optional[Dict[str, Any]] = None,
        response_headers: Optional[Dict[str, Any]] = None,
    ) -> ValidationIssues:
        issues = ValidationIssues()
        if not response_body:
            return issues  # TODO: warn missing response body

        if not isinstance(response_body, dict):
            issues.add(
                issue=ValidationError.bad_type(dict, type(response_body)),
                location=("response", "body"),
                proceed=False,
            )

        if issues.can_proceed(location=("response", "body")):
            issues.merge(
                issues=self.validate_schema(body=response_body, direction="RESPONSE"),
                location=("response", "body"),
            )

            _validate_resource_object_response(
                issues=issues,
                schema=self._schema,
                expected_status_code=201,
                actual_status_code=status_code,
                response_body=response_body,
                response_headers=response_headers,
                is_location_header_optional=False,
            )

        return issues


class _ManyResourcesGET(EndpointValidatorGET):
    @preprocess_request_validation
    def validate_request(
        self,
        *,
        query_string: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
    ) -> ValidationIssues:
        return ValidationIssues()

    @preprocess_response_validation
    def validate_response(
        self,
        *,
        status_code: int,
        request_query_string: Dict[str, Any] = None,
        request_body: Dict[str, Any] = None,
        request_headers: Dict[str, Any] = None,
        response_body: Dict[str, Any] = None,
        response_headers: Dict[str, Any] = None,
    ) -> ValidationIssues:
        issues = super().validate_response(
            status_code=status_code,
            request_query_string=request_query_string,
            request_body=request_body,
            request_headers=request_headers,
            response_body=response_body,
            response_headers=response_headers,
        )

        if status_code != 200:
            issues.add(
                issue=ValidationError.bad_status_code(
                    method="GET", expected=200, provided=status_code
                ),
                location=("response", "status"),
                proceed=True,
            )

        if not issues.can_proceed(location=("response", "body")):
            return issues

        start_index = request_query_string.get("startindex", 1)
        if start_index < 1:
            start_index = 1
        count = request_query_string.get("count")
        if count is not None and count < 0:
            count = 0

        if (
            issues.can_proceed(location=("response", "body", "totalResults"))
            and issues.can_proceed(location=("response", "body", "Resources"))
        ):
            total_results = response_body["totalresults"]
            resources = response_body.get("resources", [])
            n_resources = len(resources)

            if total_results < n_resources:
                issues.add(
                    issue=ValidationError.total_results_mismatch(
                        total_results=total_results, n_resources=n_resources
                    ),
                    location=("response", "body", "totalResults"),
                    proceed=True,
                )
                issues.add(
                    issue=ValidationError.total_results_mismatch(
                        total_results=total_results, n_resources=n_resources
                    ),
                    location=("response", "body", "Resources"),
                    proceed=True,
                )

            if count is None and total_results > n_resources:
                issues.add(
                    issue=ValidationError.too_little_results(
                        must="be equal to 'totalResults'"
                    ),
                    location=("response", "body", "Resources"),
                    proceed=True,
                )

            if count is not None and count < n_resources:
                issues.add(
                    issue=ValidationError.too_many_results(
                        must="be lesser or equal to 'count' parameter"
                    ),
                    location=("response", "body", "Resources"),
                    proceed=True,
                )

            if (
                issues.can_proceed(location=("response", "body", "startIndex"))
                and issues.can_proceed(location=("response", "body", "itemsPerPage"))
            ):
                is_pagination = (count or 0) > 0 and total_results > n_resources
                if is_pagination:
                    if "startindex" not in response_body:
                        issues.add(
                            issue=ValidationError.missing_required_attribute("startIndex"),
                            location=("response", "body", "startIndex"),
                            proceed=False,
                        )
                    if "itemsperpage" not in response_body:
                        issues.add(
                            issue=ValidationError.missing_required_attribute("itemsPerPage"),
                            location=("response", "body", "itemsPerPage"),
                            proceed=False,
                        )

        if (
            issues.can_proceed(location=("response", "body", "startIndex"))
            and "startindex" in response_body
            and response_body["startindex"] > start_index
        ):
            issues.add(
                issue=ValidationError.response_value_does_not_correspond_to_parameter(
                    response_key="startIndex",
                    response_value=response_body["startindex"],
                    query_param_name="startIndex",
                    query_param_value=start_index,
                    reason="bigger value than requested",
                ),
                location=("response", "body", "startIndex"),
                proceed=True,
            )

        if (
            issues.can_proceed(location=("response", "body", "itemsPerPage"))
            and issues.can_proceed(location=("response", "body", "Resources"))
        ):
            n_resources = len(response_body.get("resources", []))

            if "itemsperpage" in response_body and response_body["itemsperpage"] != n_resources:
                issues.add(
                    issue=ValidationError.values_must_match(
                        value_1="itemsPerPage", value_2="numer of Resources"
                    ),
                    location=("response", "body", "itemsPerPage"),
                    proceed=True,
                )
                issues.add(
                    issue=ValidationError.values_must_match(
                        value_1="itemsPerPage", value_2="numer of Resources"
                    ),
                    location=("response", "body", "Resources"),
                    proceed=True,
                )

        return issues


class ResourceTypeGET(_ManyResourcesGET):
    def __init__(self, resource_schema: Schema):
        super().__init__(ListResponseSchema())
        self._resource_schema = resource_schema

    @preprocess_response_validation
    def validate_response(
        self,
        *,
        status_code: int,
        request_query_string: Optional[Dict[str, Any]] = None,
        request_body: Optional[Dict[str, Any]] = None,
        request_headers: Optional[Dict[str, Any]] = None,
        response_body: Optional[Dict[str, Any]] = None,
        response_headers: Optional[Dict[str, Any]] = None,
    ) -> ValidationIssues:
        issues = super().validate_response(
            status_code=status_code,
            request_query_string=request_query_string,
            request_body=request_body,
            request_headers=request_headers,
            response_body=response_body,
            response_headers=response_headers,
        )

        if issues.can_proceed(location=("response", "body", "Resources")):
            resources = response_body.get("resources", [])
            for i, resource in enumerate(resources):
                for attr_name, attr in self._resource_schema.attributes.items():
                    issues.merge(
                        issues=attr.validate(resource.get(attr_name), "RESPONSE"),
                        location=("response", "body", "Resources", i, attr.name),
                    )
        return issues


class ServerRootResourceGET(_ManyResourcesGET):
    def __init__(self, resource_schemas: Iterable[Schema]):
        super().__init__(ListResponseSchema())
        self._resource_schemas = resource_schemas

    @preprocess_response_validation
    def validate_response(
        self,
        *,
        status_code: int,
        request_query_string: Optional[Dict[str, Any]] = None,
        request_body: Optional[Dict[str, Any]] = None,
        request_headers: Optional[Dict[str, Any]] = None,
        response_body: Optional[Dict[str, Any]] = None,
        response_headers: Optional[Dict[str, Any]] = None,
    ) -> ValidationIssues:
        issues = super().validate_response(
            status_code=status_code,
            request_query_string=request_query_string,
            request_body=request_body,
            request_headers=request_headers,
            response_body=response_body,
            response_headers=response_headers,
        )
        if not issues.can_proceed():
            return issues

        # TODO: validate according to 'attributes' and  whether they exists in all provided schemas
        return issues