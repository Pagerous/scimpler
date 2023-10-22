import pytest

from src.parser.attributes.attributes import AttributeName
from src.parser.parameters.sorter.sorter import Sorter
from src.parser.resource.schemas import UserSchema


@pytest.mark.parametrize("use_schema", (True, False))
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
def test_sorter_is_parsed(use_schema, sort_by):
    schema = UserSchema() if use_schema else None
    sorter, issues = Sorter.parse(by=sort_by, asc=True, schema=schema)

    assert not issues
    assert sorter is not None


@pytest.mark.parametrize(
    ("sort_by", "expected_issues"),
    (
        ("bad.attr.name", {"_errors": [{"code": 111}]}),
        ("non_existing.attr", {"_errors": [{"code": 200}]}),
        ("name", {"_errors": [{"code": 201}, {"code": 202}]}),
    ),
)
def test_sorter_parsing_fails_with_schema(sort_by, expected_issues):
    sorter, issues = Sorter.parse(by=sort_by, asc=True, schema=UserSchema())

    assert sorter is None
    assert issues.to_dict() == expected_issues


@pytest.mark.parametrize(
    ("sort_by", "expected_issues"),
    (
        ("bad.attr.name", {"_errors": [{"code": 111}]}),
        ("non_existing.attr", {}),
        ("name", {}),
    ),
)
def test_sorter_parsing_fails_without_schema(sort_by, expected_issues):
    sorter, issues = Sorter.parse(by=sort_by, asc=True, schema=None)

    assert issues.to_dict() == expected_issues


def test_sorter_can_not_be_created_if_no_attr_in_schema():
    with pytest.raises(ValueError):
        Sorter(AttributeName("non_existing.attr"), schema=UserSchema())


def test_sorter_can_not_be_created_if_no_sub_attr_in_schema():
    with pytest.raises(ValueError):
        Sorter(AttributeName("name.non_existing"), schema=UserSchema())


def test_sorter_can_not_be_created_if_complex_attr_is_not_multivalued():
    with pytest.raises(TypeError):
        Sorter(AttributeName("name"), schema=UserSchema())


def test_sorter_can_not_be_created_if_complex_multivalued_attr_has_no_primary_or_value_sub_attr():
    with pytest.raises(TypeError):
        Sorter(AttributeName("addresses"), schema=UserSchema())


def test_items_are_sorted_according_to_attr_value():
    sorter = Sorter(AttributeName("userName"), schema=UserSchema(), asc=True)
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

    actual = sorter(values)

    assert actual == expected


def test_items_with_missing_value_for_attr_are_sorted_last_for_asc():
    sorter = Sorter(AttributeName("userName"), schema=UserSchema(), asc=True)
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

    actual = sorter(values)

    assert actual == expected


def test_items_with_missing_value_for_attr_are_sorted_first_for_desc():
    sorter = Sorter(AttributeName("userName"), schema=UserSchema(), asc=False)
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

    actual = sorter(values)

    assert actual == expected


@pytest.mark.parametrize("use_schema", (True, False))
def test_original_order_is_preserved_if_no_values_for_all_items(use_schema):
    schema = UserSchema() if use_schema else None
    sorter = Sorter(AttributeName("userName"), schema=schema)
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

    actual = sorter(values)

    assert actual == expected


def test_values_are_sorted_according_to_first_value_for_multivalued_non_complex_attrs():
    sorter = Sorter(AttributeName("some_attr"), schema=None, asc=True)
    values = [
        {
            "some_attr": [7, 1, 9],
        },
        {
            "some_attr": [1, 8, 2],
        },
        {
            "some_attr": [4, 3, 6],
        },
    ]
    expected = [
        {
            "some_attr": [1, 8, 2],
        },
        {
            "some_attr": [4, 3, 6],
        },
        {
            "some_attr": [7, 1, 9],
        },
    ]

    actual = sorter(values)

    assert actual == expected


def test_items_are_sorted_according_to_sub_attr_value():
    sorter = Sorter(AttributeName("name.givenName"), schema=UserSchema(), asc=True)
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

    actual = sorter(values)

    assert actual == expected


def test_items_with_missing_value_for_sub_attr_are_sorted_last_for_asc():
    sorter = Sorter(AttributeName("name.givenName"), schema=UserSchema(), asc=True)
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

    actual = sorter(values)

    assert actual == expected


def test_items_with_missing_value_for_sub_attr_are_sorted_first_for_desc():
    sorter = Sorter(AttributeName("name.givenName"), schema=UserSchema(), asc=False)
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

    actual = sorter(values)

    assert actual == expected


@pytest.mark.parametrize("use_schema", (True, False))
def test_items_are_sorted_according_to_primary_value_for_complex_multivalued_attrs(
    use_schema,
):
    schema = UserSchema() if use_schema else None
    sorter = Sorter(AttributeName("emails"), schema=schema, asc=True)
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

    actual = sorter(values)

    assert actual == expected


def test_case_insensitive_attributes_are_respected_if_schema_provided():
    sorter = Sorter(AttributeName("userName"), schema=UserSchema(), asc=True)
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

    actual = sorter(values)

    assert actual == expected


def test_case_sensitive_attributes_are_respected_if_schema_provided():
    sorter = Sorter(AttributeName("id"), schema=UserSchema(), asc=True)
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

    actual = sorter(values)

    assert actual == expected


def test_string_values_are_sorted_less_strictly_when_schema_not_provided():
    sorter = Sorter(AttributeName("userName"), schema=None, asc=True, strict=False)
    values = [
        {
            "userName": "B",
            "id": "2",
        },
        {
            "userName": "aa",
            "id": 4,
        },
        {
            "userName": "a",
            "id": "3",
        },
        {
            "userName": "A",
            "id": "1",
        },
    ]
    expected = [
        {
            "userName": "B",
            "id": "2",
        },
        {
            "userName": "a",
            "id": "3",
        },
        {
            "userName": "A",
            "id": "1",
        },
        {
            "userName": "aa",
            "id": 4,
        },
    ]

    actual = sorter(values)

    assert actual == expected


def test_string_values_are_sorted_strictly_when_schema_not_provided():
    sorter = Sorter(AttributeName("userName"), schema=None, asc=True, strict=True)
    values = [
        {
            "userName": "C",
            "id": "2",
        },
        {
            "userName": "aa",
            "id": "3",
        },
        {
            "userName": "A",
            "id": "1",
        },
    ]
    expected = [
        {
            "userName": "A",
            "id": "1",
        },
        {
            "userName": "C",
            "id": "2",
        },
        {
            "userName": "aa",
            "id": "3",
        },
    ]

    actual = sorter(values)

    assert actual == expected
