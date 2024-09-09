import abc
from typing import Any, Mapping, Optional, Sequence, Union, cast

import scimpler.config
from scimpler.data.attr_value_presence import AttrValuePresenceConfig
from scimpler.data.attrs import (
    AttrFilter,
    AttributeIssuer,
    AttributeMutability,
    AttributeReturn,
    Complex,
)
from scimpler.data.filter import Filter
from scimpler.data.schemas import BaseResourceSchema, BaseSchema, ResourceSchema
from scimpler.data.scim_data import Invalid, Missing, ScimData
from scimpler.data.sorter import Sorter
from scimpler.error import ValidationError, ValidationIssues, ValidationWarning
from scimpler.schemas import (
    BulkRequestSchema,
    BulkResponseSchema,
    ErrorSchema,
    ListResponseSchema,
    PatchOpSchema,
    SearchRequestSchema,
)


class Validator(abc.ABC):
    def __init__(self, config: Optional[scimpler.config.ServiceProviderConfig] = None):
        self.config = config or scimpler.config.service_provider_config

    @property
    def request_schema(self) -> BaseSchema:
        raise NotImplementedError

    @property
    def response_schema(self) -> BaseSchema:
        raise NotImplementedError

    @abc.abstractmethod
    def validate_request(self, *, body: Optional[Mapping[str, Any]] = None) -> ValidationIssues:
        """Validates requests."""

    @abc.abstractmethod
    def validate_response(
        self,
        *,
        status_code: int,
        body: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, Any]] = None,
        **kwargs,
    ) -> ValidationIssues:
        """Validates responses."""


class Error(Validator):
    """
    Error validator, designed to validate any SCIM errors.
    """

    def __init__(self):
        super().__init__(None)
        self._schema = ErrorSchema()

    @property
    def response_schema(self) -> ErrorSchema:
        """
        Schema designed for response (de)serialization.
        """
        return self._schema

    def validate_request(self, *, body: Optional[Mapping[str, Any]] = None) -> ValidationIssues:
        raise NotImplementedError

    def validate_response(
        self,
        *,
        status_code: int,
        body: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, Any]] = None,
        **kwargs: Any,
    ) -> ValidationIssues:
        """
        Validates the error response.

        Except for error body validation done by the inner schema, the validator checks if:

        - `status` in body matches the provided `status_code`,
        - value of `status_code` is in range: 300 <= status_code < 600.

        Args:
            status_code: Returned HTTP status code.
            body: Returned error body.
            headers: Returned response headers.
            **kwargs: Not used.

        Returns:
            Validation issues.
        """
        body_location = ("body",)
        issues = ValidationIssues()
        normalized = ScimData(body or {})
        issues.merge(
            self.response_schema.validate(normalized, AttrValuePresenceConfig("RESPONSE")),
            location=body_location,
        )
        status_attr_rep = self.response_schema.attrs.status
        status_location = body_location + status_attr_rep.location
        if (status_in_body := normalized.get(status_attr_rep)) and str(
            status_code
        ) != status_in_body:
            issues.add_error(
                issue=ValidationError.must_be_equal_to("response status code"),
                location=status_location,
                proceed=True,
            )
            issues.add_error(
                issue=ValidationError.must_be_equal_to("'status' attribute"),
                location=["status"],
                proceed=True,
            )
        if not 300 <= status_code < 600:
            issues.add_error(
                issue=ValidationError.bad_value_content(),
                location=["status"],
                proceed=True,
            )
        return issues


def _validate_resource_location_consistency(
    body: ScimData,
    schema: BaseResourceSchema,
    headers: Mapping[str, Any],
    presence_config: AttrValuePresenceConfig,
) -> ValidationIssues:
    issues = ValidationIssues()
    location_header = headers.get("Location")
    meta_location_rep = schema.attrs.meta__location
    meta_location = body.get(meta_location_rep)
    if meta_location is Invalid or not location_header:
        return issues

    if not meta_location and not presence_config.allowed(meta_location_rep):
        return issues

    if meta_location != location_header:
        issues.add_error(
            issue=ValidationError.must_be_equal_to("'Location' header"),
            location=("body", "meta", "location"),
            proceed=True,
        )
        issues.add_error(
            issue=ValidationError.must_be_equal_to("'meta.location'"),
            location=("headers", "Location"),
            proceed=True,
        )
    return issues


def _validate_status_code(expected: int, actual: int) -> ValidationIssues:
    issues = ValidationIssues()
    if expected != actual:
        issues.add_error(
            issue=ValidationError.bad_status_code(expected),
            proceed=True,
        )
    return issues


def _validate_resource_output_body(
    schema: BaseResourceSchema,
    config: scimpler.config.ServiceProviderConfig,
    location_header_required: bool,
    expected_status_code: int,
    status_code: int,
    body: ScimData,
    headers: Mapping[str, Any],
    presence_config: Optional[AttrValuePresenceConfig],
) -> ValidationIssues:
    issues = ValidationIssues()
    body_location = ("body",)
    presence_config = presence_config or AttrValuePresenceConfig("RESPONSE")
    if presence_config.direction != "RESPONSE":
        raise ValueError("bad direction in attribute presence config for response validation")

    issues.merge(
        schema.validate(
            data=body,
            presence_config=presence_config,
        ),
        location=body_location,
    )

    if "Location" not in headers and location_header_required:
        issues.add_error(
            issue=ValidationError.missing(),
            proceed=False,
            location=("headers", "Location"),
        )
    issues.merge(
        issues=_validate_status_code(expected_status_code, status_code),
        location=["status"],
    )
    issues.merge(
        issues=_validate_resource_location_consistency(
            body=body,
            schema=schema,
            headers=headers,
            presence_config=presence_config,
        ),
    )
    etag = headers.get("ETag")
    version_rep = schema.attrs.meta__version
    version = body.get(version_rep)
    if all([etag, version]) and etag != version:
        issues.add_error(
            issue=ValidationError.must_be_equal_to("'ETag' header"),
            proceed=True,
            location=body_location + version_rep.location,
        )
        issues.add_error(
            issue=ValidationError.must_be_equal_to("'meta.version'"),
            proceed=True,
            location=("headers", "ETag"),
        )
    elif config.etag.supported:
        if etag is None:
            issues.add_error(
                issue=ValidationError.missing(),
                location=("headers", "ETag"),
                proceed=False,
            )

        if version in [None, Missing] and presence_config.allowed(version_rep):
            issues.add_error(
                issue=ValidationError.missing(),
                proceed=False,
                location=body_location + version_rep.location,
            )
    return issues


class ResourceObjectGet(Validator):
    """
    Validator for **HTTP GET** operations performed against **resource object** endpoints.
    """

    def __init__(
        self,
        config: Optional[scimpler.config.ServiceProviderConfig] = None,
        *,
        resource_schema: BaseResourceSchema,
    ):
        """
        Args:
            config: Service provider configuration. If not provided, defaults to
                `scimpler.config.service_provider_config`
            resource_schema: Resource schema associated with the validator.

        Examples:
            >>> from scimpler.schemas import UserSchema
            >>>
            >>> validator = ResourceObjectGet(resource_schema=UserSchema())
        """
        super().__init__(config)
        self._schema = resource_schema
        self._response_schema = resource_schema.clone(_resource_output_filter)

    @property
    def response_schema(self) -> BaseResourceSchema:
        """
        Schema designed for response (de)serialization. Contains attributes whose `returnability`
        differs from `never`, and whose `mutability` differs from `writeOnly`.
        """
        return self._response_schema

    def validate_request(self, *, body: Optional[Mapping[str, Any]] = None) -> ValidationIssues:
        return ValidationIssues()

    def validate_response(
        self,
        *,
        status_code: int,
        body: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, Any]] = None,
        **kwargs,
    ) -> ValidationIssues:
        """
        Validates the **HTTP GET** responses returned from **resource object** endpoints.

        Except for body validation done by the inner schema, the validator checks if:

        - returned `status_code` equals 200,
        - `Location` header matches `meta.location` from body, if header is provided,
        - `ETag` header is provided if `etag` is enabled in the service provider configuration,
        - `meta.version` is provided if `etag` is enabled in the service provider configuration,
        - `ETag` header matches `meta.version` when both are provided.

        Args:
            status_code: Returned HTTP status code.
            body: Returned body.
            headers: Returned response headers.

        Keyword Args:
            presence_config (Optional[AttrValuePresenceConfig]): If not provided, the default one
                is used, with no attribute inclusivity and exclusivity specified.

        Returns:
            Validation issues.
        """
        return _validate_resource_output_body(
            schema=self._schema,
            config=self.config,
            location_header_required=False,
            expected_status_code=200,
            status_code=status_code,
            body=ScimData(body or {}),
            headers=headers or {},
            presence_config=kwargs.get("presence_config"),
        )


class ResourceObjectPut(Validator):
    """
    Validator for **HTTP PUT** operations performed against **resource object** endpoints.
    """

    def __init__(
        self,
        config: Optional[scimpler.config.ServiceProviderConfig] = None,
        *,
        resource_schema: ResourceSchema,
    ):
        """
        Args:
            config: Service provider configuration. If not provided, defaults to
                `scimpler.config.service_provider_config`
            resource_schema: Resource schema associated with the validator.

        Examples:
            >>> from scimpler.schemas import UserSchema
            >>>
            >>> validator = ResourceObjectPut(resource_schema=UserSchema())
        """
        super().__init__(config)
        self._request_schema = resource_schema.clone(
            attr_filter=AttrFilter(
                filter_=lambda attr: (
                    attr.mutability != AttributeMutability.READ_ONLY or attr.required
                ),
            )
        )
        self._response_schema = resource_schema.clone(_resource_output_filter)
        self._schema = resource_schema

    @property
    def request_schema(self) -> ResourceSchema:
        """
        Schema designed for request (de)serialization. Contains attributes whose `mutability`
        differs from `readOnly` or are required.
        """
        return self._request_schema

    @property
    def response_schema(self) -> ResourceSchema:
        """
        Schema designed for response (de)serialization. Contains attributes whose `returnability`
        differs from `never`, and whose `mutability` differs from `writeOnly`.
        """
        return self._schema

    def validate_request(self, *, body: Optional[Mapping[str, Any]] = None) -> ValidationIssues:
        """
        Validates the **HTTP PUT** requests sent to **resource object** endpoints.

        Performs request body validation using inner resource schema, including attribute presence
        validation that checks if all required attributes are provided (regardless the issuer).

        Args:
            body: The request body.

        Returns:
            Validation issues.
        """
        issues = ValidationIssues()
        issues.merge(
            issues=self._schema.validate(
                data=body or {},
                presence_config=AttrValuePresenceConfig(
                    "REQUEST",
                    ignore_issuer=[
                        attr_rep for attr_rep, attr in self._schema.attrs if attr.required
                    ],
                ),
            ),
            location=["body"],
        )
        return issues

    def validate_response(
        self,
        *,
        status_code: int,
        body: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, Any]] = None,
        **kwargs,
    ) -> ValidationIssues:
        """
        Validates the **HTTP PUT** responses returned from **resource object** endpoints.

        Except for body validation done by inner schema, the validator checks if:

        - returned `status_code` equals 200,
        - `Location` header matches `meta.location` from body, if header is provided,
        - `ETag` header is provided if `etag` is enabled in the service provider configuration,
        - `meta.version` is provided if `etag` is enabled in the service provider configuration,
        - `ETag` header matches `meta.version` when both are provided.

        Args:
            status_code: Returned HTTP status code.
            body: Returned body.
            headers: Returned response headers.

        Keyword Args:
            presence_config (Optional[AttrValuePresenceConfig]): If not provided, the default one
                is used, with no attribute inclusivity and exclusivity specified.

        Returns:
            Validation issues.
        """
        return _validate_resource_output_body(
            schema=self._schema,
            config=self.config,
            location_header_required=False,
            expected_status_code=200,
            status_code=status_code,
            body=ScimData(body or {}),
            headers=headers or {},
            presence_config=kwargs.get("presence_config"),
        )


class ResourcesPost(Validator):
    """
    Validator for **HTTP POST** operations performed against **resource type** endpoints.
    """

    def __init__(
        self,
        config: Optional[scimpler.config.ServiceProviderConfig] = None,
        *,
        resource_schema: ResourceSchema,
    ):
        """
        Args:
            config: Service provider configuration. If not provided, defaults to
                `scimpler.config.service_provider_config`
            resource_schema: Resource schema associated with the validator.

        Examples:
            >>> from scimpler.schemas import UserSchema
            >>>
            >>> validator = ResourcesPost(resource_schema=UserSchema())
        """
        super().__init__(config)
        self._schema = resource_schema
        self._request_schema = resource_schema.clone(
            attr_filter=AttrFilter(
                filter_=lambda attr: (
                    attr.mutability != AttributeMutability.READ_ONLY
                    and attr.issuer != AttributeIssuer.SERVICE_PROVIDER
                )
            )
        )
        self._response_schema = resource_schema.clone(_resource_output_filter)

    @property
    def request_schema(self) -> ResourceSchema:
        """
        Schema designed for request (de)serialization. Contains attributes whose `mutability`
        differs from `readOnly`, and which are not issued by the service provider.
        """
        return self._request_schema

    @property
    def response_schema(self) -> ResourceSchema:
        """
        Schema designed for response (de)serialization. Contains attributes whose `returnability`
        differs from `never`, and whose `mutability` differs from `writeOnly`.
        """
        return self._response_schema

    def validate_request(self, *, body: Optional[Mapping[str, Any]] = None) -> ValidationIssues:
        """
        Validates the **HTTP POST** requests sent to **resource type** endpoints.

        Performs request body validation using inner resource schema, including attribute presence
        validation that checks if:

        - attributes issued by the service provider are not provided,
        - required attribute are provided.

        Args:
            body: The request body.

        Returns:
            Validation issues.
        """
        issues = ValidationIssues()
        normalized = ScimData(body or {})
        issues.merge(
            issues=self._schema.validate(normalized, AttrValuePresenceConfig("REQUEST")),
            location=["body"],
        )
        return issues

    def validate_response(
        self,
        *,
        status_code: int,
        body: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, Any]] = None,
        **kwargs,
    ) -> ValidationIssues:
        """
        Validates the **HTTP POST** responses returned from **resource type** endpoints.

        Except for body validation (if provided) done by the inner schema, the validator checks if:

        - returned `status_code` equals 200,
        - `Location` header is provided,
        - `Location` header matches `meta.location` from body,
        - `ETag` header is provided if `etag` is enabled in the service provider configuration,
        - `meta.version` is provided if `etag` is enabled in the service provider configuration,
        - `ETag` header matches `meta.version` when both are provided,
        - `meta.created` equals `meta.lastModified`.

        Args:
            status_code: Returned HTTP status code.
            body: Returned body.
            headers: Returned response headers.

        Keyword Args:
            presence_config (Optional[AttrValuePresenceConfig]): If not provided, the default one
                is used, with no attribute inclusivity and exclusivity specified.

        Returns:
            Validation issues.
        """
        issues = ValidationIssues()
        if not body:
            issues.add_warning(issue=ValidationWarning.missing(), location=["body"])
            return issues

        normalized = ScimData(body)
        issues = _validate_resource_output_body(
            schema=self._schema,
            config=self.config,
            location_header_required=True,
            expected_status_code=201,
            status_code=status_code,
            body=normalized,
            headers=headers or {},
            presence_config=kwargs.get("presence_config"),
        )
        if normalized.get(self._schema.attrs.meta__created) != normalized.get(
            self._schema.attrs.meta__lastModified
        ):
            issues.add_error(
                issue=ValidationError.must_be_equal_to("'meta.created'"),
                proceed=True,
                location=("body", *self._schema.attrs.meta__lastModified.location),
            )
        return issues


def _validate_resources_sorted(
    sorter: Sorter,
    resources: list[ScimData],
    resource_schemas: Sequence[BaseResourceSchema],
    resource_presence_config: AttrValuePresenceConfig,
) -> ValidationIssues:
    issues = ValidationIssues()
    for resource, resource_schema in zip(resources, resource_schemas):
        if not can_validate_sorting(sorter, resource_presence_config, resource_schema):
            return issues

    if resources != sorter(resources, resource_schemas):
        issues.add_error(
            issue=ValidationError.resources_not_sorted(),
            proceed=True,
        )
    return issues


def _validate_etag_in_resources(
    resources: list[ScimData],
    resource_schemas: Sequence[BaseResourceSchema],
) -> ValidationIssues:
    issues = ValidationIssues()
    for i, (resource, resource_schema) in enumerate(zip(resources, resource_schemas)):
        if not isinstance(resource_schema, ResourceSchema):
            continue

        if resource.get("meta.version") is Missing:
            issues.add_error(
                issue=ValidationError.missing(),
                location=[i, "meta", "version"],
                proceed=True,
            )
    return issues


def _validate_number_of_resources(
    count: Optional[int],
    total_results: int,
    resources: list[Any],
) -> ValidationIssues:
    issues = ValidationIssues()
    n_resources = len(resources)
    if total_results < n_resources:
        issues.add_error(
            issue=ValidationError.bad_number_of_resources(
                "must not be greater than 'totalResults'"
            ),
            proceed=True,
        )
    elif count is None and total_results > n_resources:
        issues.add_error(
            issue=ValidationError.bad_number_of_resources("must be equal to 'totalResults'"),
            proceed=True,
        )
    if count is not None and count < n_resources:
        issues.add_error(
            issue=ValidationError.bad_number_of_resources(
                "must be lesser or equal to 'count' parameter"
            ),
            proceed=True,
        )
    return issues


def _validate_pagination_info(
    schema: ListResponseSchema,
    count: Optional[int],
    total_results: Any,
    resources: list[Any],
    start_index: Any,
    items_per_page: Any,
) -> ValidationIssues:
    issues = ValidationIssues()
    n_resources = len(resources)
    is_pagination = (count or 0) > 0 and total_results > n_resources
    if is_pagination:
        if start_index in [None, Missing]:
            issues.add_error(
                issue=ValidationError.missing(),
                location=schema.attrs.startindex.location,
                proceed=False,
            )
        if items_per_page in [None, Missing]:
            issues.add_error(
                issue=ValidationError.missing(),
                location=schema.attrs.itemsperpage.location,
                proceed=False,
            )
    return issues


def _validate_resources_filtered(
    filter_: Filter,
    resources: list[Any],
    resource_schemas: Sequence[BaseResourceSchema],
    resource_presence_config: AttrValuePresenceConfig,
) -> ValidationIssues:
    issues = ValidationIssues()
    for resource, resource_schema in zip(resources, resource_schemas):
        if not can_validate_filtering(filter_, resource_presence_config, resource_schema):
            return issues

    for i, (resource, schema) in enumerate(zip(resources, resource_schemas)):
        if not filter_(resource, schema):
            issues.add_error(
                issue=ValidationError.resources_not_filtered(),
                proceed=True,
                location=[i],
            )
    return issues


def _validate_resources_get_response(
    schema: ListResponseSchema,
    config: scimpler.config.ServiceProviderConfig,
    status_code: int,
    body: ScimData,
    start_index: int = 1,
    count: Optional[int] = None,
    filter_: Optional[Filter] = None,
    sorter: Optional[Sorter] = None,
    resource_presence_config: Optional[AttrValuePresenceConfig] = None,
) -> ValidationIssues:
    issues = ValidationIssues()
    body_location = ("body",)
    resources_location = body_location + schema.attrs.resources.location

    start_index_rep = schema.attrs.startindex
    start_index_location = body_location + start_index_rep.location

    resource_presence_config = resource_presence_config or AttrValuePresenceConfig("RESPONSE")
    issues_ = schema.validate(
        data=body,
        presence_config=AttrValuePresenceConfig("RESPONSE"),
        resource_presence_config=resource_presence_config,
    )
    issues.merge(issues_, location=body_location)
    issues.merge(
        issues=_validate_status_code(200, status_code),
        location=("status",),
    )
    start_index_body = body.get(start_index_rep)
    if start_index_body is not Invalid:
        if start_index_body and start_index_body > start_index:
            issues.add_error(
                issue=ValidationError.bad_value_content(),
                proceed=True,
                location=start_index_location,
            )

    resources = body.get(schema.attrs.resources)
    if resources is Invalid:
        return issues

    total_results = body.get(schema.attrs.totalresults)
    items_per_page = body.get(schema.attrs.itemsperpage)
    start_index_body = body.get(schema.attrs.startindex)

    if resources is Missing:
        resources = []

    if total_results:
        issues.merge(
            issues=_validate_number_of_resources(
                count=count,
                total_results=total_results,
                resources=resources,
            ),
            location=resources_location,
        )
        if Invalid not in [start_index_body, items_per_page]:
            issues.merge(
                issues=_validate_pagination_info(
                    schema=schema,
                    count=count,
                    total_results=total_results,
                    resources=resources,
                    start_index=start_index_body,
                    items_per_page=items_per_page,
                ),
                location=body_location,
            )

    if issues.has_errors(resources_location):
        return issues

    resource_schemas = cast(Sequence[BaseResourceSchema], schema.get_schemas(resources))
    if filter_ is not None:
        issues.merge(
            issues=_validate_resources_filtered(
                filter_=filter_,
                resources=resources,
                resource_schemas=resource_schemas,
                resource_presence_config=resource_presence_config,
            ),
            location=resources_location,
        )
    if sorter is not None:
        issues.merge(
            issues=_validate_resources_sorted(
                sorter=sorter,
                resources=resources,
                resource_schemas=resource_schemas,
                resource_presence_config=resource_presence_config,
            ),
            location=resources_location,
        )
    if config.etag.supported:
        issues.merge(
            issues=_validate_etag_in_resources(
                resources=resources,
                resource_schemas=resource_schemas,
            ),
            location=resources_location,
        )
    return issues


def can_validate_filtering(
    filter_: Filter,
    presence_config: AttrValuePresenceConfig,
    schema: BaseResourceSchema,
) -> bool:
    filter_attr_reps = filter_.attr_reps
    for attr_rep in filter_attr_reps:
        if not presence_config.allowed(attr_rep):
            return False

        attr = schema.attrs.get(attr_rep)
        if attr is None:
            continue  # intentional, such resources should be filtered out (except for 'not pr')

        if not (isinstance(attr, Complex) and attr.multi_valued):
            continue

        value_attr_rep = getattr(schema.attrs, f"{attr.name}__value", None)
        if value_attr_rep is None:
            continue

        if not presence_config.allowed(value_attr_rep):
            return False
    return True


def can_validate_sorting(
    sorter: Sorter, presence_config: AttrValuePresenceConfig, schema: BaseResourceSchema
) -> bool:
    allowed = presence_config.allowed(sorter.attr_rep)
    if not allowed:
        return False

    attr = schema.attrs.get(sorter.attr_rep)
    if attr is None:
        return True  # intentional, such resources should be ordered last

    if not (isinstance(attr, Complex) and attr.multi_valued):
        return allowed

    value_attr_rep = getattr(schema.attrs, f"{attr.name}__value", None)
    if value_attr_rep is None:
        return allowed

    primary_attr_rep = getattr(schema.attrs, f"{attr.name}__primary", None)
    if primary_attr_rep is None:
        return allowed

    value_allowed = presence_config.allowed(value_attr_rep)
    primary_allowed = presence_config.allowed(primary_attr_rep)
    return bool(value_allowed and primary_allowed)


class ResourcesQuery(Validator):
    """
    Validator for **HTTP GET** operations performed against **resource type** endpoints. It is
    able to handle different schemas in the same time, so can be used in **resource root** endpoint.
    """

    def __init__(
        self,
        config: Optional[scimpler.config.ServiceProviderConfig] = None,
        *,
        resource_schema: Union[Sequence[BaseResourceSchema], BaseResourceSchema],
    ):
        """
        Args:
            config: Service provider configuration. If not provided, defaults to
                `scimpler.config.service_provider_config`
            resource_schema: Resource schema(s) associated with the validator.

        Examples:
            >>> from scimpler.schemas import UserSchema, GroupSchema
            >>>
            >>> # for resource root endpoint
            >>> root_validator = ResourcesQuery(resource_schema=[UserSchema(), GroupSchema()])
            >>> # for specific resource type endpoint
            >>> validator = ResourcesQuery(resource_schema=UserSchema())
        """
        super().__init__(config)
        if isinstance(resource_schema, BaseResourceSchema):
            resource_schema = [resource_schema]
        self._response_validation_schema = ListResponseSchema(resource_schema)
        self._response_schema = ListResponseSchema(
            [item.clone(_resource_output_filter) for item in resource_schema]
        )

    @property
    def response_schema(self) -> ListResponseSchema:
        """
        Schema designed for response (de)serialization. Resource schemas contain attributes whose
        `returnability` differs from `never`, and whose `mutability` differs from `writeOnly`.
        ListResponse schema contains all attributes.
        """
        return self._response_schema

    def validate_request(self, *, body: Optional[Mapping[str, Any]] = None) -> ValidationIssues:
        return ValidationIssues()

    def validate_response(
        self,
        *,
        status_code: int,
        body: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, Any]] = None,
        **kwargs,
    ) -> ValidationIssues:
        """
        Validates the **HTTP GET** responses returned from **resource type** endpoints.

        Except for body validation done by the inner `ListResponseSchema`, the validator checks if:

        - returned `status_code` equals 200,
        - `startIndex` in the body is lesser or equal to the provided `start_index`,
        - `totalResults` greater or equal to number of `Resources`,
        - `totalResults` differs from number of `Resources` when `count` is not specified,
        - number of `Resources` is lesser or equal to the `count`, if specified,
        - `startIndex` is specified in the body for pagination,
        - `itemsPerPage` is specified in the body for pagination,
        - `Resources` are filtered, according to the provided `filter`,
        - `Resources` are sorted, according to the provided `sorter`,
        - every resource contains `meta.version`, if `etag` is supported.

        Filtering and sorting is not validated if attributes required to check filtering and
        sorting are meant to be excluded due to `AttrValuePresenceConfig`.

        Args:
            status_code: Returned HTTP status code.
            body: Returned body.
            headers: Not used.

        Keyword Args:
            presence_config (Optional[AttrValuePresenceConfig]): If not provided, the default one
                is used, with no attribute inclusivity and exclusivity specified. Applied on
                `Resources` only.
            start_index (Optional[int]): The 1-based index of the first query result.
            count (Optional[int]): Specifies the desired number of query results per page.
            filter (Optional[Filter]): Filter that was applied on `Resources`.
            sorter (Optional[Sorter]): Sorter that was applied on `Resources`.

        Returns:
            Validation issues.
        """
        return _validate_resources_get_response(
            schema=self._response_validation_schema,
            config=self.config,
            status_code=status_code,
            body=ScimData(body or {}),
            start_index=kwargs.get("start_index", 1),
            count=kwargs.get("count"),
            filter_=kwargs.get("filter"),
            sorter=kwargs.get("sorter"),
            resource_presence_config=kwargs.get("presence_config"),
        )


class SearchRequestPost(ResourcesQuery):
    """
    Validator for **HTTP POST** query operations. It is  able to handle different schemas
    in the same time, so can be used in **resource root** endpoint.
    """

    def __init__(
        self,
        config: Optional[scimpler.config.ServiceProviderConfig] = None,
        *,
        resource_schema: Union[Sequence[ResourceSchema], ResourceSchema],
    ):
        """
        Args:
            config: Service provider configuration. If not provided, defaults to
                `scimpler.config.service_provider_config`
            resource_schema: Resource schema(s) associated with the validator.

        Examples:
            >>> from scimpler.schemas import UserSchema, GroupSchema
            >>>
            >>> # for resource root endpoint
            >>> root_validator = SearchRequestPost(resource_schema=[UserSchema(), GroupSchema()])
            >>> # for specific resource type endpoint
            >>> validator = SearchRequestPost(resource_schema=UserSchema())
        """
        super().__init__(config, resource_schema=resource_schema)
        self._request_validation_schema = SearchRequestSchema.from_config(self.config)

    @property
    def request_schema(self) -> SearchRequestSchema:
        """
        Schema designed for request (de)serialization.
        """
        return self._request_validation_schema

    @property
    def response_schema(self) -> ListResponseSchema:
        """
        Schema designed for response (de)serialization. Resource schemas contain attributes whose
        `returnability` differs from `never`, and whose `mutability` differs from `writeOnly`.
        ListResponse schema contains all attributes.
        """
        return self._response_schema

    def validate_request(self, *, body: Optional[Mapping[str, Any]] = None) -> ValidationIssues:
        """
        Validates the **HTTP POST** query requests.

        Performs request body validation using inner `SearchRequestSchema`.

        Args:
            body: The request body.

        Returns:
            Validation issues.
        """
        issues = ValidationIssues()
        issues.merge(
            self._request_validation_schema.validate(
                ScimData(body or {}), AttrValuePresenceConfig("REQUEST")
            ),
            location=["body"],
        )
        return issues


class ResourceObjectPatch(Validator):
    """
    Validator for **HTTP PATCH** operations performed against **resource object** endpoints.
    """

    def __init__(
        self,
        config: Optional[scimpler.config.ServiceProviderConfig] = None,
        *,
        resource_schema: ResourceSchema,
    ):
        """
        Args:
            config: Service provider configuration. If not provided, defaults to
                `scimpler.config.service_provider_config`
            resource_schema: Resource schema associated with the validator.

        Raises:
            RuntimeError: If `patch` operation is not supported in the service provider
                configuration.

        Examples:
            >>> from scimpler.schemas import UserSchema
            >>>
            >>> validator = ResourceObjectPatch(resource_schema=UserSchema())
        """
        super().__init__(config)
        if not self.config.patch.supported:
            raise RuntimeError("patch operation is not supported")
        self._schema = PatchOpSchema(resource_schema)
        self._request_schema = PatchOpSchema(
            resource_schema.clone(
                attr_filter=AttrFilter(
                    filter_=lambda attr: attr.mutability != AttributeMutability.READ_ONLY,
                )
            )
        )
        self._resource_schema = resource_schema
        self._response_schema = resource_schema.clone(_resource_output_filter)

    @property
    def request_schema(self) -> PatchOpSchema:
        """
        Schema designed for request (de)serialization. Contains attributes whose `mutability`
        differs from `readOnly`.
        """
        return self._request_schema

    @property
    def response_schema(self) -> ResourceSchema:
        """
        Schema designed for response (de)serialization. Contains attributes whose `returnability`
        differs from `never`, and whose `mutability` differs from `writeOnly`.
        """
        return self._response_schema

    def validate_request(self, *, body: Optional[Mapping[str, Any]] = None) -> ValidationIssues:
        """
        Validates the **HTTP PATCH** requests sent to **resource object** endpoints.

        Performs request body validation using inner `PatchOpSchema`, including attribute presence
        validation.

        Args:
            body: The request body.

        Returns:
            Validation issues.
        """
        issues = ValidationIssues()
        normalized = ScimData(body or {})
        issues.merge(
            self._schema.validate(normalized, AttrValuePresenceConfig("REQUEST")),
            location=["body"],
        )
        return issues

    def validate_response(
        self,
        *,
        status_code: int,
        body: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, Any]] = None,
        **kwargs,
    ) -> ValidationIssues:
        """
        Validates the **HTTP PATCH** responses returned from **resource object** endpoints.

        Except for body validation done by the inner schema, the validator checks if:

        - returned `status_code` equals 204 if body is not returned, or 200, if body is returned
            or `AttrValuePresenceConfig` is specified,
        - `Location` header matches `meta.location` from body, if header is provided,
        - `ETag` header is provided if `etag` is enabled in the service provider configuration,
        - `meta.version` is provided if `etag` is enabled in the service provider configuration,
        - `ETag` header matches `meta.version` when both are provided.

        Args:
            status_code: Returned HTTP status code.
            body: Returned body.
            headers: Returned response headers.

        Keyword Args:
            presence_config (Optional[AttrValuePresenceConfig]): If not provided, the default one
                is used, with no attribute inclusivity and exclusivity specified.

        Returns:
            Validation issues.
        """
        issues = ValidationIssues()
        presence_config = kwargs.get("presence_config")
        if status_code == 204:
            if body is not None or presence_config is not None and presence_config.attr_reps:
                issues.add_error(
                    issue=ValidationError.bad_status_code(200),
                    proceed=True,
                    location=("status",),
                )
            return issues
        return _validate_resource_output_body(
            schema=self._resource_schema,
            config=self.config,
            location_header_required=False,
            expected_status_code=200,
            status_code=status_code,
            body=ScimData(body or {}),
            headers=headers or {},
            presence_config=presence_config,
        )


class ResourceObjectDelete(Validator):
    """
    Validator for **HTTP DELETE** operations performed against **resource object** endpoints.
    """

    def validate_request(self, *, body: Optional[Mapping[str, Any]] = None) -> ValidationIssues:
        return ValidationIssues()

    def validate_response(
        self,
        *,
        status_code: int,
        body: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, Any]] = None,
        **kwargs: Any,
    ) -> ValidationIssues:
        """
        Validates the **HTTP DELETE** responses returned from **resource object** endpoints.

        It only validates if provided `status_code` equals 204.

        Args:
            status_code: Returned HTTP status code.
            body: Not used.
            headers: Not Used.
            **kwargs: Not used.

        Returns:
            Validation issues.
        """
        issues = ValidationIssues()
        if status_code != 204:
            issues.add_error(
                issue=ValidationError.bad_status_code(204),
                proceed=True,
                location=["status"],
            )
        return issues


class BulkOperations(Validator):
    """
    Validator for **HTTP POST** operations performed against bulk endpoint.
    """

    def __init__(
        self,
        config: Optional[scimpler.config.ServiceProviderConfig] = None,
        *,
        resource_schemas: Sequence[ResourceSchema],
    ):
        """
        Args:
            config: Service provider configuration. If not provided, defaults to
                `scimpler.config.service_provider_config`
            resource_schemas: Resource schemas associated with the validator.

        Raises:
            RuntimeError: If `bulk` operation is not supported in the service provider
                configuration.

        Examples:
            >>> from scimpler.schemas import UserSchema, GroupSchema
            >>>
            >>> validator = BulkOperations(resource_schemas=[UserSchema(), GroupSchema()])
        """
        super().__init__(config)
        if not self.config.bulk.supported:
            raise RuntimeError("bulk operations are not configured")
        self._validators: dict[str, dict[str, Validator]] = {
            "GET": {},
            "POST": {},
            "PUT": {},
            "PATCH": {},
            "DELETE": {},
        }
        response_schemas: dict[str, dict[str, Optional[BaseSchema]]] = {
            "GET": {},
            "POST": {},
            "PUT": {},
            "PATCH": {},
            "DELETE": {},
        }
        request_schemas: dict[str, dict[str, Optional[BaseSchema]]] = {
            "GET": {},
            "POST": {},
            "PUT": {},
            "PATCH": {},
            "DELETE": {},
        }
        for resource_schema in resource_schemas:
            get = ResourceObjectGet(self.config, resource_schema=resource_schema)
            self._validators["GET"][resource_schema.endpoint] = get
            response_schemas["GET"][resource_schema.endpoint] = get.response_schema
            request_schemas["GET"][resource_schema.endpoint] = None

            post = ResourcesPost(self.config, resource_schema=resource_schema)
            self._validators["POST"][resource_schema.endpoint] = post
            response_schemas["POST"][resource_schema.endpoint] = post.response_schema
            request_schemas["POST"][resource_schema.endpoint] = post.request_schema

            put = ResourceObjectPut(self.config, resource_schema=resource_schema)
            self._validators["PUT"][resource_schema.endpoint] = put
            response_schemas["PUT"][resource_schema.endpoint] = put.response_schema
            request_schemas["PUT"][resource_schema.endpoint] = put.request_schema

            patch = ResourceObjectPatch(self.config, resource_schema=resource_schema)
            self._validators["PATCH"][resource_schema.endpoint] = patch
            response_schemas["PATCH"][resource_schema.endpoint] = patch.response_schema
            request_schemas["PATCH"][resource_schema.endpoint] = patch.request_schema

            delete = ResourceObjectDelete(self.config)
            self._validators["DELETE"][resource_schema.endpoint] = delete
            response_schemas["DELETE"][resource_schema.endpoint] = None
            request_schemas["DELETE"][resource_schema.endpoint] = None

        self._error_validator = Error()
        self._request_schema = BulkRequestSchema(sub_schemas=request_schemas)
        self._response_schema = BulkResponseSchema(
            sub_schemas=response_schemas,
            error_schema=self._error_validator.response_schema,
        )

    @property
    def request_schema(self) -> BulkRequestSchema:
        """
        Schema designed for request (de)serialization. Schemas for `data` attribute values
        are the same as request schemas in validators, corresponding to the bulk operations.
        """
        return self._request_schema

    @property
    def response_schema(self) -> BulkResponseSchema:
        """
        Schema designed for response (de)serialization. Schemas for `response` attribute values
        are the same as response schemas in validators, corresponding to the bulk operations.
        """
        return self._response_schema

    def validate_request(self, *, body: Optional[Mapping[str, Any]] = None) -> ValidationIssues:
        """
        Validates the **HTTP POST** requests performed against bulk endpoint.

        Except for body validation done by the inner `BulkRequestSchema`, the validator checks if:

        - number of `Operations` does not exceed configured maximum number of operations,
        - correct data for operations is provided,

        Args:
            body: Request body.

        Returns:
            Validation issues.
        """
        issues = ValidationIssues()
        body_location = ("body",)
        normalized = ScimData(body or {})
        issues.merge(
            self._request_schema.validate(normalized, AttrValuePresenceConfig("REQUEST")),
            location=body_location,
        )
        if not normalized.get(self._request_schema.attrs.operations):
            return issues

        if (
            isinstance(self.config.bulk.max_operations, int)
            and len(normalized.get(self._request_schema.attrs.operations))
            > self.config.bulk.max_operations
        ):
            issues.add_error(
                issue=ValidationError.too_many_bulk_operations(self.config.bulk.max_operations),
                proceed=True,
                location=body_location + self._response_schema.attrs.operations.location,
            )

        data_rep = self._request_schema.attrs.operations__data
        paths = normalized.get(self._request_schema.attrs.operations__path)
        data = normalized.get(self._request_schema.attrs.operations__data)
        methods = normalized.get(self._request_schema.attrs.operations__method)
        for i, (path, data_item, method) in enumerate(zip(paths, data, methods)):
            if not all([path, data_item, method]) or method == "DELETE":
                continue

            if method == "POST":
                resource_type_endpoint = path
            else:
                resource_type_endpoint = f"/{path.split('/', 2)[1]}"
            validator = cast(Validator, self._validators[method].get(resource_type_endpoint))
            issues_ = validator.validate_request(body=data_item)
            data_item_location = body_location + (data_rep.attr, i, data_rep.sub_attr)
            issues.merge(issues_.get(location=["body"]), location=data_item_location)
        return issues

    def validate_response(
        self,
        *,
        status_code: int,
        body: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, Any]] = None,
        **kwargs,
    ) -> ValidationIssues:
        """
        Validates the **HTTP POST** responses returned from bulk endpoint.

        Except for body validation done by the inner `BulkResponseSchema`, the validator checks if:

        - returned `status_code` equals 200,
        - correct error responses are returned for statuses greater or equal to 300,
        - correct responses are returned for successful completions,
        - if `meta.location` matches `Operations.location` for every operation,
        - if `meta.version` matches `Operations.version` for every operation,
        - if number of unsuccessful completions did not exceed `fail_on_errors` parameter.

        Args:
            status_code: Returned HTTP status code.
            body: Returned body.
            headers: Not used.

        Keyword Args:
            fail_on_errors (Optional[int]): An integer specifying the number of errors that the
                service provider should accept before the operation is terminated.

        Returns:
            Validation issues.
        """
        issues = ValidationIssues()
        normalized = ScimData(body or {})
        body_location = ("body",)
        issues.merge(
            self._response_schema.validate(normalized, AttrValuePresenceConfig("RESPONSE")),
            location=body_location,
        )
        issues.merge(
            issues=_validate_status_code(200, status_code),
            location=["status"],
        )
        operations = normalized.get("Operations")
        if operations is Invalid:
            return issues

        operations_location = body_location + self._response_schema.attrs.operations.location
        for i, operation in enumerate(operations):
            issues.merge(
                issues=self._validate_response_operation(operation, (*operations_location, i)),
            )
        n_errors = 0
        for operation in operations:
            status = operation.get("status")
            if not status:
                continue
            if int(status) >= 300:
                n_errors += 1
        fail_on_errors = kwargs.get("fail_on_errors")
        if fail_on_errors is not None and n_errors > fail_on_errors:
            issues.add_error(
                issue=ValidationError.too_many_errors_in_bulk(fail_on_errors),
                proceed=True,
                location=operations_location,
            )
        return issues

    def _validate_response_operation(
        self, operation: ScimData, operation_location: tuple
    ) -> ValidationIssues:
        issues = ValidationIssues()
        status = operation.get("status")
        response = operation.get("response")
        location = operation.get("location")
        method = operation.get("method")
        version = operation.get("version")

        if not all([method, status, response]):
            return issues

        response_location: tuple[Union[str, int], ...] = (*operation_location, "response")
        status_location: tuple[Union[str, int], ...] = (*operation_location, "status")
        location_location: tuple[Union[str, int], ...] = (*operation_location, "location")
        version_location: tuple[Union[str, int], ...] = (*operation_location, "version")

        resource_validator = None
        if location:
            for endpoint, validator in self._validators[method].items():
                if endpoint in location:
                    resource_validator = validator
                    break

        status = int(status)
        if status >= 300:
            issues_ = self._error_validator.validate_response(
                status_code=status,
                body=response,
            )
            issues.merge(
                issues=issues_.get(location=["body"]),
                location=response_location,
            )
            issues.merge(
                issues=issues_.get(location=["status"]),
                location=status_location,
            )
            return issues

        if not location or not isinstance(resource_validator, Validator):
            return issues

        resource_version = response.get("meta.version")
        issues_ = resource_validator.validate_response(
            body=response,
            status_code=status,
            headers={"Location": location, "ETag": resource_version},
        )
        meta_location_mismatch = issues_.pop([8], location=("body", "meta", "location"))
        header_location_mismatch = issues_.pop([8], location=("headers", "Location"))
        issues.merge(issues_.get(location=["body"]), location=response_location)
        issues.merge(issues_.get(location=["status"]), location=status_location)
        if meta_location_mismatch.has_errors() and header_location_mismatch.has_errors():
            issues.add_error(
                issue=ValidationError.must_be_equal_to("operation's location"),
                proceed=True,
                location=[*response_location, "meta", "location"],
            )
            issues.add_error(
                issue=ValidationError.must_be_equal_to("'response.meta.location'"),
                proceed=True,
                location=location_location,
            )
        if version and resource_version and version != resource_version:
            issues.add_error(
                issue=ValidationError.must_be_equal_to("operation's version"),
                proceed=True,
                location=[*response_location, "meta", "version"],
            )
            issues.add_error(
                issue=ValidationError.must_be_equal_to("'response.meta.version'"),
                proceed=True,
                location=version_location,
            )
        return issues


_resource_output_filter = AttrFilter(
    filter_=(
        lambda attr: (
            attr.returned != AttributeReturn.NEVER
            and attr.mutability != AttributeMutability.WRITE_ONLY
        )
    )
)
