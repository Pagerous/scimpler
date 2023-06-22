from typing import Any, Dict, List, Optional, Tuple

from src.parser.attributes.common import schemas
from src.parser.error import ValidationError
from src.parser.schemas.schemas import Schema, ErrorSchema


class SchemaValidator:
    def __init__(self, schemas_mapping: Dict[Tuple[str], Schema]):
        self._schemas_mapping = schemas_mapping

    @staticmethod
    def _preprocess_body(body: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if body is None:
            return None
        body_processed = {k.lower(): v for k, v in body.items()}
        if len(body_processed) < len(body):
            ...  # TODO: warn here
        return body_processed

    @staticmethod
    def _validate_schemas_field(http_method, body: Optional[Dict[str, Any]], direction: str):
        validation_errors = []
        if "schemas" not in (body or {}):
            validation_errors.append(
                ValidationError.missing_required_attribute(
                    "schemas").with_location("schemas", "body", direction.lower())
            )
            return validation_errors
        validation_errors.extend(
            [
                error.with_location("body", direction.lower())
                for error in schemas.validate(body["schemas"], http_method, direction)
            ]
        )
        return validation_errors

    def validate_request(
        self,
        http_method: str,
        query_string: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
    ):
        body = self._preprocess_body(body)
        if http_method == "POST":
            if not body:
                return [ValidationError.missing("body")]
            validation_errors = self._validate_schemas_field(http_method, body, "REQUEST")
            if validation_errors:
                return validation_errors
            schema = self._schemas_mapping.get(tuple(body["schemas"]))
            if schema is None:
                # TODO: warn schema not recognized
                return []
            return self._validate_post_request(
                schema=schema,
                query_string=query_string,
                body=body,
                headers=headers
            )
        elif http_method == "GET":
            return []  # no validation for now
        return []

    def validate_response(
        self,
        http_method: str,
        status_code: int,
        request_query_string: Optional[Dict[str, Any]] = None,
        request_body: Optional[Dict[str, Any]] = None,
        request_headers: Optional[Dict[str, Any]] = None,
        response_body: Optional[Dict[str, Any]] = None,
        response_headers: Optional[Dict[str, Any]] = None,
    ):
        schema = None
        response_body = self._preprocess_body(response_body)
        request_body = self._preprocess_body(request_body)
        validation_errors = []
        if response_body is None:
            if http_method in ["POST"]:
                pass  # TODO: warn missing response body
            elif http_method in ["GET"]:
                validation_errors.append(ValidationError.missing("body").with_location("body", "response"))
                return validation_errors
        else:
            validation_errors.extend(self._validate_schemas_field(http_method, response_body, "RESPONSE"))
            if validation_errors:
                return validation_errors
            schema = self._schemas_mapping.get(tuple(response_body["schemas"]))

        if schema is None:
            # TODO: warn schema not recognized
            return []

        if isinstance(schema, ErrorSchema):
            if not 200 <= status_code < 600:
                validation_errors.append(
                    ValidationError.bad_error_status(status_code).with_location("status", "response")
                )

            if status_code != int(response_body["status"]):
                validation_errors.append(
                    ValidationError.error_status_mismatch(
                        status_code, int(response_body["status"])
                    ).with_location("status", "body", "response")
                )
                validation_errors.append(
                    ValidationError.error_status_mismatch(
                        status_code, int(response_body["status"])
                    ).with_location("status", "response")
                )
            validation_errors.extend(schema.validate_response(http_method, request_body, response_body))
        else:
            if http_method == "POST":
                return self._validate_post_response(
                    schema=schema,
                    request_query_string=request_query_string,
                    request_body=request_body,
                    request_headers=request_headers,
                    response_body=response_body,
                    response_headers=response_headers,
                    status_code=status_code,
                )
            elif http_method == "GET":
                return self._validate_get_response(
                    schema=schema,
                    request_query_string=request_query_string,
                    request_body=request_body,
                    request_headers=request_headers,
                    response_body=response_body,
                    response_headers=response_headers,
                    status_code=status_code,
                )

        return validation_errors

    @staticmethod
    def _validate_post_request(
        schema: Schema,
        query_string: Optional[Dict[str, Any]],
        body: Optional[Dict[str, Any]],
        headers: Optional[Dict[str, Any]],
    ):
        return schema.validate_request("POST", body)

    def _validate_post_response(
        self,
        schema: Schema,
        response_body: Dict[str, Any],
        request_query_string: Optional[Dict[str, Any]],
        request_body: Optional[Dict[str, Any]],
        request_headers: Optional[Dict[str, Any]],

        response_headers: Optional[Dict[str, Any]],
        status_code: int
    ):
        validation_errors = schema.validate_response("POST", request_body, response_body)
        validation_errors.extend(
            self._validate_location_header(
                response_body=response_body,
                response_headers=response_headers,
                header_optional=False,
            )
        )
        if status_code != 201:
            validation_errors.append(
                ValidationError.bad_status_code("POST", 201, status_code).with_location("status", "response")
            )
        return validation_errors

    def _validate_get_response(
        self,
        schema: Schema,
        response_body: Dict[str, Any],
        request_query_string: Optional[Dict[str, Any]],
        request_body: Optional[Dict[str, Any]],
        request_headers: Optional[Dict[str, Any]],

        response_headers: Optional[Dict[str, Any]],
        status_code: int
    ):
        validation_errors = schema.validate_response("GET", request_body, response_body)
        validation_errors.extend(
            self._validate_location_header(
                response_body=response_body,
                response_headers=response_headers,
                header_optional=True,
            )
        )
        if status_code != 200:
            validation_errors.append(
                ValidationError.bad_status_code("GET", 200, status_code).with_location("status", "response")
            )
        return validation_errors

    @staticmethod
    def _validate_location_header(
        response_body: Dict[str, Any], response_headers: Optional[Dict[str, Any]], header_optional: bool
    ) -> List[ValidationError]:
        validation_errors = []
        meta = response_body.get("meta")
        if isinstance(meta, dict):
            meta_location = meta.get("location")
        else:
            meta_location = None
        if "Location" not in (response_headers or {}):
            if not header_optional:
                validation_errors.append(
                    ValidationError.missing_required_header("Location").with_location("headers", "response")
                )
            else:
                return validation_errors
        elif meta_location != response_headers["Location"]:
            validation_errors.append(
                ValidationError.values_must_match(
                    value_1="'Location' header", value_2="'meta.location' attribute"
                ).with_location("location", "meta", "body", "response")
            )
            validation_errors.append(
                ValidationError.values_must_match(
                    value_1="'Location' header", value_2="'meta.location' attribute"
                ).with_location("headers", "response")
            )
        return validation_errors

