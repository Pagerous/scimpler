import abc
from typing import Any, Optional

from src.assets.config import ServiceProviderConfig
from src.assets.schemas import search_request
from src.assets.schemas.search_request import create_search_request_schema
from src.container import Missing, SCIMDataContainer


class QueryStringDeserializer(abc.ABC):
    def __init__(self, config: ServiceProviderConfig):
        self.config = config

    @abc.abstractmethod
    def deserialize(self, query_string: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """Docs placeholder."""


class _AttributesDeserializer(QueryStringDeserializer, abc.ABC):
    def deserialize(self, query_string: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        query_string = query_string or {}
        deserialized = (
            search_request.SearchRequest()
            .deserialize(
                SCIMDataContainer(
                    {
                        "attributes": query_string.pop("attributes", Missing),
                        "excludeAttributes": query_string.pop("excludeAttributes", Missing),
                    }
                )
            )
            .to_dict()
        )
        deserialized.update(query_string)
        return deserialized


class ResourcesPOST(_AttributesDeserializer):
    pass


class ResourceObjectGET(_AttributesDeserializer):
    pass


class ResourceObjectPUT(_AttributesDeserializer):
    pass


class ResourceObjectPATCH(_AttributesDeserializer):
    pass


class ServerRootResourcesGET(QueryStringDeserializer):
    def __init__(self, config: ServiceProviderConfig):
        super().__init__(config)
        self._schema = create_search_request_schema(config)

    def deserialize(self, query_string: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        query_string = query_string or {}
        additional_params = SCIMDataContainer(query_string)

        input_ = SCIMDataContainer(query_string)
        for attr_rep, attr in self._schema.attrs:
            additional_params.pop(attr_rep)

        deserialized = self._schema.deserialize(input_).to_dict()
        deserialized.update(additional_params.to_dict())
        return deserialized


class ResourcesGET(ServerRootResourcesGET):
    pass
