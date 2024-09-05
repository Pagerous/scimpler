import pytest

from scimpler.data.filter import Filter
from scimpler.identifiers import AttrRep
from scimpler.query_handler import (
    ResourceObjectGET,
    ResourceObjectPATCH,
    ResourceObjectPUT,
    ResourcesPOST,
    ServerRootResourcesGET,
)
from tests.conftest import CONFIG


@pytest.mark.parametrize(
    "deserializer",
    (
        ResourceObjectGET(CONFIG),
        ResourcesPOST(CONFIG),
        ResourceObjectPUT(CONFIG),
        ResourceObjectPATCH(CONFIG),
    ),
)
def test_presence_config_is_deserialized_from_query_params(deserializer):
    deserialized = deserializer.deserialize(query_params={"attributes": ["name.familyName"]})

    assert deserialized.get("attributes") == [AttrRep(attr="name", sub_attr="familyName")]


def test_server_root_resources_get_query_params_is_deserialized():
    data = ServerRootResourcesGET(CONFIG).deserialize(
        {
            "attributes": ["userName", "name"],
            "filter": 'userName eq "bjensen"',
            "sortBy": "name.familyName",
            "sortOrder": "descending",
            "startIndex": 2,
            "count": 10,
        }
    )

    assert data.get("attributes") == [AttrRep(attr="userName"), AttrRep(attr="name")]
    assert data.get("filter") == Filter.deserialize("userName eq 'bjensen'")
    assert data.get("sortBy") == AttrRep(attr="name", sub_attr="familyName")
    assert data.get("sortOrder") == "descending"
    assert data.get("startIndex") == 2
    assert data.get("count") == 10
