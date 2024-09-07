from scimpler.config import ServiceProviderConfig
from scimpler.data.filter import Filter
from scimpler.data.identifiers import AttrRep
from scimpler.schemas.search_request import SearchRequestSchema


def test_search_request_attrs_are_deserialized():
    schema = SearchRequestSchema()

    data = schema.deserialize({"attributes": ["userName", "name"]})

    assert data.get("attributes") == [AttrRep(attr="userName"), AttrRep(attr="name")]


def test_search_request_sorting_deserialized():
    schema = SearchRequestSchema()

    data = schema.deserialize({"sortBy": "name.familyName", "sortOrder": "descending"})

    assert data.get("sortBy") == AttrRep(attr="name", sub_attr="familyName")
    assert data.get("sortOrder") == "descending"


def test_full_search_request_is_deserialized():
    schema = SearchRequestSchema()

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

    assert data.get("attributes") == [AttrRep(attr="userName"), AttrRep(attr="name")]
    assert data.get("filter") == Filter.deserialize("userName eq 'bjensen'")
    assert data.get("sortBy") == AttrRep(attr="name", sub_attr="familyName")
    assert data.get("sortOrder") == "descending"
    assert data.get("startIndex") == 1
    assert data.get("count") == 0


def test_search_request_schema_can_exclude_filter_and_sorting():
    schema = SearchRequestSchema.from_config(
        config=ServiceProviderConfig.create(
            filter_={"supported": False},
            sort={"supported": False},
        )
    )

    assert getattr(schema.attrs, "filter", None) is None
    assert getattr(schema.attrs, "sortBy", None) is None
    assert getattr(schema.attrs, "sortOrder", None) is None


def test_search_request_schema_can_include_filter_and_sorting():
    schema = SearchRequestSchema.from_config(
        config=ServiceProviderConfig.create(
            filter_={"supported": True, "max_results": 100},
            sort={"supported": True},
        )
    )

    assert getattr(schema.attrs, "filter", None) is not None
    assert getattr(schema.attrs, "sortBy", None) is not None
    assert getattr(schema.attrs, "sortOrder", None) is not None
