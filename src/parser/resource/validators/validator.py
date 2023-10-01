import abc
from functools import wraps
from typing import Any, Dict, List, Optional, TypeVar

from src.parser.attributes.common import schemas as schemas_field
from src.parser.error import ValidationError
from src.parser.resource.schemas import Schema


TSchema = TypeVar("TSchema", bound=Schema)


class EndpointValidator(abc.ABC):
    def __init__(self, schema: TSchema):
        self._schema = schema

    @abc.abstractmethod
    def validate_request(
        self,
        *,
        query_string: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
    ) -> List[ValidationError]:
        ...

    @abc.abstractmethod
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
        ...

    def validate_schemas_field(
        self,
        body: Dict[str, Any],
        direction: str,
    ) -> List[ValidationError]:
        errors = []
        if "schemas" not in body:
            errors.append(
                ValidationError.missing_required_attribute(
                    "schemas").with_location("schemas", "body", direction.lower())
            )
        elif body["schemas"] != self._schema.schemas:
            errors.append(
                ValidationError.schemas_mismatch(repr(self._schema))
            )
        else:
            errors.extend(
                [
                    error.with_location("body", direction.lower())
                    for error in schemas_field.validate(body["schemas"], direction)
                ]
            )
        return errors


def _lower_dict_keys(d: dict) -> dict:
    d_lowered = {}
    for k, v in d.items():
        if isinstance(v, list):
            d_lowered[k.lower()] = [_lower_dict_keys(i) if isinstance(i, dict) else i for i in v ]
        elif isinstance(v, dict):
            d_lowered[k.lower()] = _lower_dict_keys(v)
        else:
            d_lowered[k.lower()] = v
    return d_lowered


def _preprocess_body(body: Optional[Any]):
    if body is None:
        return {}
    if isinstance(body, dict):
        body = _lower_dict_keys(body)
    return body


def _preprocess_dict(d: Optional[Any]):
    return d or {}


def preprocess_request_validation(func):

    @wraps(func)
    def wrapper(
        self,
        *,
        query_string: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
    ) -> List[ValidationError]:
        body = _preprocess_body(body)
        query_string = _preprocess_dict(query_string)
        headers = _preprocess_dict(headers)
        return func(
            self,
            query_string=query_string,
            body=body,
            headers=headers
        )

    return wrapper


def preprocess_response_validation(func):

    @wraps(func)
    def wrapper(
        self,
        *,
        status_code: int,
        request_query_string: Optional[Dict[str, Any]] = None,
        request_body: Optional[Dict[str, Any]] = None,
        request_headers: Optional[Dict[str, Any]] = None,
        response_body: Optional[Dict[str, Any]] = None,
        response_headers: Optional[Dict[str, Any]] = None,
    ) -> List[ValidationError]:
        request_body = _preprocess_body(request_body)
        response_body = _preprocess_body(response_body)
        request_query_string = _preprocess_dict(request_query_string)
        request_headers = _preprocess_dict(request_headers)
        response_headers = _preprocess_dict(response_headers)
        return func(
            self,
            status_code=status_code,
            request_query_string=request_query_string,
            request_body=request_body,
            request_headers=request_headers,
            response_body=response_body,
            response_headers=response_headers,
        )

    return wrapper
