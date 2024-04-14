import abc
from typing import Any, Dict, Optional

from src.assets.config import ServiceProviderConfig
from src.assets.schemas import search_request
from src.data.container import Missing, SCIMDataContainer


class QueryStringParser(abc.ABC):
    def __init__(self, config: ServiceProviderConfig):
        self._config = config

    @abc.abstractmethod
    def parse(self, query_string: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        ...


class _AttributesParser(QueryStringParser, abc.ABC):
    def parse(self, query_string: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        query_string = query_string or {}
        return (
            search_request.SearchRequest()
            .parse(
                SCIMDataContainer(
                    {
                        "attributes": query_string.get("attributes", Missing),
                        "excludeAttributes": query_string.get("excludeAttributes", Missing),
                    }
                )
            )
            .to_dict()
        )


class ResourcesPOST(_AttributesParser):
    pass


class ResourceObjectGET(_AttributesParser):
    pass


class ResourceObjectPUT(_AttributesParser):
    pass


class ResourceObjectPATCH(_AttributesParser):
    pass


class ServerRootResourcesGET(QueryStringParser):
    def parse(self, query_string: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return search_request.SearchRequest().parse(SCIMDataContainer(query_string or {})).to_dict()


class ResourcesGET(ServerRootResourcesGET):
    pass
