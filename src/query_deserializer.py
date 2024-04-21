import abc
from typing import Any, Dict, Optional

from src.assets.config import ServiceProviderConfig
from src.assets.schemas import search_request
from src.data.container import Missing, SCIMDataContainer


class QueryStringDeserializer(abc.ABC):
    def __init__(self, config: ServiceProviderConfig):
        self._config = config

    @abc.abstractmethod
    def deserialize(self, query_string: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        ...


class _AttributesDeserializer(QueryStringDeserializer, abc.ABC):
    def deserialize(self, query_string: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        query_string = query_string or {}
        return (
            search_request.SearchRequest()
            .deserialize(
                SCIMDataContainer(
                    {
                        "attributes": query_string.get("attributes", Missing),
                        "excludeAttributes": query_string.get("excludeAttributes", Missing),
                    }
                )
            )
            .to_dict()
        )


class ResourcesPOST(_AttributesDeserializer):
    pass


class ResourceObjectGET(_AttributesDeserializer):
    pass


class ResourceObjectPUT(_AttributesDeserializer):
    pass


class ResourceObjectPATCH(_AttributesDeserializer):
    pass


class ServerRootResourcesGET(QueryStringDeserializer):
    def deserialize(self, query_string: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return (
            search_request.SearchRequest()
            .deserialize(SCIMDataContainer(query_string or {}))
            .to_dict()
        )


class ResourcesGET(ServerRootResourcesGET):
    pass
