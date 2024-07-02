import abc
from typing import Any, MutableMapping, Optional

from src import registry
from src.assets.schemas.search_request import create_search_request_schema, SearchRequest
from src.config import ServiceProviderConfig
from src.container import SCIMData
from src.error import ValidationError, ValidationIssues


class QueryHandler(abc.ABC):
    def __init__(self, config: Optional[ServiceProviderConfig] = None) -> None:
        self.config = config or registry.service_provider_config

    @property
    @abc.abstractmethod
    def schema(self) -> SearchRequest:
        """Docs placeholder."""

    def validate(self, query_params: Optional[MutableMapping[str, Any]] = None) -> ValidationIssues:
        query_params = SCIMData(query_params or {})
        query_params.set(
            "schemas",
            ["urn:ietf:params:scim:api:messages:2.0:SearchRequest"],
        )
        return self.schema.validate(query_params)

    def deserialize(self, query_params: Optional[MutableMapping[str, Any]] = None) -> SCIMData:
        query_params = query_params or {}
        attributes = query_params.get("attributes")
        if isinstance(attributes, str):
            attributes = [item.strip() for item in attributes.split(",")]
            query_params["attributes"] = attributes
        exclude_attributes = query_params.get("excludeAttributes")
        if isinstance(exclude_attributes, str):
            exclude_attributes = [item.strip() for item in exclude_attributes.split(",")]
            query_params["excludeAttributes"] = exclude_attributes
        return self.schema.deserialize(query_params)

    def serialize(self, query_params: Optional[MutableMapping[str, Any]] = None) -> SCIMData:
        query_params = query_params or {}
        serialized = self.schema.serialize(query_params)
        if attributes := query_params.get("attributes"):
            serialized["attributes"] = ",".join(attributes)
        if exclude_attributes := query_params.get("excludeAttributes"):
            serialized["excludeAttributes"] = ",".join(exclude_attributes)
        return serialized


class GenericQueryHandler(QueryHandler, abc.ABC):
    def __init__(self, config: Optional[ServiceProviderConfig] = None) -> None:
        super().__init__(config)
        self._schema = SearchRequest().clone(
            lambda attr: str(attr.name) in {"attributes", "excludeAttributes"}
        )

    @property
    def schema(self) -> SearchRequest:
        return self._schema


class ResourcesPOST(GenericQueryHandler):
    pass


class ResourceObjectGET(GenericQueryHandler):
    pass


class ResourceObjectPUT(GenericQueryHandler):
    pass


class ResourceObjectPATCH(GenericQueryHandler):
    pass


class ServerRootResourcesGET(QueryHandler):
    def __init__(self, config: ServiceProviderConfig):
        super().__init__(config)
        self._schema = create_search_request_schema(self.config)

    @property
    def schema(self) -> SearchRequest:
        return self._schema


class ResourcesGET(ServerRootResourcesGET):
    pass


class _ServiceProviderConfig(QueryHandler):
    def __init__(self, config: Optional[ServiceProviderConfig] = None) -> None:
        super().__init__(config)
        self._schema = SearchRequest().clone(lambda _: False)

    @property
    def schema(self) -> SearchRequest:
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


class SchemasGET(_ServiceProviderConfig):
    pass


class ResourceTypesGET(_ServiceProviderConfig):
    pass
