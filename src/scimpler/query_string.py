import abc
from typing import Any, MutableMapping, Optional

import scimpler.config
from scimpler.data.attrs import AttrFilter
from scimpler.data.scim_data import ScimData
from scimpler.error import ValidationError, ValidationIssues
from scimpler.schemas.search_request import SearchRequestSchema


class QueryStringHandler(abc.ABC):
    """
    Handles query-string parameters.
    """

    def __init__(self, config: Optional[scimpler.config.ServiceProviderConfig] = None) -> None:
        """
        Args:
            config: Service provider configuration. If not provided, defaults to
                `scimpler.config.service_provider_config`
        """
        self.config = config or scimpler.config.service_provider_config

    @property
    @abc.abstractmethod
    def schema(self) -> SearchRequestSchema:
        """
        Inner `SearchRequestSchema` used for query-string validation, serialization,
        and deserialization.
        """

    def validate(self, query_params: Optional[MutableMapping[str, Any]] = None) -> ValidationIssues:
        """
        Validates `query_params` using `SearchRequestSchema`.

        Returns:
            Validation issues.
        """
        query_params = ScimData(query_params or {})
        query_params.set(
            "schemas",
            ["urn:ietf:params:scim:api:messages:2.0:SearchRequest"],
        )
        return self.schema.validate(query_params)

    def deserialize(self, query_params: Optional[MutableMapping[str, Any]] = None) -> ScimData:
        """
        Deserializes `query_params` using `SearchRequestSchema`, which contains attributes suitable
        for the specific HTTP operation. Unknown parameters are preserved.
        """
        query_params = ScimData(query_params or {})
        attributes = query_params.get("attributes")
        if isinstance(attributes, str):
            attributes = [item.strip() for item in attributes.split(",")]
            query_params["attributes"] = attributes
        excluded_attributes = query_params.get("excludedAttributes")
        if isinstance(excluded_attributes, str):
            excluded_attributes = [item.strip() for item in excluded_attributes.split(",")]
            query_params["excludedAttributes"] = excluded_attributes
        query_params.update(self.schema.deserialize(query_params))
        return query_params

    def serialize(self, query_params: Optional[MutableMapping[str, Any]] = None) -> ScimData:
        """
        Serializes `query_params` using `SearchRequestSchema`, which contains attributes suitable
        for the specific HTTP operation. Unknown parameters are preserved.
        """
        query_params = ScimData(query_params or {})
        serialized = self.schema.serialize(query_params)
        if attributes := query_params.get("attributes"):
            serialized["attributes"] = ",".join(str(attr_rep) for attr_rep in attributes)
        if excluded_attributes := query_params.get("excludedAttributes"):
            serialized["excludedAttributes"] = ",".join(
                str(attr_rep) for attr_rep in excluded_attributes
            )
        query_params.update(serialized)
        return query_params


class GenericQueryStringHandler(QueryStringHandler, abc.ABC):
    def __init__(self) -> None:
        super().__init__(None)
        self._schema = SearchRequestSchema(
            attr_filter=AttrFilter(attr_reps={"attributes", "excludedAttributes"}, include=True)
        )

    @property
    def schema(self) -> SearchRequestSchema:
        return self._schema


class ResourcesPost(GenericQueryStringHandler):
    """
    Handles query-string parameters sent with **HTTP POST** operations performed against
    **resource type** endpoints.
    """


class ResourceObjectGet(GenericQueryStringHandler):
    """
    Handles query-string parameters sent with **HTTP GET** operations performed against
    **resource object** endpoints.
    """


class ResourceObjectPut(GenericQueryStringHandler):
    """
    Handles query-string parameters sent with **HTTP PUT** operations performed against
    **resource object** endpoints.
    """


class ResourceObjectPatch(GenericQueryStringHandler):
    """
    Handles query-string parameters sent with **HTTP PUT** operations performed against
    **resource object** endpoints.
    """


class ResourcesGet(QueryStringHandler):
    """
    Handles query-string parameters sent with **HTTP GET** operations performed against
    **resource type** endpoints.
    """

    def __init__(self, config: Optional[scimpler.config.ServiceProviderConfig] = None):
        """
        Args:
            config: Service provider configuration. If not provided, defaults to
                `scimpler.config.service_provider_config`
        """
        super().__init__(config)
        self._schema = SearchRequestSchema.from_config(self.config)

    @property
    def schema(self) -> SearchRequestSchema:
        return self._schema


class _ServiceProviderConfigGet(QueryStringHandler):
    def __init__(self, config: Optional[scimpler.config.ServiceProviderConfig] = None) -> None:
        """
        Args:
            config: Service provider configuration. If not provided, defaults to
                `scimpler.config.service_provider_config`
        """
        super().__init__(config)
        self._schema = SearchRequestSchema(attr_filter=AttrFilter(filter_=lambda _: False))

    @property
    def schema(self) -> SearchRequestSchema:
        """
        Inner `SearchRequestSchema` used for query-string validation, serialization,
        and deserialization.
        """
        return self._schema

    def validate(self, query_params: Optional[MutableMapping[str, Any]] = None) -> ValidationIssues:
        """
        Validates `query_params` using `SearchRequestSchema`. Additionally, it checks if
        `filter` is not provided.
        """
        issues = ValidationIssues()
        query_params = query_params or {}
        if "filter" in query_params:
            issues.add_error(
                issue=ValidationError.not_supported(),
                proceed=False,
                location=["filter"],
            )
            return issues
        return super().validate(query_params)


class SchemasGet(_ServiceProviderConfigGet):
    """
    Handles query-string parameters sent with **HTTP GET** operations performed against
    **/Schemas** endpoint.
    """


class ResourceTypesGet(_ServiceProviderConfigGet):
    """
    Handles query-string parameters sent with **HTTP GET** operations performed against
    **/ResourceTypes** endpoint.
    """
