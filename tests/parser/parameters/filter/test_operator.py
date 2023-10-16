from datetime import datetime

import pytest

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
    NotEqual,
    Or,
    Present,
    StartsWith,
)
from src.parser.attributes.attributes import Attribute, ComplexAttribute
from src.parser.attributes import type as at


@pytest.mark.parametrize(
    ("value", "operator_value", "attribute", "expected"),
    (
        (1, 1, Attribute(name="my_attr", type_=at.Integer), True),
        (1, 2, Attribute(name="my_attr", type_=at.Integer), False),
        ("a", "a", Attribute(name="my_attr", type_=at.String, case_exact=True), True),
        ("A", "a", Attribute(name="my_attr", type_=at.String, case_exact=True), False),
        (True, True, Attribute(name="my_attr", type_=at.Boolean), True),
        (True, False, Attribute(name="my_attr", type_=at.Boolean), False),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            Attribute(name="my_attr", type_=at.DateTime),
            True
        ),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 2).isoformat(),
            Attribute(name="my_attr", type_=at.DateTime),
            False
        ),
        (3.14, 3.14, Attribute(name="my_attr", type_=at.Decimal), True),
        (3.14, 3.141, Attribute(name="my_attr", type_=at.Decimal), False),
        (
            "YQ==",
            "YQ==",
            Attribute(name="my_attr", type_=at.Binary),
            True,
        ),
        (
            "YQ==",
            "Yg==",
            Attribute(name="my_attr", type_=at.Binary),
            False,
        ),
        (
            "https://www.example.com",
            "https://www.example.com",
            Attribute(name="my_attr", type_=at.ExternalReference),
            True,
        ),
        (
            "https://www.example.com",
            "https://www.bad_example.com",
            Attribute(name="my_attr", type_=at.ExternalReference),
            False,
        ),
        (
            "whatever/some/location/",
            "whatever/some/location/",
            Attribute(name="my_attr", type_=at.URIReference),
            True,
        ),
        (
            "whatever/some/location/",
            "whatever/some/other/location/",
            Attribute(name="my_attr", type_=at.URIReference),
            False,
        ),
        (
            "Users",
            "Users",
            Attribute(name="my_attr", type_=at.SCIMReference),
            True,
        ),
        (
            "Users",
            "Groups",
            Attribute(name="my_attr", type_=at.SCIMReference),
            False,
        ),
    )
)
def test_equal_operator(value, operator_value, attribute, expected):
    operator = Equal(attribute.name, operator_value)

    actual = operator.match(value, attribute)

    assert actual is expected


@pytest.mark.parametrize(
    ("value", "operator_value", "attribute", "expected"),
    (
        (1, 1, Attribute(name="my_attr", type_=at.Integer), False),
        (1, 2, Attribute(name="my_attr", type_=at.Integer), True),
        ("a", "a", Attribute(name="my_attr", type_=at.String, case_exact=True), False),
        ("A", "a", Attribute(name="my_attr", type_=at.String, case_exact=True), True),
        (True, True, Attribute(name="my_attr", type_=at.Boolean), False),
        (True, False, Attribute(name="my_attr", type_=at.Boolean), True),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            Attribute(name="my_attr", type_=at.DateTime),
            False
        ),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 2).isoformat(),
            Attribute(name="my_attr", type_=at.DateTime),
            True
        ),
        (3.14, 3.14, Attribute(name="my_attr", type_=at.Decimal), False),
        (3.14, 3.141, Attribute(name="my_attr", type_=at.Decimal), True),
        (
            "YQ==",
            "YQ==",
            Attribute(name="my_attr", type_=at.Binary),
            False,
        ),
        (
            "YQ==",
            "Yg==",
            Attribute(name="my_attr", type_=at.Binary),
            True,
        ),
        (
            "https://www.example.com",
            "https://www.example.com",
            Attribute(name="my_attr", type_=at.ExternalReference),
            False,
        ),
        (
            "https://www.example.com",
            "https://www.bad_example.com",
            Attribute(name="my_attr", type_=at.ExternalReference),
            True,
        ),
        (
            "whatever/some/location/",
            "whatever/some/location/",
            Attribute(name="my_attr", type_=at.URIReference),
            False,
        ),
        (
            "whatever/some/location/",
            "whatever/some/other/location/",
            Attribute(name="my_attr", type_=at.URIReference),
            True,
        ),
        (
            "Users",
            "Users",
            Attribute(name="my_attr", type_=at.SCIMReference),
            False,
        ),
        (
            "Users",
            "Groups",
            Attribute(name="my_attr", type_=at.SCIMReference),
            True,
        ),
    )
)
def test_not_equal_operator(value, operator_value, attribute, expected):
    operator = NotEqual(attribute.name, operator_value)

    actual = operator.match(value, attribute)

    assert actual is expected


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
            True
        ),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 2).isoformat(),
            False
        ),
        (3.14, 3.14, True),
        (3.14, 3.141, False),
    )
)
def test_equal_operator_without_attribute(value, operator_value, expected):
    operator = Equal("my_attr", operator_value)

    actual = operator.match(value, None)

    assert actual is expected


@pytest.mark.parametrize(
    ("value", "operator_value", "expected"),
    (
        (1, 1, False),
        (1, 2, True),
        ("a", "a", True),  # ignored
        ("A", "a", True),  # ignored
        (True, True, False),
        (True, False, True),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            False
        ),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 2).isoformat(),
            True
        ),
        (3.14, 3.14, False),
        (3.14, 3.141, True),
    )
)
def test_equal_not_operator_without_attribute(value, operator_value, expected):
    operator = NotEqual("my_attr", operator_value)

    actual = operator.match(value, None)

    assert actual is expected


@pytest.mark.parametrize(
    ("value", "operator_value", "attribute", "expected"),
    (
        (1, 1, Attribute(name="my_attr", type_=at.Integer), False),
        (2, 1, Attribute(name="my_attr", type_=at.Integer), True),
        ("a", "a", Attribute(name="my_attr", type_=at.String, case_exact=True), False),
        ("a", "A", Attribute(name="my_attr", type_=at.String, case_exact=True), True),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            Attribute(name="my_attr", type_=at.DateTime),
            False,
        ),
        (
            datetime(2023, 10, 10, 21, 27, 2).isoformat(),
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            Attribute(name="my_attr", type_=at.DateTime),
            True
        ),
        (3.14, 3.14, Attribute(name="my_attr", type_=at.Decimal), False),
        (3.141, 3.14, Attribute(name="my_attr", type_=at.Decimal), True),
    )
)
def test_greater_than_operator(value, operator_value, attribute, expected):
    operator = GreaterThan(attribute.name, operator_value)

    actual = operator.match(value, attribute)

    assert actual is expected


@pytest.mark.parametrize(
    ("value", "operator_value", "expected"),
    (
        (1, 1, False),
        (2, 1, True),
        ("a", "a", True),
        ("a", "A", True),
        ("A", "a", True),
        ("b", "a", True),
        ("B", "a", True),
        ("a", "b", True),
        ("a", "B", True),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            False,
        ),
        (
            datetime(2023, 10, 10, 21, 27, 2).isoformat(),
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            True
        ),
        (3.14, 3.14, False),
        (3.141, 3.14, True),
    )
)
def test_greater_than_operator_without_attribute(value, operator_value, expected):
    operator = GreaterThan("my_attr", operator_value)

    actual = operator.match(value, None)

    assert actual is expected


@pytest.mark.parametrize(
    ("value", "operator_value", "attribute", "expected"),
    (
        (1, 2, Attribute(name="my_attr", type_=at.Integer), False),
        (1, 1, Attribute(name="my_attr", type_=at.Integer), True),
        (2, 1, Attribute(name="my_attr", type_=at.Integer), True),
        ("A", "a", Attribute(name="my_attr", type_=at.String, case_exact=True), False),
        ("a", "a", Attribute(name="my_attr", type_=at.String, case_exact=True), True),
        ("a", "A", Attribute(name="my_attr", type_=at.String, case_exact=True), True),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 2).isoformat(),
            Attribute(name="my_attr", type_=at.DateTime),
            False,
        ),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            Attribute(name="my_attr", type_=at.DateTime),
            True,
        ),
        (
            datetime(2023, 10, 10, 21, 27, 2).isoformat(),
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            Attribute(name="my_attr", type_=at.DateTime),
            True
        ),
        (3.14, 3.141, Attribute(name="my_attr", type_=at.Decimal), False),
        (3.14, 3.14, Attribute(name="my_attr", type_=at.Decimal), True),
        (3.141, 3.14, Attribute(name="my_attr", type_=at.Decimal), True),
    )
)
def test_greater_than_or_equal_operator(value, operator_value, attribute, expected):
    operator = GreaterThanOrEqual(attribute.name, operator_value)

    actual = operator.match(value, attribute)

    assert actual is expected


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
        ("a", "b", True),
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
            True
        ),
        (3.14, 3.141, False),
        (3.14, 3.14, True),
        (3.141, 3.14, True),
    )
)
def test_greater_than_or_equal_operator_without_attribute(value, operator_value, expected):
    operator = GreaterThanOrEqual("my_attr", operator_value)

    actual = operator.match(value, None)

    assert actual is expected


@pytest.mark.parametrize(
    ("value", "operator_value", "attribute", "expected"),
    (
        (1, 1, Attribute(name="my_attr", type_=at.Integer), False),
        (1, 2, Attribute(name="my_attr", type_=at.Integer), True),
        ("a", "a", Attribute(name="my_attr", type_=at.String, case_exact=True), False),
        ("A", "a", Attribute(name="my_attr", type_=at.String, case_exact=True), True),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            Attribute(name="my_attr", type_=at.DateTime),
            False,
        ),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 2).isoformat(),
            Attribute(name="my_attr", type_=at.DateTime),
            True
        ),
        (3.14, 3.14, Attribute(name="my_attr", type_=at.Decimal), False),
        (3.14, 3.141, Attribute(name="my_attr", type_=at.Decimal), True),
    )
)
def test_lesser_than_operator(value, operator_value, attribute, expected):
    operator = LesserThan(attribute.name, operator_value)

    actual = operator.match(value, attribute)

    assert actual is expected


@pytest.mark.parametrize(
    ("value", "operator_value", "expected"),
    (
        (1, 1, False),
        (1, 2, True),
        ("a", "a", True),
        ("a", "A", True),
        ("A", "a", True),
        ("b", "a", True),
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
            True
        ),
        (3.14, 3.14, False),
        (3.14, 3.141, True),
    )
)
def test_lesser_than_operator_without_attribute(value, operator_value, expected):
    operator = LesserThan("my_attr", operator_value)

    actual = operator.match(value, None)

    assert actual is expected


@pytest.mark.parametrize(
    ("value", "operator_value", "attribute", "expected"),
    (
        (1, 2, Attribute(name="my_attr", type_=at.Integer), True),
        (1, 1, Attribute(name="my_attr", type_=at.Integer), True),
        (2, 1, Attribute(name="my_attr", type_=at.Integer), False),
        ("A", "a", Attribute(name="my_attr", type_=at.String, case_exact=True), True),
        ("a", "a", Attribute(name="my_attr", type_=at.String, case_exact=True), True),
        ("a", "A", Attribute(name="my_attr", type_=at.String, case_exact=True), False),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 2).isoformat(),
            Attribute(name="my_attr", type_=at.DateTime),
            True,
        ),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            Attribute(name="my_attr", type_=at.DateTime),
            True,
        ),
        (
            datetime(2023, 10, 10, 21, 27, 2).isoformat(),
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            Attribute(name="my_attr", type_=at.DateTime),
            False
        ),
        (3.14, 3.141, Attribute(name="my_attr", type_=at.Decimal), True),
        (3.14, 3.14, Attribute(name="my_attr", type_=at.Decimal), True),
        (3.141, 3.14, Attribute(name="my_attr", type_=at.Decimal), False),
    )
)
def test_lesser_than_or_equal_operator(value, operator_value, attribute, expected):
    operator = LesserThanOrEqual(attribute.name, operator_value)

    actual = operator.match(value, attribute)

    assert actual is expected


@pytest.mark.parametrize(
    ("value", "operator_value", "expected"),
    (
        (1, 2, True),
        (1, 1, True),
        (2, 1, False),
        ("a", "a", True),
        ("a", "A", True),
        ("A", "a", True),
        ("b", "a", True),
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
            False
        ),
        (3.14, 3.141, True),
        (3.14, 3.14, True),
        (3.141, 3.1, False),
    )
)
def test_lesser_than_or_equal_operator_without_attribute(
    value, operator_value, expected
):
    operator = LesserThanOrEqual("my_attr", operator_value)

    actual = operator.match(value, None)

    assert actual is expected


def test_binary_operator_does_not_match_if_non_matching_attribute_type():
    attribute = Attribute(name="my_attr", type_=at.Integer)
    operator = Equal(attr_name="my_attr", value="1")

    match = operator.match(1, attribute)

    assert not match


def test_binary_operator_does_not_match_if_non_matching_attribute_name():
    attribute = Attribute(name="my_attr", type_=at.Integer)
    operator = Equal(attr_name="other_attr", value=1)

    match = operator.match(1, attribute)

    assert not match


def test_binary_operator_does_not_match_if_not_supported_scim_type():
    attribute = Attribute(name="my_attr", type_=at.SCIMReference)
    operator = GreaterThan(attr_name="other_attr", value="whatever")

    match = operator.match("Users", attribute)

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
    )
)
def test_case_insensitive_attributes_are_compared_correctly(operator_cls, expected):
    attribute = Attribute(name="my_attr", type_=at.String, case_exact=False)
    operator = operator_cls("my_attr", "A")

    actual = operator.match("a", attribute)

    assert actual is expected


@pytest.mark.parametrize(
    ("value", "operator_value", "expected"),
    (
        ("abc", "ab", True),
        ("abc", "bc", True),
        ("abc", "cd", False),
        ("ab", "abc", False)
    )
)
def test_contains_operator(value, operator_value, expected):
    attribute = Attribute(name="my_attr", type_=at.String, case_exact=True)
    operator = Contains("my_attr", operator_value)

    actual = operator.match(value, attribute)

    assert actual is expected


@pytest.mark.parametrize(
    ("value", "operator_value", "expected"),
    (
        ("abc", "ab", True),
        ("abc", "bc", True),
        ("abc", "cd", True),
        ("ab", "abc", True)
    )
)
def test_contains_operator_without_attribute(value, operator_value, expected):
    operator = Contains("my_attr", operator_value)

    actual = operator.match(value, None)

    assert actual is expected


@pytest.mark.parametrize(
    ("value", "operator_value", "expected"),
    (
        ("abc", "ab", True),
        ("abc", "bc", False),
        ("abc", "cd", False),
        ("ab", "abc", False),
        ("ab", "", True),
    )
)
def test_starts_with_operator(value, operator_value, expected):
    attribute = Attribute(name="my_attr", type_=at.String, case_exact=True)
    operator = StartsWith("my_attr", operator_value)

    actual = operator.match(value, attribute)

    assert actual is expected


@pytest.mark.parametrize(
    ("value", "operator_value", "expected"),
    (
        ("abc", "ab", True),
        ("abc", "bc", True),
        ("abc", "cd", True),
        ("ab", "abc", True),
        ("ab", "", True),
    )
)
def test_starts_with_operator_without_attribute(value, operator_value, expected):
    operator = StartsWith("my_attr", operator_value)

    actual = operator.match(value, None)

    assert actual is expected


@pytest.mark.parametrize(
    ("value", "operator_value", "expected"),
    (
        ("abc", "ab", False),
        ("abc", "bc", True),
        ("abc", "cd", False),
        ("ab", "abc", False),
        ("ab", "", True),
    )
)
def test_ends_with_operator(value, operator_value, expected):
    attribute = Attribute(name="my_attr", type_=at.String, case_exact=True)
    operator = EndsWith("my_attr", operator_value)

    actual = operator.match(value, attribute)

    assert actual is expected


@pytest.mark.parametrize(
    ("value", "operator_value", "expected"),
    (
        ("abc", "ab", True),
        ("abc", "bc", True),
        ("abc", "cd", True),
        ("ab", "abc", True),
        ("ab", "", True),
    )
)
def test_ends_with_operator_without_attribute(value, operator_value, expected):
    operator = EndsWith("my_attr", operator_value)

    actual = operator.match(value, None)

    assert actual is expected


def test_multi_value_attribute_is_matched_if_one_of_values_match():
    attribute = Attribute(name="my_attr", type_=at.String, case_exact=True, multi_valued=True)
    operator = Equal("my_attr", "abc")

    match = operator.match(["b", "c", "ab", "abc", "ca"], attribute)

    assert match


def test_multi_value_attribute_is_matched_if_one_of_values_match_without_attribute():
    operator = Equal("my_attr", "abc")

    match = operator.match(["b", "c", "ab", "abc", "ca"], None)

    assert match


def test_multi_value_attribute_is_matched_if_one_of_case_insensitive_values_match():
    attribute = Attribute(name="my_attr", type_=at.String, case_exact=False, multi_valued=True)
    operator = Equal("my_attr", "abc")

    match = operator.match(["b", "c", "ab", "ABc", "ca"], attribute)

    assert match


@pytest.mark.parametrize(
    ("value", "attribute", "expected"),
    (
        ("", Attribute(name="my_attr", type_=at.String), False),
        ("abc", Attribute(name="my_attr", type_=at.String), True),
        (None, Attribute(name="my_attr", type_=at.Boolean), False),
        (False, Attribute(name="my_attr", type_=at.Boolean), True),
        ([], Attribute(name="my_attr", type_=at.String, multi_valued=True), False),
        (["a", "b", "c"], Attribute(name="my_attr", type_=at.String, multi_valued=True), True),
        (
            {
                "value": "",
            },
            ComplexAttribute(
                name="my_attr",
                sub_attributes=[Attribute(name="value", type_=at.String)]
            ),
            False
        ),
        (
            {
                "value": "abc",
            },
            ComplexAttribute(
                name="my_attr",
                sub_attributes=[Attribute(name="value", type_=at.String)]
            ),
            False  # only multivalued complex attributes can be matched
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
            ComplexAttribute(
                name="my_attr",
                sub_attributes=[Attribute(name="value", type_=at.String, multi_valued=True)],
                multi_valued=True,
            ),
            False
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
            ComplexAttribute(
                name="my_attr",
                sub_attributes=[Attribute(name="value", type_=at.String, multi_valued=True)],
                multi_valued=True,
            ),
            True
        ),
    )
)
def test_present_operator(value, attribute, expected):
    operator = Present("my_attr")

    actual = operator.match(value, attribute)

    assert actual is expected


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
    )
)
def test_present_operator_without_attribute(value, expected):
    operator = Present("my_attr")

    actual = operator.match(value, None)

    assert actual is expected


@pytest.mark.parametrize("use_attribute", (True, False))
def test_complex_attribute_matches_binary_operator_if_one_of_values_matches(use_attribute):
    attribute = (
        ComplexAttribute(
            name="my_attr",
            sub_attributes=[Attribute(name="value", type_=at.String, multi_valued=True)],
            multi_valued=True,
        )
        if use_attribute
        else None
    )
    operator = StartsWith("my_attr", "abc")

    match = operator.match(
        value=[{"value": "a"}, {"value": "bac"}, {"value": "abcd"}],
        attr=attribute,
    )

    assert match


@pytest.mark.parametrize("use_attribute", (True, False))
def test_complex_attribute_does_not_match_binary_operator_if_not_any_of_values_matches(use_attribute):
    attribute = (
        ComplexAttribute(
            name="my_attr",
            sub_attributes=[Attribute(name="value", type_=at.String, multi_valued=True)],
            multi_valued=True,
        )
        if use_attribute
        else None
    )
    operator = StartsWith("my_attr", "abc")

    match = operator.match(
        value=[{"value": "a"}, {"value": "bac"}, {"value": "bcdd"}],
        attr=attribute,
    )

    assert not match


@pytest.mark.parametrize(
    ("lt_attr_value", "le_attr_value", "expected"),
    (
        (1, 0, True),
        (1, 2, False),
    )
)
def test_and_operator_matches(lt_attr_value, le_attr_value, expected):
    operator = And(
        Equal("eq_attr", 1),
        NotEqual("ne_attr", "2"),
        StartsWith("sw_attr", "ab"),
        EndsWith("ew_attr", "bc"),
        And(
            GreaterThan("gt_attr", 1),
            GreaterThanOrEqual("ge_attr", 1),
        ),
        Or(
            LesserThan("lt_attr", 1),
            LesserThanOrEqual("le_attr", 1),
        ),
        Contains("co_attr", "b"),
        Present("pr_attr")
    )

    actual = operator.match(
        value={
            "eq_attr": 1,
            "ne_attr": "1",
            "sw_attr": "abc",
            "ew_attr": "abc",
            "gt_attr": 2,
            "ge_attr": 1,
            "lt_attr": lt_attr_value,
            "le_attr": le_attr_value,
            "co_attr": "abc",
            "pr_attr": "abc",
        },
        attrs={  # noqa
            "eq_attr": Attribute("eq_attr", type_=at.Integer),
            "ne_attr": Attribute("ne_attr", type_=at.String),
            "sw_attr": Attribute("sw_attr", type_=at.String),
            "ew_attr": Attribute("ew_attr", type_=at.String),
            "gt_attr": Attribute("gt_attr", type_=at.Integer),
            "ge_attr": Attribute("ge_attr", type_=at.Integer),
            "lt_attr": Attribute("lt_attr", type_=at.Integer),
            "le_attr": Attribute("le_attr", type_=at.Integer),
            "co_attr": Attribute("co_attr", type_=at.String),
            "pr_attr": Attribute("pr_attr", type_=at.String),
        },
    )

    assert actual is expected


@pytest.mark.parametrize(
    ("lt_attr_value", "le_attr_value", "expected"),
    (
        (1, 0, True),
        (1, 2, False),
    )
)
def test_or_operator_matches(lt_attr_value, le_attr_value, expected):
    operator = Or(
        Equal("eq_attr", 1),
        NotEqual("ne_attr", "2"),
        StartsWith("sw_attr", "ab"),
        EndsWith("ew_attr", "bc"),
        And(
            GreaterThan("gt_attr", 1),
            GreaterThanOrEqual("ge_attr", 1),
        ),
        Or(
            LesserThan("lt_attr", 1),
            LesserThanOrEqual("le_attr", 1),
        ),
        Contains("co_attr", "b"),
        Present("pr_attr")
    )

    actual = operator.match(
        value={
            "eq_attr": 2,
            "ne_attr": "2",
            "sw_attr": "cba",
            "ew_attr": "cba",
            "gt_attr": 1,
            "ge_attr": 1,
            "lt_attr": lt_attr_value,
            "le_attr": le_attr_value,
            "co_attr": "ccc",
            "pr_attr": "",
        },
        attrs={  # noqa
            "eq_attr": Attribute("eq_attr", type_=at.Integer),
            "ne_attr": Attribute("ne_attr", type_=at.String),
            "sw_attr": Attribute("sw_attr", type_=at.String),
            "ew_attr": Attribute("ew_attr", type_=at.String),
            "gt_attr": Attribute("gt_attr", type_=at.Integer),
            "ge_attr": Attribute("ge_attr", type_=at.Integer),
            "lt_attr": Attribute("lt_attr", type_=at.Integer),
            "le_attr": Attribute("le_attr", type_=at.Integer),
            "co_attr": Attribute("co_attr", type_=at.String),
            "pr_attr": Attribute("pr_attr", type_=at.String),
        }
    )

    assert actual is expected


@pytest.mark.parametrize("use_attr", (True, False))
def test_complex_attribute_operator_matches_all_complex_sub_attrs(use_attr):
    attribute = (
        ComplexAttribute(
            name="complex_attr",
            sub_attributes=[
                Attribute(name="sub_attr_1", type_=at.String),
                Attribute(name="sub_attr_2", type_=at.Integer),
                Attribute(name="sub_attr_3", type_=at.Boolean),
            ]
        )
        if use_attr
        else None
    )
    operator = ComplexAttributeOperator(
        attr_name="complex_attr",
        sub_operator=And(
            Equal("sub_attr_1", "admin"),
            GreaterThan("sub_attr_2", 18),
            NotEqual("sub_attr_3", True),
        )
    )

    match = operator.match(
        value={"sub_attr_1": "admin", "sub_attr_2": 19, "sub_attr_3": False},
        attr=attribute,
    )

    assert match


def test_complex_attribute_operator_does_not_match_all_complex_sub_attrs():
    attribute = ComplexAttribute(
        name="complex_attr",
        sub_attributes=[
            Attribute(name="sub_attr_1", type_=at.String),
            Attribute(name="sub_attr_2", type_=at.Integer),
            Attribute(name="sub_attr_3", type_=at.Boolean),
        ]
    )

    operator = ComplexAttributeOperator(
        attr_name="complex_attr",
        sub_operator=Or(
            Equal("sub_attr_1", "admin"),
            GreaterThan("sub_attr_2", 18),
            NotEqual("sub_attr_3", True),
        )
    )

    match = operator.match(
        value={"sub_attr_1": "user", "sub_attr_2": 18, "sub_attr_3": True},
        attr=attribute,
    )

    assert not match


def test_complex_attribute_operator_ignores_str_values_when_matching_sub_attrs_without_attribute():
    operator = ComplexAttributeOperator(
        attr_name="complex_attr",
        sub_operator=Or(
            Equal("sub_attr_1", "admin"),
            GreaterThan("sub_attr_2", 18),
            NotEqual("sub_attr_3", True),
        )
    )

    # 'sub_attr_1' evaluates to 'True'
    match = operator.match(
        value={"sub_attr_1": "user", "sub_attr_2": 18, "sub_attr_3": True},
        attr=None,
    )

    assert match


@pytest.mark.parametrize("use_attr", (True, False))
def test_complex_attr_op_matches_some_of_sub_attrs_of_multi_valued_complex_attr(use_attr):
    attribute = (
        ComplexAttribute(
            name="complex_attr",
            sub_attributes=[
                Attribute(name="sub_attr_1", type_=at.String),
                Attribute(name="sub_attr_2", type_=at.Integer),
                Attribute(name="sub_attr_3", type_=at.Boolean),
            ],
            multi_valued=True,
        )
        if use_attr
        else None
    )
    operator = ComplexAttributeOperator(
        attr_name="complex_attr",
        sub_operator=And(
            Equal("sub_attr_1", "admin"),
            GreaterThan("sub_attr_2", 18),
            NotEqual("sub_attr_3", True),
        )
    )

    match = operator.match(
        value=[
            {"sub_attr_1": "admin", "sub_attr_2": 19, "sub_attr_3": False},
            {"sub_attr_1": "user", "sub_attr_2": 18, "sub_attr_3": True},
            {"sub_attr_1": "user", "sub_attr_2": 19, "sub_attr_3": False},
        ],
        attr=attribute,
    )

    assert match


def test_complex_attr_op_does_not_match_any_of_multi_valued_complex_sub_attrs():
    attribute = ComplexAttribute(
        name="complex_attr",
        sub_attributes=[
            Attribute(name="sub_attr_1", type_=at.String),
            Attribute(name="sub_attr_2", type_=at.Integer),
            Attribute(name="sub_attr_3", type_=at.Boolean),
        ],
        multi_valued=True,
    )

    operator = ComplexAttributeOperator(
        attr_name="complex_attr",
        sub_operator=Or(
            Equal("sub_attr_1", "admin"),
            GreaterThan("sub_attr_2", 18),
            NotEqual("sub_attr_3", True),
        )
    )

    match = operator.match(
        value=[
            {"sub_attr_1": "user", "sub_attr_2": 16, "sub_attr_3": True},
            {"sub_attr_1": "customer", "sub_attr_2": 18, "sub_attr_3": True},
            {"sub_attr_1": "santa-claus", "sub_attr_2": 12, "sub_attr_3": True},
        ],
        attr=attribute,
    )

    assert not match


def test_complex_attr_op_ignores_str_vals_when_matching_multivalued_complex_sub_attrs_without_attr():
    operator = ComplexAttributeOperator(
        attr_name="complex_attr",
        sub_operator=Or(
            Equal("sub_attr_1", "admin"),
            GreaterThan("sub_attr_2", 18),
            NotEqual("sub_attr_3", True),
        )
    )

    # all 'sub_attr_1' are ignored and evaluate to 'True'
    match = operator.match(
        value=[
            {"sub_attr_1": "user", "sub_attr_2": 16, "sub_attr_3": True},
            {"sub_attr_1": "customer", "sub_attr_2": 18, "sub_attr_3": True},
            {"sub_attr_1": "santa-claus", "sub_attr_2": 12, "sub_attr_3": True},
        ],
        attr=None,
    )

    assert match


@pytest.mark.parametrize(
    ("value", "is_multivalued", "expected"),
    (
        (
            {"sub_attr_1": "admin", "sub_attr_2": 19, "sub_attr_3": False},
            False,
            True,
        ),
        (
            {"sub_attr_1": "user", "sub_attr_2": 18, "sub_attr_3": True},
            False,
            False,
        ),
        (
            [
                {"sub_attr_1": "admin", "sub_attr_2": 19, "sub_attr_3": False},
                {"sub_attr_1": "user", "sub_attr_2": 18, "sub_attr_3": True},
                {"sub_attr_1": "user", "sub_attr_2": 19, "sub_attr_3": False},
            ],
            True,
            True,
        ),
        (
            [
                {"sub_attr_1": "user", "sub_attr_2": 16, "sub_attr_3": True},
                {"sub_attr_1": "customer", "sub_attr_2": 18, "sub_attr_3": True},
                {"sub_attr_1": "santa-claus", "sub_attr_2": 12, "sub_attr_3": True},
            ],
            True,
            False,
        )
    )
)
def test_attribute_operator_matches_single_complex_sub_attr(value, is_multivalued, expected):
    attribute = ComplexAttribute(
        name="complex_attr",
        sub_attributes=[
            Attribute(name="sub_attr_1", type_=at.String),
            Attribute(name="sub_attr_2", type_=at.Integer),
            Attribute(name="sub_attr_3", type_=at.Boolean),
        ],
        multi_valued=is_multivalued,
    )

    operator = ComplexAttributeOperator(
        attr_name="complex_attr",
        sub_operator=Equal("sub_attr_1", "admin"),
    )

    actual = operator.match(
        value=value,
        attr=attribute,
    )

    assert actual is expected


@pytest.mark.parametrize(
    ("value", "is_multivalued", "expected"),
    (
        (
            {"sub_attr_1": "admin", "sub_attr_2": 19, "sub_attr_3": False},
            False,
            True,
        ),
        (
            {"sub_attr_1": "user", "sub_attr_2": 18, "sub_attr_3": True},
            False,
            True,
        ),
        (
            [
                {"sub_attr_1": "admin", "sub_attr_2": 19, "sub_attr_3": False},
                {"sub_attr_1": "user", "sub_attr_2": 18, "sub_attr_3": True},
                {"sub_attr_1": "user", "sub_attr_2": 19, "sub_attr_3": False},
            ],
            True,
            True,
        ),
        (
            [
                {"sub_attr_1": "user", "sub_attr_2": 16, "sub_attr_3": True},
                {"sub_attr_1": "customer", "sub_attr_2": 18, "sub_attr_3": True},
                {"sub_attr_1": "santa-claus", "sub_attr_2": 12, "sub_attr_3": True},
            ],
            True,
            True,
        )
    )
)
def test_complex_attr_op_ignores_str_values_when_matching_complex_sub_attr_without_attribute(
    value, is_multivalued, expected
):

    operator = ComplexAttributeOperator(
        attr_name="complex_attr",
        sub_operator=Equal("sub_attr_1", "admin"),
    )

    actual = operator.match(
        value=value,
        attr=None,
    )

    assert actual is expected
