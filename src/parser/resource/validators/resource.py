from typing import Any, Dict, List, Optional

from src.parser.error import ValidationError
from src.parser.resource.validators.validator import (
    EndpointValidator,
    preprocess_response_validation,
    preprocess_request_validation,
)
from src.parser.resource.schemas import ResourceSchema


def _validate_resource_location_header(
    response_body: Dict[str, Any],
    response_headers: Optional[Dict[str, Any]],
    header_optional: bool
) -> List[ValidationError]:
    errors = []
    meta = response_body.get("meta")
    if isinstance(meta, dict):
        meta_location = meta.get("location")
    else:
        meta_location = None
    if "Location" not in (response_headers or {}):
        if not header_optional:
            errors.append(
                ValidationError.missing_required_header("Location").with_location("headers", "response")
            )
    elif meta_location != response_headers["Location"]:
        errors.append(
            ValidationError.values_must_match(
                value_1="'Location' header", value_2="'meta.location' attribute"
            ).with_location("location", "meta", "body", "response")
        )
        errors.append(
            ValidationError.values_must_match(
                value_1="'Location' header", value_2="'meta.location' attribute"
            ).with_location("headers", "response")
        )
    return errors


def _validate_resource_response(
    schema: ResourceSchema,
    expected_status_code,
    actual_status_code: int,
    response_body: Dict[str, Any],
    response_headers: Dict[str, Any],
    is_location_header_optional: bool,
) -> List[ValidationError]:
    errors = []
    for attr_name, attr in schema.attributes.items():
        errors.extend(
            [
                error.with_location("body", "response")
                for error in attr.validate(response_body.get(attr_name), "RESPONSE")
            ]
        )
    meta = response_body.get("meta", {})
    if isinstance(meta, dict):
        resource_type = meta.get("resourcetype")
        if resource_type is not None and resource_type != repr(schema):
            errors.append(
                ValidationError.resource_type_mismatch(
                    resource_type=repr(schema), provided=resource_type)
                .with_location("resourceType", "meta", "body", "response")
            )
    errors.extend(
        _validate_resource_location_header(
            response_body=response_body,
            response_headers=response_headers,
            header_optional=is_location_header_optional,
        )
    )
    if actual_status_code != expected_status_code:
        errors.append(
            ValidationError.bad_status_code(
                "POST", expected_status_code, actual_status_code
            ).with_location("status", "response")
        )
    return errors


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
    ) -> List[ValidationError]:
        errors = []
        if not body:
            errors.append(ValidationError.missing("body"))
        elif not isinstance(body, dict):
            errors.append(
                ValidationError.bad_type(dict, type(body)).with_location("body", "request")
            )
        else:
            errors.extend(self.validate_schemas_field(body, "REQUEST"))

        if errors:
            return errors

        for attr_name, attr in self._schema.attributes.items():
            errors.extend(
                [
                    error.with_location("body", "request")
                    for error in attr.validate(body.get(attr_name), "REQUEST")
                ]
            )
        return errors

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
    ) -> List[ValidationError]:
        if not response_body:
            return []  # TODO: warn missing response body
        errors = []
        if not isinstance(response_body, dict):
            errors.append(
                ValidationError.bad_type(dict, type(response_body)).with_location("body", "response")
            )
        else:
            errors.extend(self.validate_schemas_field(response_body, "RESPONSE"))

        if errors:
            return errors

        errors.extend(
            _validate_resource_response(
                schema=self._schema,
                expected_status_code=201,
                actual_status_code=status_code,
                response_body=response_body,
                response_headers=response_headers,
                is_location_header_optional=False,
            )
        )

        return errors


class ResourceGET(EndpointValidator):
    def __init__(self, schema: ResourceSchema):
        super().__init__(schema)

    @preprocess_request_validation
    def validate_request(
        self,
        *,
        query_string: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
    ) -> List[ValidationError]:
        return []

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
    ) -> List[ValidationError]:
        errors = []
        if not response_body:
            errors.append(ValidationError.missing("body").with_location("body", "response"))

        elif not isinstance(response_body, dict):
            errors.append(
                ValidationError.bad_type(dict, type(response_body)).with_location("body", "response")
            )
        else:
            errors.extend(self.validate_schemas_field(response_body, "RESPONSE"))

        if errors:
            return errors

        errors.extend(
            _validate_resource_response(
                schema=self._schema,
                expected_status_code=200,
                actual_status_code=status_code,
                response_body=response_body,
                response_headers=response_headers,
                is_location_header_optional=True,
            )
        )

        return errors
