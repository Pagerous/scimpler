from datetime import datetime
from typing import List

import pytest

from src.parser.attributes import type as at
from src.parser.attributes.attributes import Attribute, AttributeName, ComplexAttribute
from src.parser.parameters.filter.operator import (
    And,
    ComplexAttributeOperator,
    Contains,
    EndsWith,
    Equal,
    GreaterThan,
    GreaterThanOrEqual,
    LesserThan,
    LesserThanOrEqual,
    MatchStatus,
    Not,
    NotEqual,
    Or,
    Present,
    StartsWith,
)
from src.parser.resource.schemas import ResourceSchema


class SchemaForTests(ResourceSchema):
    def __init__(self):
        super().__init__(
            Attribute(name="int", type_=at.Integer),
            Attribute(name="str", type_=at.String),
            Attribute(name="str_cs", type_=at.String, case_exact=True),
            Attribute(name="str_mv", type_=at.String, multi_valued=True),
            Attribute(name="str_cs_mv", type_=at.String, case_exact=True, multi_valued=True),
            Attribute(name="bool", type_=at.Boolean),
            Attribute(name="datetime", type_=at.DateTime),
            Attribute(name="decimal", type_=at.Decimal),
            Attribute(name="binary", type_=at.Binary),
            Attribute(name="external_ref", type_=at.ExternalReference),
            Attribute(name="uri_ref", type_=at.URIReference),
            Attribute(name="scim_ref", type_=at.SCIMReference),
            ComplexAttribute(
                name="c",
                sub_attributes=[Attribute(name="value", type_=at.String)],
            ),
            ComplexAttribute(
                name="c_mv",
                sub_attributes=[Attribute(name="value", type_=at.String, multi_valued=True)],
                multi_valued=True,
            ),
            ComplexAttribute(
                name="c2",
                sub_attributes=[
                    Attribute(name="str", type_=at.String),
                    Attribute(name="int", type_=at.Integer),
                    Attribute(name="bool", type_=at.Boolean),
                ],
            ),
            ComplexAttribute(
                name="c2_mv",
                sub_attributes=[
                    Attribute(name="str", type_=at.String),
                    Attribute(name="int", type_=at.Integer),
                    Attribute(name="bool", type_=at.Boolean),
                ],
                multi_valued=True,
            ),
        )

    def __repr__(self) -> str:
        return "SchemaForTests"

    @property
    def schemas(self) -> List[str]:
        return ["schema:for:tests"]


@pytest.mark.parametrize(
    ("value", "operator_value", "attr_name", "expected"),
    (
        (1, 1, AttributeName("int"), True),
        (1, 2, AttributeName("int"), False),
        ("a", "a", AttributeName("str_cs"), True),
        ("A", "a", AttributeName("str_cs"), False),
        (True, True, AttributeName("bool"), True),
        (True, False, AttributeName("bool"), False),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            AttributeName("datetime"),
            True,
        ),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 2).isoformat(),
            AttributeName("datetime"),
            False,
        ),
        (3.14, 3.14, AttributeName("decimal"), True),
        (3.14, 3.141, AttributeName("decimal"), False),
        (
            "YQ==",
            "YQ==",
            AttributeName("binary"),
            True,
        ),
        (
            "YQ==",
            "Yg==",
            AttributeName("binary"),
            False,
        ),
        (
            "https://www.example.com",
            "https://www.example.com",
            AttributeName("external_ref"),
            True,
        ),
        (
            "https://www.example.com",
            "https://www.bad_example.com",
            AttributeName("external_ref"),
            False,
        ),
        (
            "whatever/some/location/",
            "whatever/some/location/",
            AttributeName("uri_ref"),
            True,
        ),
        (
            "whatever/some/location/",
            "whatever/some/other/location/",
            AttributeName("uri_ref"),
            False,
        ),
        (
            "Users",
            "Users",
            AttributeName("scim_ref"),
            True,
        ),
        (
            "Users",
            "Groups",
            AttributeName("scim_ref"),
            False,
        ),
    ),
)
def test_equal_operator(value, operator_value, attr_name, expected):
    operator = Equal(attr_name, operator_value)

    actual = operator.match(value, SchemaForTests())

    assert actual == expected


@pytest.mark.parametrize(
    ("value", "operator_value", "attribute_name", "expected"),
    (
        (1, 1, AttributeName("int"), False),
        (1, 2, AttributeName("int"), True),
        ("a", "a", AttributeName("str_cs"), False),
        ("A", "a", AttributeName("str_cs"), True),
        (True, True, AttributeName("bool"), False),
        (True, False, AttributeName("bool"), True),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            AttributeName("datetime"),
            False,
        ),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 2).isoformat(),
            AttributeName("datetime"),
            True,
        ),
        (3.14, 3.14, AttributeName("decimal"), False),
        (3.14, 3.141, AttributeName("decimal"), True),
        (
            "YQ==",
            "YQ==",
            AttributeName("binary"),
            False,
        ),
        (
            "YQ==",
            "Yg==",
            AttributeName("binary"),
            True,
        ),
        (
            "https://www.example.com",
            "https://www.example.com",
            AttributeName("external_ref"),
            False,
        ),
        (
            "https://www.example.com",
            "https://www.bad_example.com",
            AttributeName("external_ref"),
            True,
        ),
        (
            "whatever/some/location/",
            "whatever/some/location/",
            AttributeName("uri_ref"),
            False,
        ),
        (
            "whatever/some/location/",
            "whatever/some/other/location/",
            AttributeName("uri_ref"),
            True,
        ),
        (
            "Users",
            "Users",
            AttributeName("scim_ref"),
            False,
        ),
        (
            "Users",
            "Groups",
            AttributeName("scim_ref"),
            True,
        ),
    ),
)
def test_not_equal_operator(value, operator_value, attribute_name, expected):
    operator = NotEqual(attribute_name, operator_value)

    actual = operator.match(value, SchemaForTests())

    assert actual == expected


@pytest.mark.parametrize(
    ("value", "operator_value", "expected"),
    (
        (1, 1, True),
        (1, 2, False),
        ("a", "a", True),
        ("A", "a", True),
        (True, True, True),
        (True, False, False),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            True,
        ),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 2).isoformat(),
            False,
        ),
        (3.14, 3.14, True),
        (3.14, 3.141, False),
    ),
)
def test_equal_operator_without_schema(value, operator_value, expected):
    operator = Equal(AttributeName("attr"), operator_value)

    actual = operator.match(value)

    assert actual == expected


@pytest.mark.parametrize(
    ("value", "operator_value", "expected"),
    (
        (1, 1, False),
        (1, 2, True),
        ("a", "a", False),
        ("A", "a", True),
        ("a", "b", True),
        (True, True, False),
        (True, False, True),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            False,
        ),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 2).isoformat(),
            True,
        ),
        (3.14, 3.14, False),
        (3.14, 3.141, True),
    ),
)
def test_equal_not_operator_without_schema(value, operator_value, expected):
    operator = NotEqual(AttributeName("attr"), operator_value)

    actual = operator.match(value)

    assert actual == expected


@pytest.mark.parametrize(
    ("value", "operator_value", "attribute_name", "expected"),
    (
        (1, 1, AttributeName("int"), False),
        (2, 1, AttributeName("int"), True),
        ("a", "a", AttributeName("str_cs"), False),
        ("a", "A", AttributeName("str_cs"), True),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            AttributeName("datetime"),
            False,
        ),
        (
            datetime(2023, 10, 10, 21, 27, 2).isoformat(),
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            AttributeName("datetime"),
            True,
        ),
        (3.14, 3.14, AttributeName("decimal"), False),
        (3.141, 3.14, AttributeName("decimal"), True),
    ),
)
def test_greater_than_operator(value, operator_value, attribute_name, expected):
    operator = GreaterThan(attribute_name, operator_value)

    actual = operator.match(value, SchemaForTests())

    assert actual == expected


@pytest.mark.parametrize(
    ("value", "operator_value", "expected"),
    (
        (1, 1, False),
        (2, 1, True),
        ("a", "a", False),
        ("a", "A", True),
        ("A", "a", False),
        ("b", "a", True),
        ("B", "a", True),
        ("a", "b", False),
        ("a", "B", True),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            False,
        ),
        (
            datetime(2023, 10, 10, 21, 27, 2).isoformat(),
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            True,
        ),
        (3.14, 3.14, False),
        (3.141, 3.14, True),
    ),
)
def test_greater_than_operator_without_schema(value, operator_value, expected):
    operator = GreaterThan(AttributeName("attr"), operator_value)

    actual = operator.match(value)

    assert actual == expected


@pytest.mark.parametrize(
    ("value", "operator_value", "attribute_name", "expected"),
    (
        (1, 2, AttributeName("int"), False),
        (1, 1, AttributeName("int"), True),
        (2, 1, AttributeName("int"), True),
        ("A", "a", AttributeName("str_cs"), False),
        ("a", "a", AttributeName("str_cs"), True),
        ("a", "A", AttributeName("str_cs"), True),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 2).isoformat(),
            AttributeName("datetime"),
            False,
        ),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            AttributeName("datetime"),
            True,
        ),
        (
            datetime(2023, 10, 10, 21, 27, 2).isoformat(),
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            AttributeName("datetime"),
            True,
        ),
        (3.14, 3.141, AttributeName("decimal"), False),
        (3.14, 3.14, AttributeName("decimal"), True),
        (3.141, 3.14, AttributeName("decimal"), True),
    ),
)
def test_greater_than_or_equal_operator(value, operator_value, attribute_name, expected):
    operator = GreaterThanOrEqual(attribute_name, operator_value)

    actual = operator.match(value, SchemaForTests())

    assert actual == expected


@pytest.mark.parametrize(
    ("value", "operator_value", "expected"),
    (
        (1, 2, False),
        (1, 1, True),
        (2, 1, True),
        ("a", "a", True),
        ("a", "A", True),
        ("A", "a", True),
        ("b", "a", True),
        ("B", "a", True),
        ("a", "b", False),
        ("a", "B", True),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 2).isoformat(),
            False,
        ),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            True,
        ),
        (
            datetime(2023, 10, 10, 21, 27, 2).isoformat(),
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            True,
        ),
        (3.14, 3.141, False),
        (3.14, 3.14, True),
        (3.141, 3.14, True),
    ),
)
def test_greater_than_or_equal_operator_without_schema(value, operator_value, expected):
    operator = GreaterThanOrEqual(AttributeName("attr"), operator_value)

    actual = operator.match(value)

    assert actual == expected


@pytest.mark.parametrize(
    ("value", "operator_value", "attribute_name", "expected"),
    (
        (1, 1, AttributeName("int"), False),
        (1, 2, AttributeName("int"), True),
        ("a", "a", AttributeName("str_cs"), False),
        ("A", "a", AttributeName("str_cs"), True),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            AttributeName("datetime"),
            False,
        ),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 2).isoformat(),
            AttributeName("datetime"),
            True,
        ),
        (3.14, 3.14, AttributeName("decimal"), False),
        (3.14, 3.141, AttributeName("decimal"), True),
    ),
)
def test_lesser_than_operator(value, operator_value, attribute_name, expected):
    operator = LesserThan(attribute_name, operator_value)

    actual = operator.match(value, SchemaForTests())

    assert actual == expected


@pytest.mark.parametrize(
    ("value", "operator_value", "expected"),
    (
        (1, 1, False),
        (1, 2, True),
        ("a", "a", False),
        ("a", "A", False),
        ("A", "a", True),
        ("b", "a", False),
        ("B", "a", True),
        ("a", "b", True),
        ("a", "B", True),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            False,
        ),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 2).isoformat(),
            True,
        ),
        (3.14, 3.14, False),
        (3.14, 3.141, True),
    ),
)
def test_lesser_than_operator_without_schema(value, operator_value, expected):
    operator = LesserThan(AttributeName("attr"), operator_value)

    actual = operator.match(value)

    assert actual == expected


@pytest.mark.parametrize(
    ("value", "operator_value", "attribute_name", "expected"),
    (
        (1, 2, AttributeName("int"), True),
        (1, 1, AttributeName("int"), True),
        (2, 1, AttributeName("int"), False),
        ("A", "a", AttributeName("str_cs"), True),
        ("a", "a", AttributeName("str_cs"), True),
        ("a", "A", AttributeName("str_cs"), False),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 2).isoformat(),
            AttributeName("datetime"),
            True,
        ),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            AttributeName("datetime"),
            True,
        ),
        (
            datetime(2023, 10, 10, 21, 27, 2).isoformat(),
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            AttributeName("datetime"),
            False,
        ),
        (3.14, 3.141, AttributeName("decimal"), True),
        (3.14, 3.14, AttributeName("decimal"), True),
        (3.141, 3.14, AttributeName("decimal"), False),
    ),
)
def test_lesser_than_or_equal_operator(value, operator_value, attribute_name, expected):
    operator = LesserThanOrEqual(attribute_name, operator_value)

    actual = operator.match(value, SchemaForTests())

    assert actual == expected


@pytest.mark.parametrize(
    ("value", "operator_value", "expected"),
    (
        (1, 2, True),
        (1, 1, True),
        (2, 1, False),
        ("a", "a", True),
        ("a", "A", True),
        ("A", "a", True),
        ("b", "a", False),
        ("B", "a", True),
        ("a", "b", True),
        ("a", "B", True),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 2).isoformat(),
            True,
        ),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            True,
        ),
        (
            datetime(2023, 10, 10, 21, 27, 2).isoformat(),
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            False,
        ),
        (3.14, 3.141, True),
        (3.14, 3.14, True),
        (3.141, 3.1, False),
    ),
)
def test_lesser_than_or_equal_operator_without_schema(value, operator_value, expected):
    operator = LesserThanOrEqual(AttributeName("attr"), operator_value)

    actual = operator.match(value)

    assert actual == expected


def test_binary_operator_does_not_match_if_non_matching_attribute_type():
    operator = Equal(AttributeName("int"), "1")

    match = operator.match(1, SchemaForTests())

    assert not match


def test_binary_operator_does_not_match_if_attr_missing_in_schema():
    operator = Equal(AttributeName("other_int"), 1)

    match = operator.match(1, SchemaForTests())

    assert not match


def test_binary_operator_does_not_match_if_not_supported_scim_type():
    operator = GreaterThan(AttributeName("scim_ref"), chr(0))

    match = operator.match("Users", SchemaForTests())

    assert not match


@pytest.mark.parametrize(
    ("operator_cls", "expected"),
    (
        (Contains, True),
        (EndsWith, True),
        (Equal, True),
        (GreaterThan, False),
        (GreaterThanOrEqual, True),
        (LesserThan, False),
        (LesserThanOrEqual, True),
        (NotEqual, False),
        (StartsWith, True),
    ),
)
def test_case_insensitive_attributes_are_compared_correctly(operator_cls, expected):
    operator = operator_cls(AttributeName("str"), "A")

    actual = operator.match("a", SchemaForTests())

    assert actual == expected


@pytest.mark.parametrize(
    ("value", "operator_value", "expected"),
    (
        ("abc", "ab", True),
        ("abc", "bc", True),
        ("abc", "cd", False),
        ("ab", "abc", False),
    ),
)
def test_contains_operator(value, operator_value, expected):
    operator = Contains(AttributeName("str_cs"), operator_value)

    actual = operator.match(value, SchemaForTests())

    assert actual == expected


@pytest.mark.parametrize(
    ("value", "operator_value", "expected"),
    (
        ("abc", "ab", True),
        ("abc", "bc", True),
        ("abc", "cd", False),
        ("ab", "abc", False),
        ("Abc", "ab", True),
        ("aBC", "bc", True),
        ("abc", "aB", True),
        ("abc", "Bc", True),
    ),
)
def test_contains_operator_without_schema(value, operator_value, expected):
    operator = Contains(AttributeName("attr"), operator_value)

    actual = operator.match(value)

    assert actual == expected


@pytest.mark.parametrize(
    ("value", "operator_value", "expected"),
    (
        ("abc", "ab", True),
        ("abc", "bc", False),
        ("abc", "cd", False),
        ("ab", "abc", False),
        ("ab", "", True),
    ),
)
def test_starts_with_operator(value, operator_value, expected):
    operator = StartsWith(AttributeName("str_cs"), operator_value)

    actual = operator.match(value, SchemaForTests())

    assert actual == expected


@pytest.mark.parametrize(
    ("value", "operator_value", "expected"),
    (
        ("abc", "ab", True),
        ("abc", "bc", False),
        ("abc", "cd", False),
        ("ab", "abc", False),
        ("ab", "", True),
        ("abc", "Ab", True),
        ("aBC", "ab", True),
    ),
)
def test_starts_with_operator_without_schema(value, operator_value, expected):
    operator = StartsWith(AttributeName("attr"), operator_value)

    actual = operator.match(value)

    assert actual == expected


@pytest.mark.parametrize(
    ("value", "operator_value", "expected"),
    (
        ("abc", "ab", False),
        ("abc", "bc", True),
        ("abc", "cd", False),
        ("ab", "abc", False),
        ("ab", "", True),
    ),
)
def test_ends_with_operator(value, operator_value, expected):
    operator = EndsWith(AttributeName("str_cs"), operator_value)

    actual = operator.match(value, SchemaForTests())

    assert actual == expected


@pytest.mark.parametrize(
    ("value", "operator_value", "expected"),
    (
        ("abc", "ab", False),
        ("abc", "bc", True),
        ("abc", "cd", False),
        ("ab", "abc", False),
        ("ab", "", True),
        ("abc", "bC", True),
        ("aBC", "bc", True),
    ),
)
def test_ends_with_operator_without_schema(value, operator_value, expected):
    operator = EndsWith(AttributeName("attr"), operator_value)

    actual = operator.match(value)

    assert actual == expected


def test_multi_value_attribute_is_matched_if_one_of_values_match():
    operator = Equal(AttributeName("str_cs_mv"), "abc")

    match = operator.match(["b", "c", "ab", "abc", "ca"], SchemaForTests())

    assert match


def test_multi_value_attribute_is_matched_if_one_of_values_match_without_schema():
    operator = Equal(AttributeName("attr"), "abc")

    match = operator.match(["b", "c", "ab", "abc", "ca"])

    assert match


def test_multi_value_attribute_is_matched_if_one_of_case_insensitive_values_match():
    operator = Equal(AttributeName("str_mv"), "abc")

    match = operator.match(["b", "c", "ab", "ABc", "ca"], SchemaForTests())

    assert match


@pytest.mark.parametrize(
    ("value", "attribute_name", "expected"),
    (
        ("", AttributeName("str"), False),
        ("abc", AttributeName("str"), True),
        (None, AttributeName("bool"), False),
        (False, AttributeName("bool"), True),
        ([], AttributeName("str_mv"), False),
        (
            ["a", "b", "c"],
            AttributeName("str_mv"),
            True,
        ),
        (
            {
                "value": "",
            },
            AttributeName("c"),
            False,
        ),
        (
            {
                "value": "abc",
            },
            AttributeName("c"),
            False,  # only multivalued complex attributes can be matched
        ),
        (
            [
                {
                    "value": "",
                },
                {
                    "value": "",
                },
            ],
            AttributeName("c_mv"),
            False,
        ),
        (
            [
                {
                    "value": "",
                },
                {
                    "value": "abc",
                },
            ],
            AttributeName("c_mv"),
            True,
        ),
    ),
)
def test_present_operator(value, attribute_name, expected):
    operator = Present(attribute_name)

    actual = operator.match(value, SchemaForTests())

    assert actual == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    (
        ("", False),
        ("abc", True),
        (None, False),
        (False, True),
        ([], False),
        (["a", "b", "c"], True),
        ({"value": ""}, False),
        ({"value": "abc"}, False),  # only multivalued complex attributes can be matched
        ([{"value": ""}, {"value": ""}], False),
        ([{"value": ""}, {"value": "abc"}], True),
    ),
)
def test_present_operator_without_schema(value, expected):
    operator = Present(AttributeName("attr"))

    actual = operator.match(value)

    assert actual == expected


@pytest.mark.parametrize("use_schema", (True, False))
def test_complex_attribute_matches_binary_operator_if_one_of_values_matches(
    use_schema,
):
    schema = SchemaForTests() if use_schema else None
    operator = StartsWith(AttributeName("c_mv"), "abc")

    match = operator.match([{"value": "a"}, {"value": "bac"}, {"value": "abcd"}], schema)

    assert match


@pytest.mark.parametrize("use_schema", (True, False))
def test_complex_attribute_does_not_match_binary_operator_if_not_any_of_values_matches(
    use_schema,
):
    schema = SchemaForTests() if use_schema else None
    operator = StartsWith(AttributeName("c_mv"), "abc")

    match = operator.match([{"value": "a"}, {"value": "bac"}, {"value": "bcdd"}], schema)

    assert not match


@pytest.mark.parametrize(
    ("str_cs_value", "expected"),
    (
        ("a", True),
        ("b", False),
    ),
)
def test_and_operator_matches(str_cs_value, expected):
    operator = And(
        Equal(AttributeName("int"), 1),
        And(
            GreaterThan(AttributeName("decimal"), 1.0),
            NotEqual(AttributeName("str"), "1"),
        ),
        Or(
            Equal(AttributeName("bool"), True),
            StartsWith(AttributeName("str_cs"), "a"),
        ),
    )

    actual = operator.match(
        {
            "int": 1,
            "decimal": 1.1,
            "str": "2",
            "bool": False,
            "str_cs": str_cs_value,
        },
        SchemaForTests(),
    )

    assert actual == expected


@pytest.mark.parametrize(
    ("str_cs_value", "expected"),
    (
        ("a", True),
        ("b", False),
    ),
)
def test_or_operator_matches(str_cs_value, expected):
    operator = Or(
        Equal(AttributeName("int"), 1),
        And(
            GreaterThan(AttributeName("decimal"), 1.0),  # TODO: should work for int 1 as well
            NotEqual(AttributeName("str"), "1"),
        ),
        Or(
            Equal(AttributeName("bool"), True),
            StartsWith(AttributeName("str_cs"), "a"),
        ),
    )

    actual = operator.match(
        {
            "int": 2,
            "decimal": 1.0,
            "str": "1",
            "bool": False,
            "str_cs": str_cs_value,
        },
        SchemaForTests(),
    )

    assert actual == expected


@pytest.mark.parametrize("use_schema", (True, False))
def test_complex_attribute_operator_matches_all_complex_sub_attrs(use_schema):
    schema = SchemaForTests() if use_schema else None
    operator = ComplexAttributeOperator(
        attr_name=AttributeName("c2"),
        sub_operator=And(
            Equal(AttributeName("c2.str"), "admin"),
            GreaterThan(AttributeName("c2.int"), 18),
            NotEqual(AttributeName("c2.bool"), True),
        ),
    )

    match = operator.match({"str": "admin", "int": 19, "bool": False}, schema)

    assert match


@pytest.mark.parametrize("use_schema", (True, False))
def test_complex_attribute_operator_does_not_match_all_complex_sub_attrs(use_schema):
    schema = SchemaForTests() if use_schema else None
    operator = ComplexAttributeOperator(
        attr_name=AttributeName("c2"),
        sub_operator=Or(
            Equal(AttributeName("c2.str"), "admin"),
            GreaterThan(AttributeName("c2.int"), 18),
            NotEqual(AttributeName("c2.bool"), True),
        ),
    )

    match = operator.match({"str": "user", "int": 18, "bool": True}, schema)

    assert not match


@pytest.mark.parametrize("use_schema", (True, False))
def test_complex_attr_op_matches_some_of_sub_attrs_of_multi_valued_complex_attr(
    use_schema,
):
    schema = SchemaForTests() if use_schema else None
    operator = ComplexAttributeOperator(
        attr_name=AttributeName("c2_mv"),
        sub_operator=And(
            Equal(AttributeName("c2_mv.str"), "admin"),
            GreaterThan(AttributeName("c2_mv.int"), 18),
            NotEqual(AttributeName("c2_mv.bool"), True),
        ),
    )

    match = operator.match(
        [
            {"str": "admin", "int": 19, "bool": False},
            {"str": "user", "int": 18, "bool": True},
            {"str": "user", "int": 19, "bool": False},
        ],
        schema,
    )

    assert match


@pytest.mark.parametrize("use_schema", (True, False))
def test_complex_attr_op_does_not_match_any_of_multi_valued_complex_sub_attrs(use_schema):
    schema = SchemaForTests() if use_schema else None
    operator = ComplexAttributeOperator(
        attr_name=AttributeName("c2_mv"),
        sub_operator=Or(
            Equal(AttributeName("c2_mv.str"), "admin"),
            GreaterThan(AttributeName("c2_mv.int"), 18),
            NotEqual(AttributeName("c2_mv.bool"), True),
        ),
    )

    match = operator.match(
        [
            {"str": "user", "int": 16, "bool": True},
            {"str": "customer", "int": 18, "bool": True},
            {"str": "santa-claus", "int": 12, "bool": True},
        ],
        schema,
    )

    assert not match


@pytest.mark.parametrize("use_schema", (True, False))
@pytest.mark.parametrize(
    ("value", "is_multivalued", "expected"),
    (
        (
            {"str": "admin", "int": 19, "bool": False},
            False,
            True,
        ),
        (
            {"str": "user", "int": 18, "bool": True},
            False,
            False,
        ),
        (
            [
                {"str": "admin", "int": 19, "bool": False},
                {"str": "user", "int": 18, "bool": True},
                {"str": "user", "int": 19, "bool": False},
            ],
            True,
            True,
        ),
        (
            [
                {"str": "user", "int": 16, "bool": True},
                {"str": "customer", "int": 18, "bool": True},
                {"str": "santa-claus", "int": 12, "bool": True},
            ],
            True,
            False,
        ),
    ),
)
def test_attribute_operator_matches_single_complex_sub_attr(
    use_schema, value, is_multivalued, expected
):
    schema = SchemaForTests() if use_schema else None
    if is_multivalued:
        operator = ComplexAttributeOperator(
            attr_name=AttributeName("c2_mv"),
            sub_operator=Equal(AttributeName("c2_mv.str"), "admin"),
        )
    else:
        operator = ComplexAttributeOperator(
            attr_name=AttributeName("c2"),
            sub_operator=Equal(AttributeName("c2.str"), "admin"),
        )

    actual = operator.match(value, schema)

    assert actual == expected


@pytest.mark.parametrize("use_schema", (True, False))
def test_binary_op_returns_missing_data_if_no_value_provided_with_strict(use_schema):
    schema = SchemaForTests() if use_schema else None
    operator = Equal(AttributeName("str"), "abc")

    match = operator.match(None, schema, True)

    assert match.status == MatchStatus.MISSING_DATA


@pytest.mark.parametrize("use_schema", (True, False))
def test_binary_op_returns_matches_if_no_value_provided_without_strict(use_schema):
    schema = SchemaForTests() if use_schema else None
    operator = Equal(AttributeName("str"), "abc")

    match = operator.match(None, schema, False)

    assert match


@pytest.mark.parametrize("use_schema", (True, False))
def test_complex_op_matches_if_sub_attr_value_not_provided_without_strict(use_schema):
    schema = SchemaForTests() if use_schema else None
    operator = ComplexAttributeOperator(
        attr_name=AttributeName("c"),
        sub_operator=Equal(AttributeName("c.str"), "abc"),
    )

    match = operator.match({}, schema, False)

    assert match


@pytest.mark.parametrize("use_schema", (True, False))
def test_complex_op_does_not_matches_if_sub_attribute_not_provided_with_strict(
    use_schema,
):
    schema = SchemaForTests() if use_schema else None
    operator = ComplexAttributeOperator(
        attr_name=AttributeName("c"),
        sub_operator=Equal(AttributeName("c.str"), "abc"),
    )

    match = operator.match({}, schema, True)

    assert not match


@pytest.mark.parametrize("use_schema", (True, False))
def test_or_op_returns_missing_data_if_no_sub_attr_matched_with_strict(use_schema):
    schema = SchemaForTests() if use_schema else None
    operator = Or(
        Equal(AttributeName("int"), 1),
        Equal(AttributeName("str"), "abc"),
    )

    match = operator.match({"int": 2}, schema, True)

    assert match.status == MatchStatus.MISSING_DATA


@pytest.mark.parametrize("strict", (True, False))
@pytest.mark.parametrize("use_schema", (True, False))
def test_or_op_matches_if_any_sub_attr_matched(strict, use_schema):
    schema = SchemaForTests() if use_schema else None
    operator = Or(
        Equal(AttributeName("int"), 1),
        Equal(AttributeName("str"), "abc"),
    )

    match = operator.match({"int": 1}, schema, strict)

    assert match


@pytest.mark.parametrize("use_schema", (True, False))
def test_and_op_returns_missing_data_if_any_sub_attr_is_without_data_with_strict(
    use_schema,
):
    schema = SchemaForTests() if use_schema else None
    operator = And(
        Equal(AttributeName("int"), 1),
        Equal(AttributeName("str"), "abc"),
    )
    value = {"int": 1}  # value for this attr is correct, but missing 'str'

    match = operator.match(value, schema, True)

    assert match.status == MatchStatus.MISSING_DATA


@pytest.mark.parametrize("use_schema", (True, False))
def test_and_op_does_not_match_if_any_sub_attr_does_not_match_with_strict(use_schema):
    schema = SchemaForTests() if use_schema else None
    operator = And(
        Equal(AttributeName("int"), 1),
        Equal(AttributeName("str"), "abc"),
    )

    match = operator.match({"int": 1, "str": "cba"}, schema, True)

    assert not match


@pytest.mark.parametrize("use_schema", (True, False))
def test_and_operator_matches_if_non_of_sub_attrs_fail_without_strict(use_schema):
    schema = SchemaForTests() if use_schema else None
    operator = And(
        Equal(AttributeName("int"), 1),
        Equal(
            AttributeName("str"),
            "abc",
        ),
    )
    value = {"int": 1}  # value for this attr is correct, 'str' is missing, but no strict

    match = operator.match(value, schema, False)

    assert match


@pytest.mark.parametrize("use_schema", (True, False))
def test_not_op_matches_for_missing_value_in_logical_sub_op_without_strict(use_schema):
    schema = SchemaForTests() if use_schema else None
    operator = Not(
        Or(
            Equal(AttributeName("int"), 1),
            Equal(AttributeName("str"), "abc"),
        ),
    )

    match = operator.match({"int": 2}, schema, False)

    assert match


@pytest.mark.parametrize("use_schema", (True, False))
def test_not_op_does_not_match_for_missing_value_in_logical_sub_op_with_strict(
    use_schema,
):
    schema = SchemaForTests() if use_schema else None
    operator = Not(
        Or(
            Equal(AttributeName("int"), 1),
            Equal(AttributeName("str"), "abc"),
        ),
    )

    match = operator.match({"int": 2}, schema, True)

    assert not match


@pytest.mark.parametrize("use_schema", (True, False))
def test_not_op_matches_for_missing_value_in_attr_sub_op_without_strict(use_schema):
    schema = SchemaForTests() if use_schema else None
    operator = Not(Equal(AttributeName("int"), 1))

    match = operator.match({}, schema, False)

    assert match


@pytest.mark.parametrize("use_schema", (True, False))
def test_not_op_does_not_match_for_missing_value_in_attr_sub_op_with_strict(use_schema):
    schema = SchemaForTests() if use_schema else None
    operator = Not(Equal(AttributeName("int"), 1))

    match = operator.match({}, schema, True)

    assert not match


def test_not_op_does_not_match_if_op_attr_not_in_attrs():
    operator = Not(Equal(AttributeName("other_attr"), 1))

    match = operator.match({"other_attr": 2}, SchemaForTests())

    assert not match


@pytest.mark.parametrize("strict", (True, False))
def test_not_op_matches_if_no_data_for_pr_sub_op_with_strict(strict):
    operator = Not(Present(AttributeName("int")))

    match = operator.match({}, SchemaForTests(), strict)

    assert match


@pytest.mark.parametrize("strict", (True, False))
@pytest.mark.parametrize("use_schema", (True, False))
@pytest.mark.parametrize(("value", "expected"), ((1.0, True), (2.0, False)))
def test_binary_attributes_allows_to_compare_int_with_decimal(strict, use_schema, value, expected):
    schema = SchemaForTests() if use_schema else None
    operator = Equal(AttributeName("decimal"), 1)

    match = operator.match(value, schema, strict)

    assert bool(match) is expected


@pytest.mark.parametrize("strict", (True, False))
@pytest.mark.parametrize("use_schema", (True, False))
@pytest.mark.parametrize(("value", "expected"), ((1, True), (2, False)))
def test_binary_attributes_allows_to_compare_decimal_with_int(strict, use_schema, value, expected):
    schema = SchemaForTests() if use_schema else None
    operator = Equal(AttributeName("int"), 1.0)

    match = operator.match(value, schema, strict)

    assert bool(match) is expected


@pytest.mark.parametrize("use_schema", (True, False))
def test_complex_op_can_be_used_with_logical_op(use_schema):
    schema = SchemaForTests() if use_schema else None
    operator = ComplexAttributeOperator(
        attr_name=AttributeName("c2"),
        sub_operator=And(Equal(AttributeName("int"), 1), Equal(AttributeName("str"), "abc")),
    )

    match = operator.match({"int": 1, "str": "abc"}, schema)

    assert match


@pytest.mark.parametrize("use_schema", (True, False))
def test_complex_op_used_with_or_op_matches_if_at_least_one_sub_attr_matches(use_schema):
    schema = SchemaForTests() if use_schema else None
    operator = ComplexAttributeOperator(
        attr_name=AttributeName("c2"),
        sub_operator=Or(Equal(AttributeName("int"), 1), Equal(AttributeName("str"), "abc")),
    )

    match = operator.match({"int": 1}, schema)

    assert match


@pytest.mark.parametrize("use_schema", (True, False))
def test_complex_op_used_with_or_op_does_not_match_if_no_values_provided(use_schema):
    schema = SchemaForTests() if use_schema else None
    operator = ComplexAttributeOperator(
        attr_name=AttributeName("c2"),
        sub_operator=Or(Equal(AttributeName("int"), 1), Equal(AttributeName("str"), "abc")),
    )

    match = operator.match({}, schema)

    assert not match


@pytest.mark.parametrize("use_schema", (True, False))
def test_complex_op_used_with_or_op_matches_if_no_values_provided_without_strict(use_schema):
    schema = SchemaForTests() if use_schema else None
    operator = ComplexAttributeOperator(
        attr_name=AttributeName("c2"),
        sub_operator=Or(Equal(AttributeName("int"), 1), Equal(AttributeName("str"), "abc")),
    )

    match = operator.match({}, schema, False)

    assert match


@pytest.mark.parametrize("use_schema", (True, False))
def test_multivalued_complex_op_can_be_used_with_logical_op(use_schema):
    schema = SchemaForTests() if use_schema else None
    operator = ComplexAttributeOperator(
        attr_name=AttributeName("c2_mv"),
        sub_operator=And(Equal(AttributeName("int"), 1), Equal(AttributeName("str"), "abc")),
    )

    match = operator.match(
        [{"int": 2, "str": "abc"}, {"int": 1, "str": "cba"}, {"int": 1, "str": "abc"}], schema
    )

    assert match
