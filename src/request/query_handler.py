import abc
from typing import Any, MutableMapping, Optional

from src import registry
from src.assets.schemas import search_request
from src.assets.schemas.search_request import create_search_request_schema
from src.config import ServiceProviderConfig
from src.container import Missing, SCIMData
from src.data.attr_presence import AttrPresenceConfig
from src.data.filter import Filter
from src.data.sorter import Sorter


class QueryHandler(abc.ABC):
    def __init__(self, config: Optional[ServiceProviderConfig] = None) -> None:
        self.config = config or registry.service_provider_config

    @abc.abstractmethod
    def deserialize(
        self, query_params: Optional[MutableMapping[str, Any]] = None
    ) -> dict[str, Any]:
        """Docs placeholder."""

    @abc.abstractmethod
    def serialize(self, query_params: Optional[MutableMapping[str, Any]]) -> dict[str, Any]:
        """Docs placeholder."""


class _AttributesDeserializer(QueryHandler, abc.ABC):
    def deserialize(
        self, query_params: Optional[MutableMapping[str, Any]] = None
    ) -> dict[str, Any]:
        query_params = query_params or {}
        deserialized = (
            search_request.SearchRequest()
            .deserialize(
                SCIMData(
                    {
                        "attributes": query_params.pop("attributes", Missing),
                        "excludeAttributes": query_params.pop("excludeAttributes", Missing),
                    }
                )
            )
            .to_dict()
        )
        deserialized.update(query_params)
        return deserialized

    def serialize(self, query_params: Optional[MutableMapping[str, Any]]) -> dict[str, Any]:
        query_params = query_params or {}
        presence_config = query_params.get("presence_config")
        if not isinstance(presence_config, AttrPresenceConfig):
            return {}
        return _serialize_presence_config(presence_config)


def _serialize_presence_config(presence_config: AttrPresenceConfig) -> dict[str, Any]:
    serialized_attr_reps = ",".join(str(attr) for attr in presence_config.attr_reps)
    if presence_config.include:
        return {"attributes": serialized_attr_reps}
    return {"excludeAttributes": serialized_attr_reps}


class ResourcesPOST(_AttributesDeserializer):
    pass


class ResourceObjectGET(_AttributesDeserializer):
    pass


class ResourceObjectPUT(_AttributesDeserializer):
    pass


class ResourceObjectPATCH(_AttributesDeserializer):
    pass


class ServerRootResourcesGET(QueryHandler):
    def __init__(self, config: ServiceProviderConfig):
        super().__init__(config)
        self._schema = create_search_request_schema(self.config)

    def deserialize(
        self, query_params: Optional[MutableMapping[str, Any]] = None
    ) -> dict[str, Any]:
        query_params = query_params or {}
        additional_params = SCIMData(query_params)

        input_ = SCIMData(query_params)
        for attr_rep, attr in self._schema.attrs:
            additional_params.pop(attr_rep)

        deserialized = self._schema.deserialize(input_).to_dict()
        deserialized.update(additional_params.to_dict())
        return deserialized

    def serialize(self, query_params: Optional[MutableMapping[str, Any]]) -> dict[str, Any]:
        query_params = query_params or {}
        serialized = {}
        presence_config = query_params.get("presence_config")
        if isinstance(presence_config, AttrPresenceConfig):
            serialized.update(_serialize_presence_config(presence_config))

        filter_ = query_params.get("filter")
        if isinstance(filter_, Filter):
            if not self.config.filter.supported:
                raise RuntimeError("service provider does not support filtering")
            serialized["filter"] = filter_.serialize()

        sorter = query_params.get("sorter")
        if isinstance(sorter, Sorter):
            if not self.config.sort.supported:
                raise RuntimeError("service provider does not support sorting")
            serialized["sortBy"] = str(sorter.attr_rep)
            serialized["sortOrder"] = "ascending" if sorter.asc else "descending"

        count = query_params.get("count")
        if isinstance(count, int):
            serialized["count"] = count

        start_index = query_params.get("startIndex")
        if isinstance(start_index, int):
            serialized["startIndex"] = start_index

        return serialized


class ResourcesGET(ServerRootResourcesGET):
    pass
