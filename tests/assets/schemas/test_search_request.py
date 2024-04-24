from src.assets.schemas.search_request import SearchRequest
from src.data.container import BoundedAttrRep


def test_search_request_is_deserialized():
    schema = SearchRequest()

    data = schema.deserialize(
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
        BoundedAttrRep(attr="userName"),
        BoundedAttrRep(attr="name"),
    ]
    assert data.get("presence_checker").include is True
    assert data.get("filter").to_dict() == {
        "op": "eq",
        "attr_rep": "userName",
        "value": "bjensen",
    }
    assert data.get("sorter").attr_rep == BoundedAttrRep(attr="name", sub_attr="familyName")
    assert data.get("sorter").asc is False
    assert data.get("startIndex") == 2
    assert data.get("count") == 10
