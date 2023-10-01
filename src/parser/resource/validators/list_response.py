from typing import Any, Dict, Iterable, List, Optional

from src.parser.error import ValidationError
from src.parser.resource.validators.validator import (
    EndpointValidator,
    preprocess_response_validation,
    preprocess_request_validation,
)
from src.parser.resource.schemas import ListResponseSchema, Schema


class _ListResponseGET(EndpointValidator):
    @preprocess_request_validation
    def validate_request(
        self,
        *,
        query_string: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
    ) -> List[ValidationError]:
        return []

    def validate_response(
        self,
        *,
        status_code: int,
        request_query_string: Dict[str, Any] = None,
        request_body: Dict[str, Any] = None,
        request_headers: Dict[str, Any] = None,
        response_body: Dict[str, Any] = None,
        response_headers: Dict[str, Any] = None,
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

        if errors:
            return errors

        for attr_name, attr in self._schema.attributes.items():
            errors.extend(
                [
                    error.with_location("body", "response")
                    for error in attr.validate(response_body.get(attr_name), "RESPONSE")
                ]
            )

        if errors:
            return errors

        start_index = request_query_string.get("startindex", 1)
        if start_index < 1:
            start_index = 1
        count = request_query_string.get("count")
        if count is not None and count < 0:
            count = 0

        total_results = response_body["totalresults"]
        resources = response_body.get("resources", [])
        n_resources = len(resources)

        if total_results < n_resources:
            errors.append(
                ValidationError.total_results_mismatch(
                    total_results, n_resources
                ).with_location("body", "response", "totalResults")
            )
            errors.append(
                ValidationError.total_results_mismatch(
                    total_results, n_resources
                ).with_location("body", "response", "Resources")
            )
        if count is None and total_results > n_resources:
            errors.append(
                ValidationError.too_little_results().with_location("body", "response", "Resources")
            )
        if count is not None and count < n_resources:
            errors.append(
                ValidationError.too_many_results().with_location("body", "response", "Resources")
            )

        if errors:
            return errors

        is_pagination = (count or 0) > 0 and total_results > n_resources
        if is_pagination:
            if "startindex" not in response_body:
                errors.append(
                    ValidationError.missing_required_attribute(
                        "startindex"
                    ).with_location("body", "response", "startIndex")
                )
            if "itemsperpage" not in response_body:
                errors.append(
                    ValidationError.missing_required_attribute(
                        "startindex"
                    ).with_location("body", "response", "startIndex")
                )

        if errors:
            return errors

        if "startindex" in response_body and response_body["startindex"] > start_index:
            errors.append(
                ValidationError.response_value_does_not_correspond_to_parameter(
                    response_key="startIndex",
                    response_value=response_body["startindex"],
                    query_param_name="startIndex",
                    query_param_value=start_index,
                    reason="bigger value than requested",
                ).with_location("body", "response", "startIndex")
            )

        if "itemsperpage" in response_body and response_body["itemsperpage"] != n_resources:
            errors.append(
                ValidationError.values_must_match(
                    "itemsPerPage", "numer of Resources"
                ).with_location("body", "response", "itemsPerPage")
            )
            errors.append(
                ValidationError.values_must_match(
                    "itemsPerPage", "numer of Resources"
                ).with_location("body", "response", "Resources")
            )

        if status_code != 200:
            errors.append(
                ValidationError.bad_status_code("GET", 200, status_code).with_location(
                    "status", "response"
                )
            )

        return errors


class ListResponseResourceObjectGET(_ListResponseGET):
    def __init__(self, resource_schema: Schema):
        super().__init__(ListResponseSchema())
        self._resource_schema = resource_schema

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
        errors = super().validate_response(
            status_code=status_code,
            request_query_string=request_query_string,
            request_body=request_body,
            request_headers=request_headers,
            response_body=response_body,
            response_headers=response_headers,
        )
        if errors:
            return errors

        resources = response_body.get("resources", [])
        n_resources = len(resources)
        if n_resources == 1:
            resource = resources[0]
            for attr_name, attr in self._resource_schema.attributes.items():
                errors.extend(
                    [
                        error.with_location(0, "Resources", "body", "response")
                        for error in attr.validate(resource.get(attr_name), "RESPONSE")
                    ]
                )
        elif n_resources > 1:
            errors.append(
                ValidationError.too_many_results().with_location("Resources", "body", "response")
            )

        return errors


class ListResponseResourceTypeGET(_ListResponseGET):
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
    ) -> List[ValidationError]:
        errors = super().validate_response(
            status_code=status_code,
            request_query_string=request_query_string,
            request_body=request_body,
            request_headers=request_headers,
            response_body=response_body,
            response_headers=response_headers,
        )
        if errors:
            return errors

        resources = response_body.get("resources", [])
        for i, resource in enumerate(resources):
            for attr_name, attr in self._resource_schema.attributes.items():
                errors.extend(
                    [
                        error.with_location(i, "Resources", "body", "response")
                        for error in attr.validate(resource.get(attr_name), "RESPONSE")
                    ]
                )

        return errors


class ListResponseServerRootGET(_ListResponseGET):
    def __init__(self, resource_schemas: Iterable[Schema]):
        super().__init__(ListResponseSchema())
        self._resource_schemas = resource_schemas

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
        errors = super().validate_response(
            status_code=status_code,
            request_query_string=request_query_string,
            request_body=request_body,
            request_headers=request_headers,
            response_body=response_body,
            response_headers=response_headers,
        )
        if errors:
            return errors

        # TODO: validate according to 'attributes' and  whether they exists in all provided schemas
        return errors
