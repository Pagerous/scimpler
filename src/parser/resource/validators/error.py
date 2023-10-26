from typing import Any, Dict, Optional

from src.parser.error import ValidationError, ValidationIssues
from src.parser.resource.schemas import ERROR
from src.parser.resource.validators.validator import (
    EndpointValidator,
    EndpointValidatorGET,
    preprocess_request_validation,
    preprocess_response_validation,
)


class _Error(EndpointValidatorGET):
    def __init__(self):
        super().__init__(ERROR)

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

        if issues.can_proceed(("response", "body")):
            status_in_body = response_body.get("status")
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

        if not 200 <= status_code < 600:
            issues.add(
                issue=ValidationError.bad_error_status(status_code),
                location=("response", "status"),
                proceed=True,
            )

        return issues


ErrorGET = _Error
ErrorPOST = _Error
