from src.config import create_service_provider_config
from src.assets.schemas.search_request import (
    SearchRequest,
    create_search_request_schema,
)
from src.container import AttrRep


def test_search_request_attrs_are_deserialized():
    schema = SearchRequest()

    data = schema.deserialize({"attributes": ["userName", "name"]})

    assert data.get("presence_config").attr_reps == [AttrRep(attr="userName"), AttrRep(attr="name")]
    assert data.get("presence_config").include is True


def test_search_request_sorting_deserialized():
    schema = SearchRequest()

    data = schema.deserialize({"sortBy": "name.familyName", "sortOrder": "descending"})

    assert data.get("sorter").attr_rep == AttrRep(attr="name", sub_attr="familyName")
    assert data.get("sorter").asc is False


def test_full_search_request_is_deserialized():
    schema = SearchRequest()

    data = schema.deserialize(
        {
            "attributes": ["userName", "name"],
            "filter": 'userName eq "bjensen"',
            "sortBy": "name.familyName",
            "sortOrder": "descending",
            "startIndex": 0,
            "count": -1,
        }
    )

    assert data.get("presence_config").attr_reps == [
        AttrRep(attr="userName"),
        AttrRep(attr="name"),
    ]
    assert data.get("presence_config").include is True
    assert data.get("filter").to_dict() == {
        "op": "eq",
        "attr": "userName",
        "value": "bjensen",
    }
    assert data.get("sorter").attr_rep == AttrRep(attr="name", sub_attr="familyName")
    assert data.get("sorter").asc is False
    assert data.get("startIndex") == 1
    assert data.get("count") == 0


def test_search_request_schema_can_exclude_filter_and_sorting():
    schema = create_search_request_schema(
        config=create_service_provider_config(
            filter_={"supported": False},
            sort={"supported": False},
        )
    )

    assert getattr(schema.attrs, "filter", None) is None
    assert getattr(schema.attrs, "sortBy", None) is None
    assert getattr(schema.attrs, "sortOrder", None) is None


def test_search_request_schema_can_include_filter_and_sorting():
    schema = create_search_request_schema(
        config=create_service_provider_config(
            filter_={"supported": True, "max_results": 100},
            sort={"supported": True},
        )
    )

    assert getattr(schema.attrs, "filter", None) is not None
    assert getattr(schema.attrs, "sortBy", None) is not None
    assert getattr(schema.attrs, "sortOrder", None) is not None
