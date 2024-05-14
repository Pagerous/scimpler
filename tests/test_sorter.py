import pytest

from src.assets.schemas.user import User
from src.container import BoundedAttrRep, SCIMDataContainer
from src.sorter import Sorter
from tests.conftest import SchemaForTests


def test_items_are_sorted_according_to_attr_value():
    sorter = Sorter(BoundedAttrRep(attr="userName"), asc=True)
    c_1 = SCIMDataContainer({"userName": "C", "id": "2"})
    c_2 = SCIMDataContainer({"userName": "A", "id": "3"})
    c_3 = SCIMDataContainer({"userName": "B", "id": "1"})

    values = [c_1, c_2, c_3]
    expected = [c_2, c_3, c_1]

    actual = sorter(values, schema=User)

    assert actual == expected


def test_items_with_missing_value_for_attr_are_sorted_last_for_asc():
    sorter = Sorter(BoundedAttrRep(attr="userName"), asc=True)
    c_1 = SCIMDataContainer({"urn:ietf:params:scim:schemas:core:2.0:User:userName": "C", "id": "2"})
    c_2 = SCIMDataContainer({"userName": "A", "id": "3"})
    c_3 = SCIMDataContainer({"id": "1"})
    values = [c_1, c_2, c_3]
    expected = [c_2, c_1, c_3]

    actual = sorter(values, schema=User)

    assert actual == expected


def test_items_with_missing_value_for_attr_are_sorted_first_for_desc():
    sorter = Sorter(BoundedAttrRep(attr="userName"), asc=False)
    c_1 = SCIMDataContainer({"userName": "C", "id": "2"})
    c_2 = SCIMDataContainer({"userName": "A", "id": "3"})
    c_3 = SCIMDataContainer({"id": "1"})
    values = [c_1, c_2, c_3]
    expected = [c_3, c_1, c_2]

    actual = sorter(values, schema=User)

    assert actual == expected


def test_original_order_is_preserved_if_no_values_for_all_items():
    sorter = Sorter(BoundedAttrRep(attr="userName"))
    c_1 = SCIMDataContainer({"id": "2"})
    c_2 = SCIMDataContainer({"id": "3"})
    c_3 = SCIMDataContainer({"id": "1"})
    values = [c_1, c_2, c_3]
    expected = [c_1, c_2, c_3]

    actual = sorter(values, schema=User)

    assert actual == expected


def test_values_are_sorted_according_to_first_value_for_multivalued_non_complex_attrs():
    sorter = Sorter(BoundedAttrRep(attr="str_mv"), asc=True)
    c_1 = SCIMDataContainer({"str_mv": [7, 1, 9]})
    c_2 = SCIMDataContainer({"str_mv": [1, 8, 2]})
    c_3 = SCIMDataContainer({"str_mv": [4, 3, 6]})
    values = [c_1, c_2, c_3]
    expected = [c_2, c_3, c_1]

    actual = sorter(values, schema=SchemaForTests)

    assert actual == expected


def test_items_are_sorted_according_to_sub_attr_value():
    sorter = Sorter(BoundedAttrRep(attr="name", sub_attr="givenName"), asc=True)
    c_1 = SCIMDataContainer(
        {"urn:ietf:params:scim:schemas:core:2.0:User:name": {"givenName": "C"}, "id": "2"}
    )
    c_2 = SCIMDataContainer({"name": {"givenName": "A"}, "id": "3"})
    c_3 = SCIMDataContainer({"name": {"givenName": "B"}, "id": "1"})
    values = [c_1, c_2, c_3]

    expected = [c_2, c_3, c_1]

    actual = sorter(values, schema=User)

    assert actual == expected


def test_items_with_missing_value_for_sub_attr_are_sorted_last_for_asc():
    sorter = Sorter(BoundedAttrRep(attr="name", sub_attr="givenName"), asc=True)
    c_1 = SCIMDataContainer({"name": {"givenName": "C"}, "id": "2"})
    c_2 = SCIMDataContainer({"id": "3"})
    c_3 = SCIMDataContainer({"name": {"givenName": "B"}, "id": "1"})
    values = [c_1, c_2, c_3]
    expected = [c_3, c_1, c_2]

    actual = sorter(values, schema=User)

    assert actual == expected


def test_items_with_missing_value_for_sub_attr_are_sorted_first_for_desc():
    sorter = Sorter(BoundedAttrRep(attr="name", sub_attr="givenName"), asc=False)
    c_1 = SCIMDataContainer({"name": {"givenName": "C"}, "id": "2"})
    c_2 = SCIMDataContainer({"id": "3"})
    c_3 = SCIMDataContainer({"name": {"givenName": "B"}, "id": "1"})
    values = [c_1, c_2, c_3]
    expected = [c_2, c_1, c_3]

    actual = sorter(values, schema=User)

    assert actual == expected


def test_items_are_sorted_according_to_primary_value_for_complex_multivalued_attrs():
    sorter = Sorter(BoundedAttrRep(attr="emails"), asc=True)
    c_1 = SCIMDataContainer(
        {
            "id": "1",
            "emails": [{"primary": True, "value": "z@example.com"}, {"value": "b@example.com"}],
        }
    )
    c_2 = SCIMDataContainer(
        {
            "id": "2",
            "emails": [
                {"value": "c@example.com"},
            ],
        }
    )
    c_3 = SCIMDataContainer(
        {
            "id": "3",
            "emails": [{"primary": True, "value": "a@example.com"}, {"value": "z@example.com"}],
        }
    )
    c_4 = SCIMDataContainer({"id": "4", "emails": []})
    values = [c_1, c_4, c_2, c_3]
    expected = [c_3, c_2, c_1, c_4]

    actual = sorter(values, schema=User)

    assert actual == expected


def test_case_insensitive_attributes_are_respected_if_schema_provided():
    sorter = Sorter(BoundedAttrRep(attr="userName"), asc=True)
    c_1 = SCIMDataContainer({"userName": "C", "id": "2"})
    # 'a' would be after 'C' if case-sensitive
    c_2 = SCIMDataContainer({"userName": "a", "id": "3"})
    c_3 = SCIMDataContainer({"userName": "B", "id": "1"})
    values = [c_1, c_2, c_3]
    expected = [c_2, c_3, c_1]

    actual = sorter(values, schema=User)

    assert actual == expected


def test_case_sensitive_attributes_are_respected_if_schema_provided():
    sorter = Sorter(BoundedAttrRep(attr="id"), asc=True)
    c_1 = SCIMDataContainer({"id": "a"})
    c_2 = SCIMDataContainer({"id": "A"})
    c_3 = SCIMDataContainer({"id": "B"})
    values = [c_1, c_2, c_3]
    expected = [c_2, c_3, c_1]

    actual = sorter(values, schema=User)

    assert actual == expected


def test_case_sensitive_match_if_any_of_two_fields_from_different_schemas_is_case_sensitive():
    sorter = Sorter(BoundedAttrRep(attr="userName"), asc=False)
    c_1 = SCIMDataContainer({"userName": "A"})
    c_2 = SCIMDataContainer({"userName": "a"})
    c_3 = SCIMDataContainer({"userName": "B"})
    values = [c_1, c_2, c_3]
    expected = [c_3, c_2, c_1]
    schemas = [SchemaForTests, User, User]

    actual = sorter(values, schemas)

    assert actual == expected


def test_fails_if_different_value_types():
    sorter = Sorter(BoundedAttrRep(attr="title"), asc=False)
    c_1 = SCIMDataContainer({"title": 1})
    c_2 = SCIMDataContainer({"title": "a"})
    values = [c_1, c_2]
    schemas = [SchemaForTests, User]

    with pytest.raises(TypeError):
        sorter(values, schemas)
