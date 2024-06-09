from datetime import datetime

import pytest

from src.assets.schemas import User
from src.container import AttrRep, SCIMDataContainer
from src.data.attrs import Attribute, Complex, DateTime, String
from src.data.operator import (
    And,
    ComplexAttributeOperator,
    Contains,
    EndsWith,
    Equal,
    GreaterThan,
    GreaterThanOrEqual,
    LesserThan,
    LesserThanOrEqual,
    Not,
    NotEqual,
    Or,
    Present,
    StartsWith,
)
from tests.conftest import SchemaForTests


@pytest.mark.parametrize(
    ("value", "operator_value", "attr_rep", "expected"),
    (
        (1, 1, AttrRep(attr="int"), True),
        (1, 2, AttrRep(attr="int"), False),
        ("a", "a", AttrRep(attr="str_cs"), True),
        ("A", "a", AttrRep(attr="str_cs"), False),
        (True, True, AttrRep(attr="bool"), True),
        (True, False, AttrRep(attr="bool"), False),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            AttrRep(attr="datetime"),
            True,
        ),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 2).isoformat(),
            AttrRep(attr="datetime"),
            False,
        ),
        (3.14, 3.14, AttrRep(attr="decimal"), True),
        (3.14, 3.141, AttrRep(attr="decimal"), False),
        (
            "YQ==",
            "YQ==",
            AttrRep(attr="binary"),
            True,
        ),
        (
            "YQ==",
            "Yg==",
            AttrRep(attr="binary"),
            False,
        ),
        (
            "https://www.example.com",
            "https://www.example.com",
            AttrRep(attr="external_ref"),
            True,
        ),
        (
            "https://www.example.com",
            "https://www.bad_example.com",
            AttrRep(attr="external_ref"),
            False,
        ),
        (
            "whatever/some/location/",
            "whatever/some/location/",
            AttrRep(attr="uri_ref"),
            True,
        ),
        (
            "whatever/some/location/",
            "whatever/some/other/location/",
            AttrRep(attr="uri_ref"),
            False,
        ),
        (
            "Users",
            "Users",
            AttrRep(attr="scim_ref"),
            True,
        ),
        (
            "Users",
            "Groups",
            AttrRep(attr="scim_ref"),
            False,
        ),
    ),
)
def test_equal_operator(value, operator_value, attr_rep, expected):
    operator = Equal(attr_rep, operator_value)

    actual = operator.match(value, SchemaForTests)

    assert actual == expected


@pytest.mark.parametrize(
    ("value", "operator_value", "attribute_name", "expected"),
    (
        (1, 1, AttrRep(attr="int"), False),
        (1, 2, AttrRep(attr="int"), True),
        ("a", "a", AttrRep(attr="str_cs"), False),
        ("A", "a", AttrRep(attr="str_cs"), True),
        (True, True, AttrRep(attr="bool"), False),
        (True, False, AttrRep(attr="bool"), True),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            AttrRep(attr="datetime"),
            False,
        ),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 2).isoformat(),
            AttrRep(attr="datetime"),
            True,
        ),
        (3.14, 3.14, AttrRep(attr="decimal"), False),
        (3.14, 3.141, AttrRep(attr="decimal"), True),
        (
            "YQ==",
            "YQ==",
            AttrRep(attr="binary"),
            False,
        ),
        (
            "YQ==",
            "Yg==",
            AttrRep(attr="binary"),
            True,
        ),
        (
            "https://www.example.com",
            "https://www.example.com",
            AttrRep(attr="external_ref"),
            False,
        ),
        (
            "https://www.example.com",
            "https://www.bad_example.com",
            AttrRep(attr="external_ref"),
            True,
        ),
        (
            "whatever/some/location/",
            "whatever/some/location/",
            AttrRep(attr="uri_ref"),
            False,
        ),
        (
            "whatever/some/location/",
            "whatever/some/other/location/",
            AttrRep(attr="uri_ref"),
            True,
        ),
        (
            "Users",
            "Users",
            AttrRep(attr="scim_ref"),
            False,
        ),
        (
            "Users",
            "Groups",
            AttrRep(attr="scim_ref"),
            True,
        ),
    ),
)
def test_not_equal_operator(value, operator_value, attribute_name, expected):
    operator = NotEqual(attribute_name, operator_value)

    actual = operator.match(value, SchemaForTests)

    assert actual == expected


@pytest.mark.parametrize(
    ("value", "operator_value", "attribute_name", "expected"),
    (
        (1, 1, AttrRep(attr="int"), False),
        (2, 1, AttrRep(attr="int"), True),
        ("a", "a", AttrRep(attr="str_cs"), False),
        ("a", "A", AttrRep(attr="str_cs"), True),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            AttrRep(attr="datetime"),
            False,
        ),
        (
            datetime(2023, 10, 10, 21, 27, 2).isoformat(),
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            AttrRep(attr="datetime"),
            True,
        ),
        (3.14, 3.14, AttrRep(attr="decimal"), False),
        (3.141, 3.14, AttrRep(attr="decimal"), True),
    ),
)
def test_greater_than_operator(value, operator_value, attribute_name, expected):
    operator = GreaterThan(attribute_name, operator_value)

    actual = operator.match(value, SchemaForTests)

    assert actual == expected


@pytest.mark.parametrize(
    ("value", "operator_value", "attribute_name", "expected"),
    (
        (1, 2, AttrRep(attr="int"), False),
        (1, 1, AttrRep(attr="int"), True),
        (2, 1, AttrRep(attr="int"), True),
        ("A", "a", AttrRep(attr="str_cs"), False),
        ("a", "a", AttrRep(attr="str_cs"), True),
        ("a", "A", AttrRep(attr="str_cs"), True),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 2).isoformat(),
            AttrRep(attr="datetime"),
            False,
        ),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            AttrRep(attr="datetime"),
            True,
        ),
        (
            datetime(2023, 10, 10, 21, 27, 2).isoformat(),
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            AttrRep(attr="datetime"),
            True,
        ),
        (3.14, 3.141, AttrRep(attr="decimal"), False),
        (3.14, 3.14, AttrRep(attr="decimal"), True),
        (3.141, 3.14, AttrRep(attr="decimal"), True),
    ),
)
def test_greater_than_or_equal_operator(value, operator_value, attribute_name, expected):
    operator = GreaterThanOrEqual(attribute_name, operator_value)

    actual = operator.match(value, SchemaForTests)

    assert actual == expected


@pytest.mark.parametrize(
    ("value", "operator_value", "attribute_name", "expected"),
    (
        (1, 1, AttrRep(attr="int"), False),
        (1, 2, AttrRep(attr="int"), True),
        ("a", "a", AttrRep(attr="str_cs"), False),
        ("A", "a", AttrRep(attr="str_cs"), True),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            AttrRep(attr="datetime"),
            False,
        ),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 2).isoformat(),
            AttrRep(attr="datetime"),
            True,
        ),
        (3.14, 3.14, AttrRep(attr="decimal"), False),
        (3.14, 3.141, AttrRep(attr="decimal"), True),
    ),
)
def test_lesser_than_operator(value, operator_value, attribute_name, expected):
    operator = LesserThan(attribute_name, operator_value)

    actual = operator.match(value, SchemaForTests)

    assert actual == expected


@pytest.mark.parametrize(
    ("value", "operator_value", "attribute_name", "expected"),
    (
        (1, 2, AttrRep(attr="int"), True),
        (1, 1, AttrRep(attr="int"), True),
        (2, 1, AttrRep(attr="int"), False),
        ("A", "a", AttrRep(attr="str_cs"), True),
        ("a", "a", AttrRep(attr="str_cs"), True),
        ("a", "A", AttrRep(attr="str_cs"), False),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 2).isoformat(),
            AttrRep(attr="datetime"),
            True,
        ),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            AttrRep(attr="datetime"),
            True,
        ),
        (
            datetime(2023, 10, 10, 21, 27, 2).isoformat(),
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            AttrRep(attr="datetime"),
            False,
        ),
        (3.14, 3.141, AttrRep(attr="decimal"), True),
        (3.14, 3.14, AttrRep(attr="decimal"), True),
        (3.141, 3.14, AttrRep(attr="decimal"), False),
    ),
)
def test_lesser_than_or_equal_operator(value, operator_value, attribute_name, expected):
    operator = LesserThanOrEqual(attribute_name, operator_value)

    actual = operator.match(value, SchemaForTests)

    assert actual == expected


def test_binary_operator_does_not_match_if_non_matching_attribute_type():
    operator = Equal(AttrRep(attr="int"), "1")

    match = operator.match(1, SchemaForTests)

    assert not match


def test_binary_operator_does_not_match_if_attr_missing_in_schema():
    operator = Equal(AttrRep(attr="other_int"), 1)

    match = operator.match(1, SchemaForTests)

    assert not match


def test_binary_operator_does_not_match_if_not_supported_scim_type():
    operator = GreaterThan(AttrRep(attr="scim_ref"), chr(0))

    match = operator.match("Users", SchemaForTests)

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
    operator = operator_cls(AttrRep(attr="str"), "A")

    actual = operator.match("a", SchemaForTests)

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
    operator = Contains(AttrRep(attr="str_cs"), operator_value)

    actual = operator.match(value, SchemaForTests)

    assert actual == expected


@pytest.mark.parametrize(
    ("value", "operator_value", "expected"),
    (
        ("abc", "ab", True),
        ("abc", "bc", False),
        ("abc", "cd", False),
        ("ab", "abc", False),
        ("ab", "", False),
    ),
)
def test_starts_with_operator(value, operator_value, expected):
    operator = StartsWith(AttrRep(attr="str_cs"), operator_value)

    actual = operator.match(value, SchemaForTests)

    assert actual == expected


@pytest.mark.parametrize(
    ("value", "operator_value", "expected"),
    (
        ("abc", "ab", False),
        ("abc", "bc", True),
        ("abc", "cd", False),
        ("ab", "abc", False),
        ("ab", "", False),
    ),
)
def test_ends_with_operator(value, operator_value, expected):
    operator = EndsWith(AttrRep(attr="str_cs"), operator_value)

    actual = operator.match(value, SchemaForTests)

    assert actual == expected


def test_multi_value_attribute_is_matched_if_one_of_values_match():
    operator = Equal(AttrRep(attr="str_cs_mv"), "abc")

    match = operator.match(["b", "c", "ab", "abc", "ca"], SchemaForTests)

    assert match


def test_multi_value_attribute_is_matched_if_one_of_case_insensitive_values_match():
    operator = Equal(AttrRep(attr="str_mv"), "abc")

    match = operator.match(["b", "c", "ab", "ABc", "ca"], SchemaForTests)

    assert match


@pytest.mark.parametrize(
    ("value", "attribute_name", "expected"),
    (
        ("", AttrRep(attr="str"), False),
        ("abc", AttrRep(attr="str"), True),
        (None, AttrRep(attr="bool"), False),
        (False, AttrRep(attr="bool"), True),
        ([], AttrRep(attr="str_mv"), False),
        (
            ["a", "b", "c"],
            AttrRep(attr="str_mv"),
            True,
        ),
        (
            {
                "value": "",
            },
            AttrRep(attr="c"),
            False,
        ),
        (
            {
                "value": "abc",
            },
            AttrRep(attr="c"),
            True,
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
            AttrRep(attr="c_mv"),
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
            AttrRep(attr="c_mv"),
            True,
        ),
    ),
)
def test_present_operator(value, attribute_name, expected):
    operator = Present(attribute_name)

    actual = operator.match(value, SchemaForTests)

    assert actual == expected


def test_complex_attribute_matches_binary_operator_if_one_of_values_matches():
    operator = StartsWith(AttrRep(attr="c_mv"), "abc")

    match = operator.match([{"value": "a"}, {"value": "bac"}, {"value": "abcd"}], SchemaForTests)

    assert match


def test_complex_attribute_does_not_match_binary_operator_if_not_any_of_values_matches():
    operator = StartsWith(AttrRep(attr="c_mv"), "abc")

    match = operator.match([{"value": "a"}, {"value": "bac"}, {"value": "bcdd"}], SchemaForTests)

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
        Equal(AttrRep(attr="int"), 1),
        And(
            GreaterThan(AttrRep(attr="decimal"), 1.0),
            NotEqual(AttrRep(attr="str"), "1"),
        ),
        Or(
            Equal(AttrRep(attr="bool"), True),
            StartsWith(AttrRep(attr="str_cs"), "a"),
        ),
    )

    actual = operator.match(
        SCIMDataContainer(
            {
                "int": 1,
                "decimal": 1.1,
                "str": "2",
                "bool": False,
                "str_cs": str_cs_value,
            }
        ),
        SchemaForTests,
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
        Equal(AttrRep(attr="int"), 1),
        And(
            GreaterThan(AttrRep(attr="decimal"), 1.0),
            NotEqual(AttrRep(attr="str"), "1"),
        ),
        Or(
            Equal(AttrRep(attr="bool"), True),
            StartsWith(AttrRep(attr="str_cs"), "a"),
        ),
    )

    actual = operator.match(
        SCIMDataContainer(
            {
                "int": 2,
                "decimal": 1.0,
                "str": "1",
                "bool": False,
                "str_cs": str_cs_value,
            }
        ),
        SchemaForTests,
    )

    assert actual == expected


def test_complex_attribute_operator_matches_all_complex_sub_attrs():
    operator = ComplexAttributeOperator(
        attr_rep=AttrRep(attr="c2"),
        sub_operator=And(
            Equal(AttrRep(attr="str"), "admin"),
            GreaterThan(AttrRep(attr="int"), 18),
            NotEqual(AttrRep(attr="bool"), True),
        ),
    )

    match = operator.match(
        SCIMDataContainer({"str": "admin", "int": 19, "bool": False}), SchemaForTests
    )

    assert match


def test_complex_attribute_operator_does_not_match_all_complex_sub_attrs():
    operator = ComplexAttributeOperator(
        attr_rep=AttrRep(attr="c2"),
        sub_operator=Or(
            Equal(AttrRep(attr="str"), "admin"),
            GreaterThan(AttrRep(attr="int"), 18),
            NotEqual(AttrRep(attr="bool"), True),
        ),
    )

    match = operator.match(
        SCIMDataContainer({"str": "user", "int": 18, "bool": True}), SchemaForTests
    )

    assert not match


def test_complex_attr_op_matches_some_of_sub_attrs_of_multi_valued_complex_attr():
    operator = ComplexAttributeOperator(
        attr_rep=AttrRep(attr="c2_mv"),
        sub_operator=And(
            Equal(AttrRep(attr="str"), "admin"),
            GreaterThan(AttrRep(attr="int"), 18),
            NotEqual(AttrRep(attr="bool"), True),
        ),
    )

    match = operator.match(
        [
            SCIMDataContainer({"str": "admin", "int": 19, "bool": False}),
            SCIMDataContainer({"str": "user", "int": 18, "bool": True}),
            SCIMDataContainer({"str": "user", "int": 19, "bool": False}),
        ],
        SchemaForTests,
    )

    assert match


def test_complex_attr_op_does_not_match_any_of_multi_valued_complex_sub_attrs():
    operator = ComplexAttributeOperator(
        attr_rep=AttrRep(attr="c2_mv"),
        sub_operator=Or(
            Equal(AttrRep(attr="str"), "admin"),
            GreaterThan(AttrRep(attr="int"), 18),
            NotEqual(AttrRep(attr="bool"), True),
        ),
    )

    match = operator.match(
        [
            SCIMDataContainer({"str": "user", "int": 16, "bool": True}),
            SCIMDataContainer({"str": "customer", "int": 18, "bool": True}),
            SCIMDataContainer({"str": "santa-claus", "int": 12, "bool": True}),
        ],
        SchemaForTests,
    )

    assert not match


@pytest.mark.parametrize(
    ("value", "is_multivalued", "expected"),
    (
        (
            SCIMDataContainer({"str": "admin", "int": 19, "bool": False}),
            False,
            True,
        ),
        (
            SCIMDataContainer({"str": "user", "int": 18, "bool": True}),
            False,
            False,
        ),
        (
            [
                SCIMDataContainer({"str": "admin", "int": 19, "bool": False}),
                SCIMDataContainer({"str": "user", "int": 18, "bool": True}),
                SCIMDataContainer({"str": "user", "int": 19, "bool": False}),
            ],
            True,
            True,
        ),
        (
            [
                SCIMDataContainer({"str": "user", "int": 16, "bool": True}),
                SCIMDataContainer({"str": "customer", "int": 18, "bool": True}),
                SCIMDataContainer({"str": "santa-claus", "int": 12, "bool": True}),
            ],
            True,
            False,
        ),
    ),
)
def test_attribute_operator_matches_single_complex_sub_attr(value, is_multivalued, expected):
    if is_multivalued:
        operator = ComplexAttributeOperator(
            attr_rep=AttrRep(attr="c2_mv"),
            sub_operator=Equal(AttrRep(attr="str"), "admin"),
        )
    else:
        operator = ComplexAttributeOperator(
            attr_rep=AttrRep(attr="c2"),
            sub_operator=Equal(AttrRep(attr="str"), "admin"),
        )

    actual = operator.match(value, SchemaForTests)

    assert actual == expected


def test_binary_op_does_not_match_if_no_value_provided():
    operator = Equal(AttrRep(attr="str"), "abc")

    match = operator.match(None, SchemaForTests)

    assert not match


def test_complex_op_does_not_matches_if_sub_attribute_not_provided():
    operator = ComplexAttributeOperator(
        attr_rep=AttrRep(attr="c"),
        sub_operator=Equal(AttrRep(attr="str"), "abc"),
    )

    match = operator.match(SCIMDataContainer({}), SchemaForTests)

    assert not match


def test_or_op_does_not_match_if_no_sub_attr_matched():
    operator = Or(
        Equal(AttrRep(attr="int"), 1),
        Equal(AttrRep(attr="str"), "abc"),
    )

    match = operator.match(SCIMDataContainer({"int": 2}), SchemaForTests)

    assert not match


def test_or_op_matches_if_any_sub_attr_matched():
    operator = Or(
        Equal(AttrRep(attr="int"), 1),
        Equal(AttrRep(attr="str"), "abc"),
    )

    match = operator.match(SCIMDataContainer({"int": 1}), SchemaForTests)

    assert match


def test_and_op_does_not_match_if_any_sub_attr_is_without_data():
    operator = And(
        Equal(AttrRep(attr="int"), 1),
        Equal(AttrRep(attr="str"), "abc"),
    )
    value = {"int": 1}  # value for this attr is correct, but missing 'str'

    match = operator.match(SCIMDataContainer(value), SchemaForTests)

    assert not match


def test_and_op_does_not_match_if_any_sub_attr_does_not_match():
    operator = And(
        Equal(AttrRep(attr="int"), 1),
        Equal(AttrRep(attr="str"), "abc"),
    )

    match = operator.match(SCIMDataContainer({"int": 1, "str": "cba"}), SchemaForTests)

    assert not match


def test_not_op_matches_if_missing_value_in_logical_sub_op():
    operator = Not(
        Or(
            Equal(AttrRep(attr="int"), 1),
            Equal(AttrRep(attr="str"), "abc"),
        ),
    )

    match = operator.match(SCIMDataContainer({"int": 2}), SchemaForTests)

    assert match


def test_not_op_matches_for_missing_value_in_attr_sub_op():
    operator = Not(Equal(AttrRep(attr="int"), 1))

    match = operator.match(SCIMDataContainer({}), SchemaForTests)

    assert match


def test_not_op_matches_if_op_attr_not_in_attrs():
    operator = Not(Equal(AttrRep(attr="other_attr"), 1))

    match = operator.match(SCIMDataContainer({"other_attr": 2}), SchemaForTests)

    assert match


def test_not_op_matches_if_no_data_for_pr_sub_op():
    operator = Not(Present(AttrRep(attr="int")))

    match = operator.match(SCIMDataContainer({}), SchemaForTests)

    assert match


@pytest.mark.parametrize(("value", "expected"), ((1.0, True), (2.0, False)))
def test_binary_attributes_allows_to_compare_int_with_decimal(value, expected):
    operator = Equal(AttrRep(attr="decimal"), 1)

    match = operator.match(value, SchemaForTests)

    assert bool(match) is expected


@pytest.mark.parametrize(("value", "expected"), ((1, True), (2, False)))
def test_binary_attributes_allows_to_compare_decimal_with_int(value, expected):
    operator = Equal(AttrRep(attr="int"), 1.0)

    match = operator.match(value, SchemaForTests)

    assert bool(match) is expected


def test_complex_op_can_be_used_with_logical_op():
    operator = ComplexAttributeOperator(
        attr_rep=AttrRep(attr="c2"),
        sub_operator=And(Equal(AttrRep(attr="int"), 1), Equal(AttrRep(attr="str"), "abc")),
    )

    match = operator.match(SCIMDataContainer({"int": 1, "str": "abc"}), SchemaForTests)

    assert match


def test_complex_op_used_with_or_op_matches_if_at_least_one_sub_attr_matches():
    operator = ComplexAttributeOperator(
        attr_rep=AttrRep(attr="c2"),
        sub_operator=Or(Equal(AttrRep(attr="int"), 1), Equal(AttrRep(attr="str"), "abc")),
    )

    match = operator.match(SCIMDataContainer({"int": 1}), SchemaForTests)

    assert match


def test_complex_op_used_with_or_op_does_not_match_if_no_values_provided():
    operator = ComplexAttributeOperator(
        attr_rep=AttrRep(attr="c2"),
        sub_operator=Or(Equal(AttrRep(attr="int"), 1), Equal(AttrRep(attr="str"), "abc")),
    )

    match = operator.match(SCIMDataContainer({}), SchemaForTests)

    assert not match


def test_multivalued_complex_op_can_be_used_with_logical_op():
    operator = ComplexAttributeOperator(
        attr_rep=AttrRep(attr="c2_mv"),
        sub_operator=And(Equal(AttrRep(attr="int"), 1), Equal(AttrRep(attr="str"), "abc")),
    )

    match = operator.match(
        [
            SCIMDataContainer({"int": 2, "str": "abc"}),
            SCIMDataContainer({"int": 1, "str": "cba"}),
            SCIMDataContainer({"int": 1, "str": "abc"}),
        ],
        SchemaForTests,
    )

    assert match


def test_operator_values_are_converted_if_deserializer_registered():
    DateTime.set_deserializer(datetime.fromisoformat)

    operator = GreaterThan(attr_rep=AttrRep(attr="datetime"), value="2024-04-29T18:14:15.189594")

    match = operator.match(datetime.now(), SchemaForTests)

    assert match

    DateTime.set_deserializer(str)


def test_value_is_not_matched_if_bad_input_value_type():
    operator = GreaterThan(attr_rep=AttrRep(attr="str"), value="abc")

    match = operator.match(1, SchemaForTests)

    assert not match


def test_value_is_not_matched_if_bad_operator_value_type():
    operator = GreaterThan(attr_rep=AttrRep(attr="str"), value=1)

    match = operator.match("abc", SchemaForTests)

    assert not match


def test_matching_unary_operator_fails_if_missing_attr():
    op = Present(attr_rep=AttrRep("attr"))
    complex_attr = Complex("complex")

    assert op.match({"attr": "I'm here!"}, complex_attr) is False


def test_matching_unary_operator_fails_if_attr_scim_type_is_not_supported():
    class CustomAttribute(Attribute):
        SCIM_TYPE = "dontYouEverDoThat"

    op = Present(attr_rep=AttrRep("attr"))

    complex_attr = Complex("complex", sub_attributes=[CustomAttribute("attr")])

    assert op.match({"attr": "I'm here!"}, complex_attr) is False


def test_matching_unary_operator_fails_if_attr_multivalued_but_value_is_not_list():
    op = Present(attr_rep=AttrRep("attr"))

    complex_attr = Complex("complex", sub_attributes=[String("attr", multi_valued=True)])

    assert op.match({"attr": "I'm here!"}, complex_attr) is False


def test_binary_operator_does_not_match_complex_attr_if_no_value_sub_attr():
    op = Equal(attr_rep=AttrRep(attr="c2"), value="test")

    # c2 has no 'value' sub-attr in 'SchemaForTests'
    match = op.match({"c2": [{"value": "test"}]}, SchemaForTests)

    assert match is False


def test_binary_operator_does_not_match_complex_attr_if_not_multivalued():
    op = Equal(attr_rep=AttrRep(attr="c"), value="test")

    # c is not multivalued in 'SchemaForTests'
    match = op.match({"c": {"value": "test"}}, SchemaForTests)

    assert match is False


def test_complex_operator_does_not_match_if_no_attr_in_schema():
    op = ComplexAttributeOperator(
        attr_rep=AttrRep(attr="non_existing"),
        sub_operator=Equal(attr_rep=AttrRep(attr="sub_attr"), value="test"),
    )

    assert op.match({"sub_attr": "test"}, User) is False


def test_complex_operator_does_not_match_if_attr_is_not_complex():
    op = ComplexAttributeOperator(
        attr_rep=AttrRep(attr="userName"),
        sub_operator=Equal(attr_rep=AttrRep(attr="formatted"), value="test"),
    )

    assert op.match({"formatted": "test"}, User) is False


def test_complex_operator_does_not_match_if_provided_list_for_single_valued_attr():
    op = ComplexAttributeOperator(
        attr_rep=AttrRep(attr="name"),
        sub_operator=Equal(attr_rep=AttrRep(attr="formatted"), value="test"),
    )

    assert op.match([{"formatted": "test"}], User) is False


def test_complex_operator_does_not_match_if_provided_mapping_for_multi_valued_attr():
    op = ComplexAttributeOperator(
        attr_rep=AttrRep(attr="emails"),
        sub_operator=Equal(attr_rep=AttrRep(attr="value"), value="test@example.com"),
    )

    assert op.match({"value": "test@example.com"}, User) is False
