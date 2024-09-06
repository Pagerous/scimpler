import abc
from typing import Any, MutableMapping, Optional

import scimpler.config
from scimpler.data.attrs import AttrFilter
from scimpler.data.scim_data import ScimData
from scimpler.error import ValidationError, ValidationIssues
from scimpler.schemas.search_request import SearchRequestSchema


class QueryHandler(abc.ABC):
    def __init__(self, config: Optional[scimpler.config.ServiceProviderConfig] = None) -> None:
        self.config = config or scimpler.config.service_provider_config

    @property
    @abc.abstractmethod
    def schema(self) -> SearchRequestSchema:
        """Docs placeholder."""

    def validate(self, query_params: Optional[MutableMapping[str, Any]] = None) -> ValidationIssues:
        query_params = ScimData(query_params or {})
        query_params.set(
            "schemas",
            ["urn:ietf:params:scim:api:messages:2.0:SearchRequest"],
        )
        return self.schema.validate(query_params)

    def deserialize(self, query_params: Optional[MutableMapping[str, Any]] = None) -> ScimData:
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
        query_params = ScimData(query_params or {})
        serialized = self.schema.serialize(query_params)
        if attributes := query_params.get("attributes"):
            serialized["attributes"] = ",".join(attributes)
        if excluded_attributes := query_params.get("excludedAttributes"):
            serialized["excludedAttributes"] = ",".join(excluded_attributes)
        query_params.update(serialized)
        return query_params


class GenericQueryHandler(QueryHandler, abc.ABC):
    def __init__(self, config: Optional[scimpler.config.ServiceProviderConfig] = None) -> None:
        super().__init__(config)
        self._schema = SearchRequestSchema(
            attr_filter=AttrFilter(attr_names={"attributes", "excludedAttributes"}, include=True)
        )

    @property
    def schema(self) -> SearchRequestSchema:
        return self._schema


class ResourcesPost(GenericQueryHandler):
    pass


class ResourceObjectGet(GenericQueryHandler):
    pass


class ResourceObjectPut(GenericQueryHandler):
    pass


class ResourceObjectPatch(GenericQueryHandler):
    pass


class ServerRootResourcesGet(QueryHandler):
    def __init__(self, config: scimpler.config.ServiceProviderConfig):
        super().__init__(config)
        self._schema = SearchRequestSchema.from_config(self.config)

    @property
    def schema(self) -> SearchRequestSchema:
        return self._schema


class ResourcesGet(ServerRootResourcesGet):
    pass


class _ServiceProviderConfig(QueryHandler):
    def __init__(self, config: Optional[scimpler.config.ServiceProviderConfig] = None) -> None:
        super().__init__(config)
        self._schema = SearchRequestSchema(attr_filter=AttrFilter(filter_=lambda _: False))

    @property
    def schema(self) -> SearchRequestSchema:
        return self._schema

    def validate(self, query_params: Optional[MutableMapping[str, Any]] = None) -> ValidationIssues:
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


class SchemasGet(_ServiceProviderConfig):
    pass


class ResourceTypesGet(_ServiceProviderConfig):
    pass
