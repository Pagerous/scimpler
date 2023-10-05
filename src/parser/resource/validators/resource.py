from typing import Any, Dict, Optional

from src.parser.error import ValidationError, ValidationIssues
from src.parser.resource.validators.validator import (
    EndpointValidator,
    EndpointValidatorGET, preprocess_response_validation,
    preprocess_request_validation,
)
from src.parser.resource.schemas import ResourceSchema


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


def _validate_resource_response(
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


class ResourcePOST(EndpointValidator):
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

            _validate_resource_response(
                issues=issues,
                schema=self._schema,
                expected_status_code=201,
                actual_status_code=status_code,
                response_body=response_body,
                response_headers=response_headers,
                is_location_header_optional=False,
            )

        return issues


class ResourceGET(EndpointValidatorGET):
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
            _validate_resource_response(
                issues=issues,
                schema=self._schema,
                expected_status_code=200,
                actual_status_code=status_code,
                response_body=response_body,
                response_headers=response_headers,
                is_location_header_optional=True,
            )
        return issues
