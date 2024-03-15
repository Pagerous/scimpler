import pytest

from src.assets.schemas.user import User
from src.data.container import AttrRep, Invalid, SCIMDataContainer
from src.sorter import Sorter
from tests.conftest import SchemaForTests


@pytest.mark.parametrize(
    "sort_by",
    (
        "userName",
        "name.givenName",
        "urn:ietf:params:scim:schemas:core:2.0:User:userName",
        "urn:ietf:params:scim:schemas:core:2.0:User:name.givenName",
        "emails",
        "urn:ietf:params:scim:schemas:core:2.0:User:emails",
    ),
)
def test_sorter_is_parsed(sort_by):
    sorter, issues = Sorter.parse(by=sort_by)

    assert issues.to_dict(msg=True) == {}
    assert sorter is not None


def test_sorter_parsing_fails_with_schema():
    expected = {"_errors": [{"code": 111}]}
    sorter, issues = Sorter.parse(by="bad.attr.name")

    assert sorter is Invalid
    assert issues.to_dict() == expected


def test_items_are_sorted_according_to_attr_value():
    sorter = Sorter(AttrRep.parse("userName"), asc=True)
    c_1 = SCIMDataContainer({"userName": "C", "id": "2"})
    c_2 = SCIMDataContainer({"userName": "A", "id": "3"})
    c_3 = SCIMDataContainer({"userName": "B", "id": "1"})

    values = [c_1, c_2, c_3]
    expected = [c_2, c_3, c_1]

    actual = sorter(values, schema=User())

    assert actual == expected


def test_items_with_missing_value_for_attr_are_sorted_last_for_asc():
    sorter = Sorter(AttrRep.parse("userName"), asc=True)
    c_1 = SCIMDataContainer({"urn:ietf:params:scim:schemas:core:2.0:User:userName": "C", "id": "2"})
    c_2 = SCIMDataContainer({"userName": "A", "id": "3"})
    c_3 = SCIMDataContainer({"id": "1"})
    values = [c_1, c_2, c_3]
    expected = [c_2, c_1, c_3]

    actual = sorter(values, schema=User())

    assert actual == expected


def test_items_with_missing_value_for_attr_are_sorted_first_for_desc():
    sorter = Sorter(AttrRep.parse("userName"), asc=False)
    c_1 = SCIMDataContainer({"userName": "C", "id": "2"})
    c_2 = SCIMDataContainer({"userName": "A", "id": "3"})
    c_3 = SCIMDataContainer({"id": "1"})
    values = [c_1, c_2, c_3]
    expected = [c_3, c_1, c_2]

    actual = sorter(values, schema=User())

    assert actual == expected


def test_original_order_is_preserved_if_no_values_for_all_items():
    sorter = Sorter(AttrRep.parse("userName"))
    c_1 = SCIMDataContainer({"id": "2"})
    c_2 = SCIMDataContainer({"id": "3"})
    c_3 = SCIMDataContainer({"id": "1"})
    values = [c_1, c_2, c_3]
    expected = [c_1, c_2, c_3]

    actual = sorter(values, schema=User())

    assert actual == expected


def test_values_are_sorted_according_to_first_value_for_multivalued_non_complex_attrs():
    sorter = Sorter(AttrRep.parse("str_mv"), asc=True)
    c_1 = SCIMDataContainer({"str_mv": [7, 1, 9]})
    c_2 = SCIMDataContainer({"str_mv": [1, 8, 2]})
    c_3 = SCIMDataContainer({"str_mv": [4, 3, 6]})
    values = [c_1, c_2, c_3]
    expected = [c_2, c_3, c_1]

    actual = sorter(values, schema=SchemaForTests())

    assert actual == expected


def test_items_are_sorted_according_to_sub_attr_value():
    sorter = Sorter(AttrRep.parse("name.givenName"), asc=True)
    c_1 = SCIMDataContainer(
        {"urn:ietf:params:scim:schemas:core:2.0:User:name": {"givenName": "C"}, "id": "2"}
    )
    c_2 = SCIMDataContainer({"name": {"givenName": "A"}, "id": "3"})
    c_3 = SCIMDataContainer({"name": {"givenName": "B"}, "id": "1"})
    values = [c_1, c_2, c_3]

    expected = [c_2, c_3, c_1]

    actual = sorter(values, schema=User())

    assert actual == expected


def test_items_with_missing_value_for_sub_attr_are_sorted_last_for_asc():
    sorter = Sorter(AttrRep.parse("name.givenName"), asc=True)
    c_1 = SCIMDataContainer({"name": {"givenName": "C"}, "id": "2"})
    c_2 = SCIMDataContainer({"id": "3"})
    c_3 = SCIMDataContainer({"name": {"givenName": "B"}, "id": "1"})
    values = [c_1, c_2, c_3]
    expected = [c_3, c_1, c_2]

    actual = sorter(values, schema=User())

    assert actual == expected


def test_items_with_missing_value_for_sub_attr_are_sorted_first_for_desc():
    sorter = Sorter(AttrRep.parse("name.givenName"), asc=False)
    c_1 = SCIMDataContainer({"name": {"givenName": "C"}, "id": "2"})
    c_2 = SCIMDataContainer({"id": "3"})
    c_3 = SCIMDataContainer({"name": {"givenName": "B"}, "id": "1"})
    values = [c_1, c_2, c_3]
    expected = [c_2, c_1, c_3]

    actual = sorter(values, schema=User())

    assert actual == expected


def test_items_are_sorted_according_to_primary_value_for_complex_multivalued_attrs():
    sorter = Sorter(AttrRep(attr="emails"), asc=True)
    c_1 = SCIMDataContainer(
        {
            "id": "1",
            "emails": [
                {"primary": True, "value": "z@example.com"},
            ],
        }
    )
    c_2 = SCIMDataContainer(
        {
            "id": "2",
            "emails": [
                {"value": "a@example.com"},
            ],
        }
    )
    c_3 = SCIMDataContainer(
        {
            "id": "3",
            "emails": [
                {"primary": True, "value": "a@example.com"},
            ],
        }
    )
    values = [c_1, c_2, c_3]
    expected = [c_3, c_1, c_2]

    actual = sorter(values, schema=User())

    assert actual == expected


def test_case_insensitive_attributes_are_respected_if_schema_provided():
    sorter = Sorter(AttrRep.parse("userName"), asc=True)
    c_1 = SCIMDataContainer({"userName": "C", "id": "2"})
    # 'a' would be after 'C' if case-sensitive
    c_2 = SCIMDataContainer({"userName": "a", "id": "3"})
    c_3 = SCIMDataContainer({"userName": "B", "id": "1"})
    values = [c_1, c_2, c_3]
    expected = [c_2, c_3, c_1]

    actual = sorter(values, schema=User())

    assert actual == expected


def test_case_sensitive_attributes_are_respected_if_schema_provided():
    sorter = Sorter(AttrRep.parse("id"), asc=True)
    c_1 = SCIMDataContainer({"id": "a"})
    c_2 = SCIMDataContainer({"id": "A"})
    c_3 = SCIMDataContainer({"id": "B"})
    values = [c_1, c_2, c_3]
    expected = [c_2, c_3, c_1]

    actual = sorter(values, schema=User())

    assert actual == expected


def test_case_sensitive_match_if_any_of_two_fields_from_different_schemas_is_case_sensitive():
    sorter = Sorter(AttrRep.parse("userName"), asc=False)
    c_1 = SCIMDataContainer({"userName": "A"})
    c_2 = SCIMDataContainer({"userName": "a"})
    c_3 = SCIMDataContainer({"userName": "B"})
    values = [c_1, c_2, c_3]
    expected = [c_3, c_2, c_1]
    schemas = [SchemaForTests(), User(), User()]

    actual = sorter(values, schemas)

    assert actual == expected


def test_fails_if_different_value_types():
    sorter = Sorter(AttrRep.parse("title"), asc=False)
    c_1 = SCIMDataContainer({"title": 1})
    c_2 = SCIMDataContainer({"title": "a"})
    values = [c_1, c_2]
    schemas = [SchemaForTests(), User()]

    with pytest.raises(TypeError):
        sorter(values, schemas)
