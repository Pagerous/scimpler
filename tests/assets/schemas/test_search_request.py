from src.assets.schemas.search_request import SearchRequest
from src.data.container import AttrRep


def test_search_request_is_parsed():
    schema = SearchRequest()

    data = schema.parse(
        {
            "attributes": ["userName", "name"],
            "filter": 'userName eq "bjensen"',
            "sortBy": "name.familyName",
            "sortOrder": "descending",
            "startIndex": 2,
            "count": 10,
        }
    )

    assert data.get("presence_checker").attr_reps == [
        AttrRep(attr="userName"),
        AttrRep(attr="name"),
    ]
    assert data.get("presence_checker").include is True
    assert data.get("filter").to_dict() == {
        "op": "eq",
        "attr_rep": "userName",
        "value": "bjensen",
    }
    assert data.get("sorter").attr_rep == AttrRep(attr="name", sub_attr="familyName")
    assert data.get("sorter").asc is False
    assert data.get("startIndex") == 2
    assert data.get("count") == 10
