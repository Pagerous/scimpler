import pytest

from src.data.container import AttrRep
from src.query_parser import (
    ResourceObjectGET,
    ResourceObjectPATCH,
    ResourceObjectPUT,
    ResourcesPOST,
    ServerRootResourcesGET,
)
from tests.conftest import CONFIG


@pytest.mark.parametrize(
    "parser",
    (
        ResourceObjectGET(CONFIG),
        ResourcesPOST(CONFIG),
        ResourceObjectPUT(CONFIG),
        ResourceObjectPATCH(CONFIG),
    ),
)
def test_presence_checker_is_parsed_from_query_string(parser):
    parsed = parser.parse(query_string={"attributes": ["name.familyName"]})

    assert parsed["presence_checker"].attr_reps == [AttrRep(attr="name", sub_attr="familyName")]
    assert parsed["presence_checker"].include is True


def test_server_root_resources_get_query_string_is_parsed():
    data = ServerRootResourcesGET(CONFIG).parse(
        {
            "attributes": ["userName", "name"],
            "filter": 'userName eq "bjensen"',
            "sortBy": "name.familyName",
            "sortOrder": "descending",
            "startIndex": 2,
            "count": 10,
        }
    )

    assert data["presence_checker"].attr_reps == [
        AttrRep(attr="userName"),
        AttrRep(attr="name"),
    ]
    assert data["presence_checker"].include is True
    assert data["filter"].to_dict() == {
        "op": "eq",
        "attr_rep": "userName",
        "value": "bjensen",
    }
    assert data["sorter"].attr_rep == AttrRep(attr="name", sub_attr="familyName")
    assert data["sorter"].asc is False
    assert data["startIndex"] == 2
    assert data["count"] == 10
