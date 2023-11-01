from datetime import datetime

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

SCHEMA_FOR_TESTS = ResourceSchema(
    schema="schema:for:tests",
    repr_="SchemaForTests",
    attrs=[
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
    ],
)


@pytest.mark.parametrize(
    ("value", "operator_value", "attr_name", "expected"),
    (
        (1, 1, AttributeName.parse("int"), True),
        (1, 2, AttributeName.parse("int"), False),
        ("a", "a", AttributeName.parse("str_cs"), True),
        ("A", "a", AttributeName.parse("str_cs"), False),
        (True, True, AttributeName.parse("bool"), True),
        (True, False, AttributeName.parse("bool"), False),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            AttributeName.parse("datetime"),
            True,
        ),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 2).isoformat(),
            AttributeName.parse("datetime"),
            False,
        ),
        (3.14, 3.14, AttributeName.parse("decimal"), True),
        (3.14, 3.141, AttributeName.parse("decimal"), False),
        (
            "YQ==",
            "YQ==",
            AttributeName.parse("binary"),
            True,
        ),
        (
            "YQ==",
            "Yg==",
            AttributeName.parse("binary"),
            False,
        ),
        (
            "https://www.example.com",
            "https://www.example.com",
            AttributeName.parse("external_ref"),
            True,
        ),
        (
            "https://www.example.com",
            "https://www.bad_example.com",
            AttributeName.parse("external_ref"),
            False,
        ),
        (
            "whatever/some/location/",
            "whatever/some/location/",
            AttributeName.parse("uri_ref"),
            True,
        ),
        (
            "whatever/some/location/",
            "whatever/some/other/location/",
            AttributeName.parse("uri_ref"),
            False,
        ),
        (
            "Users",
            "Users",
            AttributeName.parse("scim_ref"),
            True,
        ),
        (
            "Users",
            "Groups",
            AttributeName.parse("scim_ref"),
            False,
        ),
    ),
)
def test_equal_operator(value, operator_value, attr_name, expected):
    operator = Equal(attr_name, operator_value)

    actual = operator.match(value, SCHEMA_FOR_TESTS)

    assert actual == expected


@pytest.mark.parametrize(
    ("value", "operator_value", "attribute_name", "expected"),
    (
        (1, 1, AttributeName.parse("int"), False),
        (1, 2, AttributeName.parse("int"), True),
        ("a", "a", AttributeName.parse("str_cs"), False),
        ("A", "a", AttributeName.parse("str_cs"), True),
        (True, True, AttributeName.parse("bool"), False),
        (True, False, AttributeName.parse("bool"), True),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            AttributeName.parse("datetime"),
            False,
        ),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 2).isoformat(),
            AttributeName.parse("datetime"),
            True,
        ),
        (3.14, 3.14, AttributeName.parse("decimal"), False),
        (3.14, 3.141, AttributeName.parse("decimal"), True),
        (
            "YQ==",
            "YQ==",
            AttributeName.parse("binary"),
            False,
        ),
        (
            "YQ==",
            "Yg==",
            AttributeName.parse("binary"),
            True,
        ),
        (
            "https://www.example.com",
            "https://www.example.com",
            AttributeName.parse("external_ref"),
            False,
        ),
        (
            "https://www.example.com",
            "https://www.bad_example.com",
            AttributeName.parse("external_ref"),
            True,
        ),
        (
            "whatever/some/location/",
            "whatever/some/location/",
            AttributeName.parse("uri_ref"),
            False,
        ),
        (
            "whatever/some/location/",
            "whatever/some/other/location/",
            AttributeName.parse("uri_ref"),
            True,
        ),
        (
            "Users",
            "Users",
            AttributeName.parse("scim_ref"),
            False,
        ),
        (
            "Users",
            "Groups",
            AttributeName.parse("scim_ref"),
            True,
        ),
    ),
)
def test_not_equal_operator(value, operator_value, attribute_name, expected):
    operator = NotEqual(attribute_name, operator_value)

    actual = operator.match(value, SCHEMA_FOR_TESTS)

    assert actual == expected


@pytest.mark.parametrize(
    ("value", "operator_value", "attribute_name", "expected"),
    (
        (1, 1, AttributeName.parse("int"), False),
        (2, 1, AttributeName.parse("int"), True),
        ("a", "a", AttributeName.parse("str_cs"), False),
        ("a", "A", AttributeName.parse("str_cs"), True),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            AttributeName.parse("datetime"),
            False,
        ),
        (
            datetime(2023, 10, 10, 21, 27, 2).isoformat(),
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            AttributeName.parse("datetime"),
            True,
        ),
        (3.14, 3.14, AttributeName.parse("decimal"), False),
        (3.141, 3.14, AttributeName.parse("decimal"), True),
    ),
)
def test_greater_than_operator(value, operator_value, attribute_name, expected):
    operator = GreaterThan(attribute_name, operator_value)

    actual = operator.match(value, SCHEMA_FOR_TESTS)

    assert actual == expected


@pytest.mark.parametrize(
    ("value", "operator_value", "attribute_name", "expected"),
    (
        (1, 2, AttributeName.parse("int"), False),
        (1, 1, AttributeName.parse("int"), True),
        (2, 1, AttributeName.parse("int"), True),
        ("A", "a", AttributeName.parse("str_cs"), False),
        ("a", "a", AttributeName.parse("str_cs"), True),
        ("a", "A", AttributeName.parse("str_cs"), True),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 2).isoformat(),
            AttributeName.parse("datetime"),
            False,
        ),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            AttributeName.parse("datetime"),
            True,
        ),
        (
            datetime(2023, 10, 10, 21, 27, 2).isoformat(),
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            AttributeName.parse("datetime"),
            True,
        ),
        (3.14, 3.141, AttributeName.parse("decimal"), False),
        (3.14, 3.14, AttributeName.parse("decimal"), True),
        (3.141, 3.14, AttributeName.parse("decimal"), True),
    ),
)
def test_greater_than_or_equal_operator(value, operator_value, attribute_name, expected):
    operator = GreaterThanOrEqual(attribute_name, operator_value)

    actual = operator.match(value, SCHEMA_FOR_TESTS)

    assert actual == expected


@pytest.mark.parametrize(
    ("value", "operator_value", "attribute_name", "expected"),
    (
        (1, 1, AttributeName.parse("int"), False),
        (1, 2, AttributeName.parse("int"), True),
        ("a", "a", AttributeName.parse("str_cs"), False),
        ("A", "a", AttributeName.parse("str_cs"), True),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            AttributeName.parse("datetime"),
            False,
        ),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 2).isoformat(),
            AttributeName.parse("datetime"),
            True,
        ),
        (3.14, 3.14, AttributeName.parse("decimal"), False),
        (3.14, 3.141, AttributeName.parse("decimal"), True),
    ),
)
def test_lesser_than_operator(value, operator_value, attribute_name, expected):
    operator = LesserThan(attribute_name, operator_value)

    actual = operator.match(value, SCHEMA_FOR_TESTS)

    assert actual == expected


@pytest.mark.parametrize(
    ("value", "operator_value", "attribute_name", "expected"),
    (
        (1, 2, AttributeName.parse("int"), True),
        (1, 1, AttributeName.parse("int"), True),
        (2, 1, AttributeName.parse("int"), False),
        ("A", "a", AttributeName.parse("str_cs"), True),
        ("a", "a", AttributeName.parse("str_cs"), True),
        ("a", "A", AttributeName.parse("str_cs"), False),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 2).isoformat(),
            AttributeName.parse("datetime"),
            True,
        ),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            AttributeName.parse("datetime"),
            True,
        ),
        (
            datetime(2023, 10, 10, 21, 27, 2).isoformat(),
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            AttributeName.parse("datetime"),
            False,
        ),
        (3.14, 3.141, AttributeName.parse("decimal"), True),
        (3.14, 3.14, AttributeName.parse("decimal"), True),
        (3.141, 3.14, AttributeName.parse("decimal"), False),
    ),
)
def test_lesser_than_or_equal_operator(value, operator_value, attribute_name, expected):
    operator = LesserThanOrEqual(attribute_name, operator_value)

    actual = operator.match(value, SCHEMA_FOR_TESTS)

    assert actual == expected


def test_binary_operator_does_not_match_if_non_matching_attribute_type():
    operator = Equal(AttributeName.parse("int"), "1")

    match = operator.match(1, SCHEMA_FOR_TESTS)

    assert not match


def test_binary_operator_does_not_match_if_attr_missing_in_schema():
    operator = Equal(AttributeName.parse("other_int"), 1)

    match = operator.match(1, SCHEMA_FOR_TESTS)

    assert not match


def test_binary_operator_does_not_match_if_not_supported_scim_type():
    operator = GreaterThan(AttributeName.parse("scim_ref"), chr(0))

    match = operator.match("Users", SCHEMA_FOR_TESTS)

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
    operator = operator_cls(AttributeName.parse("str"), "A")

    actual = operator.match("a", SCHEMA_FOR_TESTS)

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
    operator = Contains(AttributeName.parse("str_cs"), operator_value)

    actual = operator.match(value, SCHEMA_FOR_TESTS)

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
    operator = StartsWith(AttributeName.parse("str_cs"), operator_value)

    actual = operator.match(value, SCHEMA_FOR_TESTS)

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
    operator = EndsWith(AttributeName.parse("str_cs"), operator_value)

    actual = operator.match(value, SCHEMA_FOR_TESTS)

    assert actual == expected


def test_multi_value_attribute_is_matched_if_one_of_values_match():
    operator = Equal(AttributeName.parse("str_cs_mv"), "abc")

    match = operator.match(["b", "c", "ab", "abc", "ca"], SCHEMA_FOR_TESTS)

    assert match


def test_multi_value_attribute_is_matched_if_one_of_case_insensitive_values_match():
    operator = Equal(AttributeName.parse("str_mv"), "abc")

    match = operator.match(["b", "c", "ab", "ABc", "ca"], SCHEMA_FOR_TESTS)

    assert match


@pytest.mark.parametrize(
    ("value", "attribute_name", "expected"),
    (
        ("", AttributeName.parse("str"), False),
        ("abc", AttributeName.parse("str"), True),
        (None, AttributeName.parse("bool"), False),
        (False, AttributeName.parse("bool"), True),
        ([], AttributeName.parse("str_mv"), False),
        (
            ["a", "b", "c"],
            AttributeName.parse("str_mv"),
            True,
        ),
        (
            {
                "value": "",
            },
            AttributeName.parse("c"),
            False,
        ),
        (
            {
                "value": "abc",
            },
            AttributeName.parse("c"),
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
            AttributeName.parse("c_mv"),
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
            AttributeName.parse("c_mv"),
            True,
        ),
    ),
)
def test_present_operator(value, attribute_name, expected):
    operator = Present(attribute_name)

    actual = operator.match(value, SCHEMA_FOR_TESTS)

    assert actual == expected


def test_complex_attribute_matches_binary_operator_if_one_of_values_matches():
    operator = StartsWith(AttributeName.parse("c_mv"), "abc")

    match = operator.match([{"value": "a"}, {"value": "bac"}, {"value": "abcd"}], SCHEMA_FOR_TESTS)

    assert match


def test_complex_attribute_does_not_match_binary_operator_if_not_any_of_values_matches():
    operator = StartsWith(AttributeName.parse("c_mv"), "abc")

    match = operator.match([{"value": "a"}, {"value": "bac"}, {"value": "bcdd"}], SCHEMA_FOR_TESTS)

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
        Equal(AttributeName.parse("int"), 1),
        And(
            GreaterThan(AttributeName.parse("decimal"), 1.0),
            NotEqual(AttributeName.parse("str"), "1"),
        ),
        Or(
            Equal(AttributeName.parse("bool"), True),
            StartsWith(AttributeName.parse("str_cs"), "a"),
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
        SCHEMA_FOR_TESTS,
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
        Equal(AttributeName.parse("int"), 1),
        And(
            GreaterThan(AttributeName.parse("decimal"), 1.0),
            NotEqual(AttributeName.parse("str"), "1"),
        ),
        Or(
            Equal(AttributeName.parse("bool"), True),
            StartsWith(AttributeName.parse("str_cs"), "a"),
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
        SCHEMA_FOR_TESTS,
    )

    assert actual == expected


def test_complex_attribute_operator_matches_all_complex_sub_attrs():
    operator = ComplexAttributeOperator(
        attr_name=AttributeName.parse("c2"),
        sub_operator=And(
            Equal(AttributeName.parse("c2.str"), "admin"),
            GreaterThan(AttributeName.parse("c2.int"), 18),
            NotEqual(AttributeName.parse("c2.bool"), True),
        ),
    )

    match = operator.match({"str": "admin", "int": 19, "bool": False}, SCHEMA_FOR_TESTS)

    assert match


def test_complex_attribute_operator_does_not_match_all_complex_sub_attrs():
    operator = ComplexAttributeOperator(
        attr_name=AttributeName.parse("c2"),
        sub_operator=Or(
            Equal(AttributeName.parse("c2.str"), "admin"),
            GreaterThan(AttributeName.parse("c2.int"), 18),
            NotEqual(AttributeName.parse("c2.bool"), True),
        ),
    )

    match = operator.match({"str": "user", "int": 18, "bool": True}, SCHEMA_FOR_TESTS)

    assert not match


def test_complex_attr_op_matches_some_of_sub_attrs_of_multi_valued_complex_attr():
    operator = ComplexAttributeOperator(
        attr_name=AttributeName.parse("c2_mv"),
        sub_operator=And(
            Equal(AttributeName.parse("c2_mv.str"), "admin"),
            GreaterThan(AttributeName.parse("c2_mv.int"), 18),
            NotEqual(AttributeName.parse("c2_mv.bool"), True),
        ),
    )

    match = operator.match(
        [
            {"str": "admin", "int": 19, "bool": False},
            {"str": "user", "int": 18, "bool": True},
            {"str": "user", "int": 19, "bool": False},
        ],
        SCHEMA_FOR_TESTS,
    )

    assert match


def test_complex_attr_op_does_not_match_any_of_multi_valued_complex_sub_attrs():
    operator = ComplexAttributeOperator(
        attr_name=AttributeName.parse("c2_mv"),
        sub_operator=Or(
            Equal(AttributeName.parse("c2_mv.str"), "admin"),
            GreaterThan(AttributeName.parse("c2_mv.int"), 18),
            NotEqual(AttributeName.parse("c2_mv.bool"), True),
        ),
    )

    match = operator.match(
        [
            {"str": "user", "int": 16, "bool": True},
            {"str": "customer", "int": 18, "bool": True},
            {"str": "santa-claus", "int": 12, "bool": True},
        ],
        SCHEMA_FOR_TESTS,
    )

    assert not match


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
def test_attribute_operator_matches_single_complex_sub_attr(value, is_multivalued, expected):
    if is_multivalued:
        operator = ComplexAttributeOperator(
            attr_name=AttributeName.parse("c2_mv"),
            sub_operator=Equal(AttributeName.parse("c2_mv.str"), "admin"),
        )
    else:
        operator = ComplexAttributeOperator(
            attr_name=AttributeName.parse("c2"),
            sub_operator=Equal(AttributeName.parse("c2.str"), "admin"),
        )

    actual = operator.match(value, SCHEMA_FOR_TESTS)

    assert actual == expected


def test_binary_op_returns_missing_data_if_no_value_provided_with_strict():
    operator = Equal(AttributeName.parse("str"), "abc")

    match = operator.match(None, SCHEMA_FOR_TESTS, True)

    assert match.status == MatchStatus.MISSING_DATA


def test_binary_op_returns_matches_if_no_value_provided_without_strict():
    operator = Equal(AttributeName.parse("str"), "abc")

    match = operator.match(None, SCHEMA_FOR_TESTS, False)

    assert match


def test_complex_op_matches_if_sub_attr_value_not_provided_without_strict():
    operator = ComplexAttributeOperator(
        attr_name=AttributeName.parse("c"),
        sub_operator=Equal(AttributeName.parse("c.str"), "abc"),
    )

    match = operator.match({}, SCHEMA_FOR_TESTS, False)

    assert match


def test_complex_op_does_not_matches_if_sub_attribute_not_provided_with_strict():
    operator = ComplexAttributeOperator(
        attr_name=AttributeName.parse("c"),
        sub_operator=Equal(AttributeName.parse("c.str"), "abc"),
    )

    match = operator.match({}, SCHEMA_FOR_TESTS, True)

    assert not match


def test_or_op_returns_missing_data_if_no_sub_attr_matched_with_strict():
    operator = Or(
        Equal(AttributeName.parse("int"), 1),
        Equal(AttributeName.parse("str"), "abc"),
    )

    match = operator.match({"int": 2}, SCHEMA_FOR_TESTS, True)

    assert match.status == MatchStatus.MISSING_DATA


@pytest.mark.parametrize("strict", (True, False))
def test_or_op_matches_if_any_sub_attr_matched(strict):
    operator = Or(
        Equal(AttributeName.parse("int"), 1),
        Equal(AttributeName.parse("str"), "abc"),
    )

    match = operator.match({"int": 1}, SCHEMA_FOR_TESTS, strict)

    assert match


def test_and_op_returns_missing_data_if_any_sub_attr_is_without_data_with_strict():
    operator = And(
        Equal(AttributeName.parse("int"), 1),
        Equal(AttributeName.parse("str"), "abc"),
    )
    value = {"int": 1}  # value for this attr is correct, but missing 'str'

    match = operator.match(value, SCHEMA_FOR_TESTS, True)

    assert match.status == MatchStatus.MISSING_DATA


def test_and_op_does_not_match_if_any_sub_attr_does_not_match_with_strict():
    operator = And(
        Equal(AttributeName.parse("int"), 1),
        Equal(AttributeName.parse("str"), "abc"),
    )

    match = operator.match({"int": 1, "str": "cba"}, SCHEMA_FOR_TESTS, True)

    assert not match


def test_and_operator_matches_if_non_of_sub_attrs_fail_without_strict():
    operator = And(
        Equal(AttributeName.parse("int"), 1),
        Equal(
            AttributeName.parse("str"),
            "abc",
        ),
    )
    value = {"int": 1}  # value for this attr is correct, 'str' is missing, but no strict

    match = operator.match(value, SCHEMA_FOR_TESTS, False)

    assert match


def test_not_op_matches_for_missing_value_in_logical_sub_op_without_strict():
    operator = Not(
        Or(
            Equal(AttributeName.parse("int"), 1),
            Equal(AttributeName.parse("str"), "abc"),
        ),
    )

    match = operator.match({"int": 2}, SCHEMA_FOR_TESTS, False)

    assert match


def test_not_op_does_not_match_for_missing_value_in_logical_sub_op_with_strict():
    operator = Not(
        Or(
            Equal(AttributeName.parse("int"), 1),
            Equal(AttributeName.parse("str"), "abc"),
        ),
    )

    match = operator.match({"int": 2}, SCHEMA_FOR_TESTS, True)

    assert not match


def test_not_op_matches_for_missing_value_in_attr_sub_op_without_strict():
    operator = Not(Equal(AttributeName.parse("int"), 1))

    match = operator.match({}, SCHEMA_FOR_TESTS, False)

    assert match


def test_not_op_does_not_match_for_missing_value_in_attr_sub_op_with_strict():
    operator = Not(Equal(AttributeName.parse("int"), 1))

    match = operator.match({}, SCHEMA_FOR_TESTS, True)

    assert not match


def test_not_op_does_not_match_if_op_attr_not_in_attrs():
    operator = Not(Equal(AttributeName.parse("other_attr"), 1))

    match = operator.match({"other_attr": 2}, SCHEMA_FOR_TESTS)

    assert not match


@pytest.mark.parametrize("strict", (True, False))
def test_not_op_matches_if_no_data_for_pr_sub_op_with_strict(strict):
    operator = Not(Present(AttributeName.parse("int")))

    match = operator.match({}, SCHEMA_FOR_TESTS, strict)

    assert match


@pytest.mark.parametrize("strict", (True, False))
@pytest.mark.parametrize(("value", "expected"), ((1.0, True), (2.0, False)))
def test_binary_attributes_allows_to_compare_int_with_decimal(strict, value, expected):
    operator = Equal(AttributeName.parse("decimal"), 1)

    match = operator.match(value, SCHEMA_FOR_TESTS, strict)

    assert bool(match) is expected


@pytest.mark.parametrize("strict", (True, False))
@pytest.mark.parametrize(("value", "expected"), ((1, True), (2, False)))
def test_binary_attributes_allows_to_compare_decimal_with_int(strict, value, expected):
    operator = Equal(AttributeName.parse("int"), 1.0)

    match = operator.match(value, SCHEMA_FOR_TESTS, strict)

    assert bool(match) is expected


def test_complex_op_can_be_used_with_logical_op():
    operator = ComplexAttributeOperator(
        attr_name=AttributeName.parse("c2"),
        sub_operator=And(
            Equal(AttributeName.parse("int"), 1), Equal(AttributeName.parse("str"), "abc")
        ),
    )

    match = operator.match({"int": 1, "str": "abc"}, SCHEMA_FOR_TESTS)

    assert match


def test_complex_op_used_with_or_op_matches_if_at_least_one_sub_attr_matches():
    operator = ComplexAttributeOperator(
        attr_name=AttributeName.parse("c2"),
        sub_operator=Or(
            Equal(AttributeName.parse("int"), 1), Equal(AttributeName.parse("str"), "abc")
        ),
    )

    match = operator.match({"int": 1}, SCHEMA_FOR_TESTS)

    assert match


def test_complex_op_used_with_or_op_does_not_match_if_no_values_provided():
    operator = ComplexAttributeOperator(
        attr_name=AttributeName.parse("c2"),
        sub_operator=Or(
            Equal(AttributeName.parse("int"), 1), Equal(AttributeName.parse("str"), "abc")
        ),
    )

    match = operator.match({}, SCHEMA_FOR_TESTS)

    assert not match


def test_complex_op_used_with_or_op_matches_if_no_values_provided_without_strict():
    operator = ComplexAttributeOperator(
        attr_name=AttributeName.parse("c2"),
        sub_operator=Or(
            Equal(AttributeName.parse("int"), 1), Equal(AttributeName.parse("str"), "abc")
        ),
    )

    match = operator.match({}, SCHEMA_FOR_TESTS, False)

    assert match


def test_multivalued_complex_op_can_be_used_with_logical_op():
    operator = ComplexAttributeOperator(
        attr_name=AttributeName.parse("c2_mv"),
        sub_operator=And(
            Equal(AttributeName.parse("int"), 1), Equal(AttributeName.parse("str"), "abc")
        ),
    )

    match = operator.match(
        [{"int": 2, "str": "abc"}, {"int": 1, "str": "cba"}, {"int": 1, "str": "abc"}],
        SCHEMA_FOR_TESTS,
    )

    assert match
