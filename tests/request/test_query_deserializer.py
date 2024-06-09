import pytest

from src.container import AttrRep
from src.request.query_deserializer import (
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
def test_presence_config_is_deserialized_from_query_string(deserializer):
    deserialized = deserializer.deserialize(query_string={"attributes": ["name.familyName"]})

    assert deserialized["presence_config"].attr_reps == [
        AttrRep(attr="name", sub_attr="familyName")
    ]
    assert deserialized["presence_config"].include is True


def test_server_root_resources_get_query_string_is_deserialized():
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

    assert data["presence_config"].attr_reps == [
        AttrRep(attr="userName"),
        AttrRep(attr="name"),
    ]
    assert data["presence_config"].include is True
    assert data["filter"].to_dict() == {
        "op": "eq",
        "attr_rep": "userName",
        "value": "bjensen",
    }
    assert data["sorter"].attr_rep == AttrRep(attr="name", sub_attr="familyName")
    assert data["sorter"].asc is False
    assert data["startIndex"] == 2
    assert data["count"] == 10
