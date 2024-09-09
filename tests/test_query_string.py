import pytest

from scimpler.data.filter import Filter
from scimpler.data.identifiers import AttrRep
from scimpler.query_string import (
    ResourceObjectGet,
    ResourceObjectPatch,
    ResourceObjectPut,
    ResourcesGet,
    ResourcesPost,
    ResourceTypesGet,
    SchemasGet,
)
from tests.conftest import CONFIG


@pytest.mark.parametrize(
    "deserializer",
    (
        ResourceObjectGet(),
        ResourcesPost(),
        ResourceObjectPut(),
        ResourceObjectPatch(),
    ),
)
def test_presence_config_is_deserialized_from_query_params(deserializer):
    deserialized = deserializer.deserialize(query_params={"attributes": ["name.familyName"]})

    assert deserialized.get("attributes") == [AttrRep(attr="name", sub_attr="familyName")]


def test_resources_get_query_params_is_deserialized():
    data = ResourcesGet(CONFIG).deserialize(
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


def test_resources_get_attributes_query_param_is_deserialized_from_string():
    data = ResourcesGet(CONFIG).deserialize({"attributes": "userName,name"})

    assert data.get("attributes") == [AttrRep(attr="userName"), AttrRep(attr="name")]


def test_resources_get_excluded_attributes_query_param_is_deserialized_from_string():
    data = ResourcesGet(CONFIG).deserialize({"excludedAttributes": "userName,name"})

    assert data.get("excludedAttributes") == [AttrRep(attr="userName"), AttrRep(attr="name")]


def test_resources_get_query_params_is_serialized():
    data = {
        "attributes": [AttrRep(attr="userName"), AttrRep(attr="name")],
        "excludedAttributes": [AttrRep(attr="nickName")],
        "filter": Filter.deserialize("userName eq 'bjensen'"),
        "sortBy": AttrRep("name", "familyName"),
        "sortOrder": "descending",
        "startIndex": 2,
        "count": 10,
    }

    data = ResourcesGet(CONFIG).serialize(data)

    assert data.get("attributes") == "userName,name"
    assert data.get("excludedAttributes") == "nickName"
    assert data.get("filter") == "userName eq 'bjensen'"
    assert data.get("sortBy") == "name.familyName"
    assert data.get("sortOrder") == "descending"
    assert data.get("startIndex") == 2
    assert data.get("count") == 10


def test_resources_get_query_params_is_serialized_without_attributes_and_excluded_attributes():
    data = {
        "filter": Filter.deserialize("userName eq 'bjensen'"),
        "sortBy": AttrRep("name", "familyName"),
        "sortOrder": "descending",
        "startIndex": 2,
        "count": 10,
    }

    data = ResourcesGet(CONFIG).serialize(data)

    assert data.get("filter") == "userName eq 'bjensen'"
    assert data.get("sortBy") == "name.familyName"
    assert data.get("sortOrder") == "descending"
    assert data.get("startIndex") == 2
    assert data.get("count") == 10


def test_resources_get_query_params_is_validated():
    expected_issues = {
        "attributes": {"1": {"_errors": [{"code": 17}]}},
        "filter": {"_errors": [{"code": 104}]},
        "sortBy": {"_errors": [{"code": 17}]},
    }

    issues = ResourcesGet(CONFIG).validate(
        {
            "attributes": ["userName", "bad^attr"],
            "filter": 'userName hehe "bjensen"',
            "sortBy": "emails[type eq 'work']",
        }
    )

    assert issues.to_dict() == expected_issues


@pytest.mark.parametrize("handler", (SchemasGet, ResourceTypesGet))
def test_passing_filter_to_service_provider_config_get_query_handler_fails_on_validation(handler):
    expected_issues = {"filter": {"_errors": [{"code": 31}]}}

    issues = handler(CONFIG).validate(
        {
            "filter": 'userName eq "bjensen"',
        }
    )

    assert issues.to_dict() == expected_issues


@pytest.mark.parametrize("handler", (SchemasGet, ResourceTypesGet))
def test_unknown_params_passed_to_service_provider_config_get_query_handler_validation(handler):
    issues = handler(CONFIG).validate(
        {
            "unknown-param": 42,
        }
    )

    assert issues.to_dict(message=True) == {}
