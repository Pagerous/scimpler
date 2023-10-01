from typing import Any, Dict, List, Optional

from src.parser.error import ValidationError
from src.parser.resource.validators.validator import (
    EndpointValidator,
    preprocess_response_validation,
    preprocess_request_validation,
)
from src.parser.resource.schemas import ErrorSchema


class _Error(EndpointValidator):
    def __init__(self):
        super().__init__(ErrorSchema())

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
                ValidationError.bad_type(dict, type(request_body)).with_location("body", "response")
            )
        else:
            errors.extend(self.validate_schemas_field(response_body, "RESPONSE"))

        for attr_name, attr in self._schema.attributes.items():
            errors.extend(
                [
                    error.with_location("body", "response")
                    for error in attr.validate(response_body.get(attr_name), "RESPONSE")
                ]
            )
        status_in_body = response_body.get("status")
        if str(status_code) != status_in_body:
            errors.append(
                ValidationError.error_status_mismatch(
                    str(status_code), status_in_body
                ).with_location("status", "body", "response")
            )
            errors.append(
                ValidationError.error_status_mismatch(
                    str(status_code), status_in_body
                ).with_location("status", "response")
            )
        if not 200 <= status_code < 600:
            errors.append(
                ValidationError.bad_error_status(status_code).with_location("status", "response")
            )
        return errors


ErrorGET = _Error
ErrorPOST = _Error
