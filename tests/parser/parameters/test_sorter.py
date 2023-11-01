import pytest

from src.parser.attributes.attributes import AttributeName
from src.parser.parameters.sorter import Sorter
from src.parser.resource.schemas import USER
from tests.parser.conftest import SCHEMA_FOR_TESTS


@pytest.mark.parametrize(
    "sort_by",
    (
        "userName",
        "name.givenName",
        "urn:ietf:params:scim:schemas:core:2.0:User:userName",
        "urn:ietf:params:scim:schemas:core:2.0:User:name.givenName",
        "emails",  # complex, multivalued,
        "urn:ietf:params:scim:schemas:core:2.0:User:emails",
    ),
)
def test_sorter_is_parsed(sort_by):
    sorter, issues = Sorter.parse(by=sort_by)

    assert not issues
    assert sorter is not None


def test_sorter_parsing_fails_with_schema():
    expected = {"_errors": [{"code": 111}]}
    sorter, issues = Sorter.parse(by="bad.attr.name")

    assert sorter is None
    assert issues.to_dict() == expected


def test_items_are_sorted_according_to_attr_value():
    sorter = Sorter(AttributeName.parse("userName"), asc=True)
    values = [
        {
            "userName": "C",
            "id": "2",
        },
        {
            "userName": "A",
            "id": "3",
        },
        {
            "userName": "B",
            "id": "1",
        },
    ]
    expected = [
        {
            "userName": "A",
            "id": "3",
        },
        {
            "userName": "B",
            "id": "1",
        },
        {
            "userName": "C",
            "id": "2",
        },
    ]

    actual = sorter(values, schema=USER)

    assert actual == expected


def test_items_with_missing_value_for_attr_are_sorted_last_for_asc():
    sorter = Sorter(AttributeName.parse("userName"), asc=True)
    values = [
        {
            "urn:ietf:params:scim:schemas:core:2.0:User:userName": "C",
            "id": "2",
        },
        {
            "userName": "A",
            "id": "3",
        },
        {
            "id": "1",
        },
    ]
    expected = [
        {
            "userName": "A",
            "id": "3",
        },
        {
            "urn:ietf:params:scim:schemas:core:2.0:User:userName": "C",
            "id": "2",
        },
        {
            "id": "1",
        },
    ]

    actual = sorter(values, schema=USER)

    assert actual == expected


def test_items_with_missing_value_for_attr_are_sorted_first_for_desc():
    sorter = Sorter(AttributeName.parse("userName"), asc=False)
    values = [
        {
            "userName": "C",
            "id": "2",
        },
        {
            "userName": "A",
            "id": "3",
        },
        {
            "id": "1",
        },
    ]
    expected = [
        {
            "id": "1",
        },
        {
            "userName": "C",
            "id": "2",
        },
        {
            "userName": "A",
            "id": "3",
        },
    ]

    actual = sorter(values, schema=USER)

    assert actual == expected


def test_original_order_is_preserved_if_no_values_for_all_items():
    sorter = Sorter(AttributeName.parse("userName"))
    values = [
        {
            "id": "2",
        },
        {
            "id": "3",
        },
        {
            "id": "1",
        },
    ]
    expected = values

    actual = sorter(values, schema=USER)

    assert actual == expected


def test_values_are_sorted_according_to_first_value_for_multivalued_non_complex_attrs():
    sorter = Sorter(AttributeName.parse("str_mv"), asc=True)
    values = [
        {
            "str_mv": [7, 1, 9],
        },
        {
            "str_mv": [1, 8, 2],
        },
        {
            "str_mv": [4, 3, 6],
        },
    ]
    expected = [
        {
            "str_mv": [1, 8, 2],
        },
        {
            "str_mv": [4, 3, 6],
        },
        {
            "str_mv": [7, 1, 9],
        },
    ]

    actual = sorter(values, schema=SCHEMA_FOR_TESTS)

    assert actual == expected


def test_items_are_sorted_according_to_sub_attr_value():
    sorter = Sorter(AttributeName.parse("name.givenName"), asc=True)
    values = [
        {
            "urn:ietf:params:scim:schemas:core:2.0:User:name": {"givenName": "C"},
            "id": "2",
        },
        {
            "name": {"givenName": "A"},
            "id": "3",
        },
        {
            "name": {"givenName": "B"},
            "id": "1",
        },
    ]
    expected = [
        {
            "name": {"givenName": "A"},
            "id": "3",
        },
        {
            "name": {"givenName": "B"},
            "id": "1",
        },
        {
            "urn:ietf:params:scim:schemas:core:2.0:User:name": {"givenName": "C"},
            "id": "2",
        },
    ]

    actual = sorter(values, schema=USER)

    assert actual == expected


def test_items_with_missing_value_for_sub_attr_are_sorted_last_for_asc():
    sorter = Sorter(AttributeName.parse("name.givenName"), asc=True)
    values = [
        {
            "name": {"givenName": "C"},
            "id": "2",
        },
        {
            "id": "3",
        },
        {
            "name": {"givenName": "B"},
            "id": "1",
        },
    ]
    expected = [
        {
            "name": {"givenName": "B"},
            "id": "1",
        },
        {
            "name": {"givenName": "C"},
            "id": "2",
        },
        {
            "id": "3",
        },
    ]

    actual = sorter(values, schema=USER)

    assert actual == expected


def test_items_with_missing_value_for_sub_attr_are_sorted_first_for_desc():
    sorter = Sorter(AttributeName.parse("name.givenName"), asc=False)
    values = [
        {
            "name": {"givenName": "C"},
            "id": "2",
        },
        {
            "id": "3",
        },
        {
            "name": {"givenName": "B"},
            "id": "1",
        },
    ]
    expected = [
        {
            "id": "3",
        },
        {
            "name": {"givenName": "C"},
            "id": "2",
        },
        {
            "name": {"givenName": "B"},
            "id": "1",
        },
    ]

    actual = sorter(values, schema=USER)

    assert actual == expected


def test_items_are_sorted_according_to_primary_value_for_complex_multivalued_attrs():
    sorter = Sorter(AttributeName(attr="emails"), asc=True)
    values = [
        {
            "id": "1",
            "emails": [
                {"primary": True, "value": "z@example.com"},
            ],
        },
        {
            "id": "2",
            "emails": [
                {"value": "a@example.com"},
            ],
        },
        {
            "id": "3",
            "emails": [
                {"primary": True, "value": "a@example.com"},
            ],
        },
    ]
    expected = [
        {
            "id": "3",
            "emails": [
                {"primary": True, "value": "a@example.com"},
            ],
        },
        {
            "id": "1",
            "emails": [
                {"primary": True, "value": "z@example.com"},
            ],
        },
        {
            "id": "2",
            "emails": [
                {"value": "a@example.com"},
            ],
        },
    ]

    actual = sorter(values, schema=USER)

    assert actual == expected


def test_case_insensitive_attributes_are_respected_if_schema_provided():
    sorter = Sorter(AttributeName.parse("userName"), asc=True)
    values = [
        {
            "userName": "C",
            "id": "2",
        },
        {
            "userName": "a",  # 'a' would be after 'C' if case-sensitive
            "id": "3",
        },
        {
            "userName": "B",
            "id": "1",
        },
    ]
    expected = [
        {
            "userName": "a",
            "id": "3",
        },
        {
            "userName": "B",
            "id": "1",
        },
        {
            "userName": "C",
            "id": "2",
        },
    ]

    actual = sorter(values, schema=USER)

    assert actual == expected


def test_case_sensitive_attributes_are_respected_if_schema_provided():
    sorter = Sorter(AttributeName.parse("id"), asc=True)
    values = [
        {
            "id": "a",
        },
        {
            "id": "A",
        },
        {
            "id": "B",
        },
    ]
    expected = [
        {
            "id": "A",
        },
        {
            "id": "B",
        },
        {
            "id": "a",
        },
    ]

    actual = sorter(values, schema=USER)

    assert actual == expected
