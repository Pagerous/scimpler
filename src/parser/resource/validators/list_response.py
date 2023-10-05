from typing import Any, Dict, Iterable, Optional

from src.parser.error import ValidationError, ValidationIssues
from src.parser.resource.validators.validator import (
    EndpointValidatorGET, preprocess_response_validation,
    preprocess_request_validation,
)
from src.parser.resource.schemas import ListResponseSchema, Schema


class _ListResponseGET(EndpointValidatorGET):
    @preprocess_request_validation
    def validate_request(
        self,
        *,
        query_string: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
    ) -> ValidationIssues:
        return ValidationIssues()

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
                    issue=ValidationError.too_little_results(),
                    location=("response", "body", "Resources"),
                    proceed=True,
                )

            if count is not None and count < n_resources:
                issues.add(
                    issue=ValidationError.too_many_results(),
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
                    location=("body", "response", "itemsPerPage"),
                    proceed=True,
                )
                issues.add(
                    issue=ValidationError.values_must_match(
                        value_1="itemsPerPage", value_2="numer of Resources"
                    ),
                    location=("body", "response", "Resources"),
                    proceed=True,
                )

        return issues


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
            n_resources = len(resources)
            if n_resources == 1:
                resource = resources[0]
                for attr_name, attr in self._resource_schema.attributes.items():
                    issues.merge(
                        issues=attr.validate(resource.get(attr_name), "RESPONSE"),
                        location=("response", "body", "Resources", 0, attr.name)
                    )

            elif n_resources > 1:
                issues.add(
                    issue=ValidationError.too_many_results(),
                    location=("response", "body", "Resources"),
                    proceed=True,
                )

        return issues


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
