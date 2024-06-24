import pytest

from src.assets.schemas.user import User
from src.container import AttrRep, SCIMData
from src.data.attrs import SCIMReference, String
from src.data.sorter import AlwaysLastKey, Sorter, StringKey
from tests.conftest import SchemaForTests


def test_items_are_sorted_according_to_attr_value():
    sorter = Sorter(AttrRep(attr="userName"), asc=True)
    c_1 = SCIMData({"userName": "C", "id": "2"})
    c_2 = SCIMData({"userName": "A", "id": "3"})
    c_3 = SCIMData({"userName": "B", "id": "1"})

    values = [c_1, c_2, c_3]
    expected = [c_2, c_3, c_1]

    actual = sorter(values, schema=User)

    assert actual == expected


def test_items_with_missing_value_for_attr_are_sorted_last_for_asc():
    sorter = Sorter(AttrRep(attr="userName"), asc=True)
    c_1 = SCIMData({"urn:ietf:params:scim:schemas:core:2.0:User:userName": "C", "id": "2"})
    c_2 = SCIMData({"userName": "A", "id": "3"})
    c_3 = SCIMData({"id": "1"})
    values = [c_1, c_2, c_3]
    expected = [c_2, c_1, c_3]

    actual = sorter(values, schema=User)

    assert actual == expected


def test_items_with_missing_value_for_attr_are_sorted_first_for_desc():
    sorter = Sorter(AttrRep(attr="userName"), asc=False)
    c_1 = SCIMData({"userName": "C", "id": "2"})
    c_2 = SCIMData({"userName": "A", "id": "3"})
    c_3 = SCIMData({"id": "1"})
    values = [c_1, c_2, c_3]
    expected = [c_3, c_1, c_2]

    actual = sorter(values, schema=User)

    assert actual == expected


def test_original_order_is_preserved_if_no_values_for_all_items():
    sorter = Sorter(AttrRep(attr="userName"))
    c_1 = SCIMData({"id": "2"})
    c_2 = SCIMData({"id": "3"})
    c_3 = SCIMData({"id": "1"})
    values = [c_1, c_2, c_3]
    expected = [c_1, c_2, c_3]

    actual = sorter(values, schema=User)

    assert actual == expected


def test_values_are_sorted_according_to_first_value_for_multivalued_non_complex_attrs():
    sorter = Sorter(AttrRep(attr="str_mv"), asc=True)
    c_1 = SCIMData({"str_mv": [7, 1, 9]})
    c_2 = SCIMData({"str_mv": [1, 8, 2]})
    c_3 = SCIMData({"str_mv": [4, 3, 6]})
    values = [c_1, c_2, c_3]
    expected = [c_2, c_3, c_1]

    actual = sorter(values, schema=SchemaForTests)

    assert actual == expected


def test_items_are_sorted_according_to_sub_attr_value():
    sorter = Sorter(AttrRep(attr="name", sub_attr="givenName"), asc=True)
    c_1 = SCIMData(
        {"urn:ietf:params:scim:schemas:core:2.0:User:name": {"givenName": "C"}, "id": "2"}
    )
    c_2 = SCIMData({"name": {"givenName": "A"}, "id": "3"})
    c_3 = SCIMData({"name": {"givenName": "B"}, "id": "1"})
    values = [c_1, c_2, c_3]

    expected = [c_2, c_3, c_1]

    actual = sorter(values, schema=User)

    assert actual == expected


def test_items_with_missing_value_for_sub_attr_are_sorted_last_for_asc():
    sorter = Sorter(AttrRep(attr="name", sub_attr="givenName"), asc=True)
    c_1 = SCIMData({"name": {"givenName": "C"}, "id": "2"})
    c_2 = SCIMData({"id": "3"})
    c_3 = SCIMData({"name": {"givenName": "B"}, "id": "1"})
    values = [c_1, c_2, c_3]
    expected = [c_3, c_1, c_2]

    actual = sorter(values, schema=User)

    assert actual == expected


def test_items_with_missing_value_for_sub_attr_are_sorted_first_for_desc():
    sorter = Sorter(AttrRep(attr="name", sub_attr="givenName"), asc=False)
    c_1 = SCIMData({"name": {"givenName": "C"}, "id": "2"})
    c_2 = SCIMData({"id": "3"})
    c_3 = SCIMData({"name": {"givenName": "B"}, "id": "1"})
    values = [c_1, c_2, c_3]
    expected = [c_2, c_1, c_3]

    actual = sorter(values, schema=User)

    assert actual == expected


def test_items_are_sorted_according_to_primary_value_for_complex_multivalued_attrs():
    sorter = Sorter(AttrRep(attr="emails"), asc=True)
    c_1 = SCIMData(
        {
            "id": "1",
            "emails": [{"value": "b@example.com"}, {"primary": True, "value": "z@example.com"}],
        }
    )
    c_2 = SCIMData(
        {
            "id": "2",
            "emails": [
                {"value": "c@example.com"},
            ],
        }
    )
    c_3 = SCIMData(
        {
            "id": "3",
            "emails": [{"primary": True, "value": "a@example.com"}, {"value": "z@example.com"}],
        }
    )
    c_4 = SCIMData({"id": "4", "emails": []})
    values = [c_1, c_4, c_2, c_3]
    expected = [c_3, c_2, c_1, c_4]

    actual = sorter(values, schema=User)

    assert actual == expected


def test_items_can_be_sorted_by_complex_sub_attr_if_attr_multivalued():
    sorter = Sorter(AttrRep(attr="emails", sub_attr="value"), asc=True)
    c_1 = SCIMData(
        {
            "id": "1",
            "emails": [{"value": "z@example.com"}, {"value": "b@example.com"}],
        }
    )
    c_2 = SCIMData(
        {
            "id": "2",
            "emails": [
                {"value": "c@example.com"},
            ],
        }
    )
    c_3 = SCIMData(
        {
            "id": "3",
            "emails": [{"value": "a@example.com"}, {"value": "z@example.com"}],
        }
    )
    c_4 = SCIMData({"id": "4", "emails": []})
    values = [c_1, c_4, c_2, c_3]
    expected = [c_3, c_2, c_1, c_4]

    actual = sorter(values, schema=User)

    assert actual == expected


def test_case_insensitive_attributes_are_respected_if_schema_provided():
    sorter = Sorter(AttrRep(attr="userName"), asc=True)
    c_1 = SCIMData({"userName": "C", "id": "2"})
    # 'a' would be after 'C' if case-sensitive
    c_2 = SCIMData({"userName": "a", "id": "3"})
    c_3 = SCIMData({"userName": "B", "id": "1"})
    values = [c_1, c_2, c_3]
    expected = [c_2, c_3, c_1]

    actual = sorter(values, schema=User)

    assert actual == expected


def test_case_sensitive_attributes_are_respected_if_schema_provided():
    sorter = Sorter(AttrRep(attr="id"), asc=True)
    c_1 = SCIMData({"id": "a"})
    c_2 = SCIMData({"id": "A"})
    c_3 = SCIMData({"id": "B"})
    values = [c_1, c_2, c_3]
    expected = [c_2, c_3, c_1]

    actual = sorter(values, schema=User)

    assert actual == expected


def test_case_sensitive_match_if_any_of_two_fields_from_different_schemas_is_case_sensitive():
    sorter = Sorter(AttrRep(attr="userName"), asc=False)
    c_1 = SCIMData({"userName": "A"})
    c_2 = SCIMData({"userName": "a"})
    c_3 = SCIMData({"userName": "B"})
    values = [c_1, c_2, c_3]
    expected = [c_3, c_2, c_1]
    schemas = [SchemaForTests, User, User]

    actual = sorter(values, schemas)

    assert actual == expected


def test_fails_if_different_value_types():
    sorter = Sorter(AttrRep(attr="title"), asc=False)
    c_1 = SCIMData({"title": 1})
    c_2 = SCIMData({"title": "a"})
    values = [c_1, c_2]
    schemas = [SchemaForTests, User]

    with pytest.raises(TypeError):
        sorter(values, schemas)


def test_comparing_string_key_to_always_last_key_returns_true():
    key = StringKey("test", String(name="attr"))
    always_last = AlwaysLastKey()

    assert key < always_last


def test_comparing_string_key_to_string_raises_type_error():
    key = StringKey("test", String(name="attr"))

    with pytest.raises(TypeError, match="'<' not supported"):
        print(key < "key")


def test_string_keys_with_non_string_underlying_attributes_can_be_compared():
    key_1 = StringKey("/Users/1", SCIMReference(name="attr", reference_types=["User"]))
    key_2 = StringKey("/Users/2", SCIMReference(name="attr", reference_types=["User"]))

    assert key_1 < key_2


def test_empty_collection_can_be_passed_to_sorter():
    sorter = Sorter(attr_rep=AttrRep(attr="userName"), asc=False)

    assert sorter([], User) == []


def test_sorter_preserves_input_data_type__container():
    sorter = Sorter(attr_rep=AttrRep(attr="userName"), asc=True)
    data = [SCIMData({"userName": "B"}), SCIMData({"userName": "A"})]
    expected = [SCIMData({"userName": "A"}), SCIMData({"userName": "B"})]

    actual = sorter(data, User)

    assert actual == expected
    assert isinstance(actual[0], SCIMData)


def test_sorter_preserves_input_data_type__dict():
    sorter = Sorter(attr_rep=AttrRep(attr="userName"), asc=True)
    data = [{"userName": "B"}, {"userName": "A"}]
    expected = [{"userName": "A"}, {"userName": "B"}]

    actual = sorter(data, User)

    assert actual == expected
    assert isinstance(actual[0], dict)


def test_data_item_with_string_value_but_for_non_string_attr_is_ordered_last_if_ascending():
    sorter = Sorter(attr_rep=AttrRep(attr="int"), asc=True)
    data = [{"int": "ABC"}, {"int": 10}]
    expected = [{"int": 10}, {"int": "ABC"}]

    actual = sorter(data, SchemaForTests)

    assert actual == expected


def test_data_item_is_ordered_last_if_ascending_if_attr_does_not_exist():
    sorter = Sorter(attr_rep=AttrRep(attr="int"), asc=True)
    data = [{"int": 2}, {"int": 1}]
    expected = [{"int": 2}, {"int": 1}]

    actual = sorter(data, [SchemaForTests, User])

    assert actual == expected
