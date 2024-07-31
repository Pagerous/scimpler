from datetime import datetime

import pytest

from scimple.container import AttrRep, SCIMData
from scimple.data.attrs import Attribute, Complex, DateTime, String
from scimple.data.operator import (
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
def test_equal_operator(value, operator_value, attr_rep, expected, fake_schema):
    operator = Equal(attr_rep, operator_value)

    actual = operator.match(SCIMData({attr_rep: value}), fake_schema)

    assert actual == expected


@pytest.mark.parametrize(
    ("value", "operator_value", "attr_rep", "expected"),
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
def test_not_equal_operator(value, operator_value, attr_rep, expected, fake_schema):
    operator = NotEqual(attr_rep, operator_value)

    actual = operator.match(SCIMData({attr_rep: value}), fake_schema)

    assert actual == expected


@pytest.mark.parametrize(
    ("value", "operator_value", "attr_rep", "expected"),
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
def test_greater_than_operator(value, operator_value, attr_rep, expected, fake_schema):
    operator = GreaterThan(attr_rep, operator_value)

    actual = operator.match(SCIMData({attr_rep: value}), fake_schema)

    assert actual == expected


@pytest.mark.parametrize(
    ("value", "operator_value", "attr_rep", "expected"),
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
def test_greater_than_or_equal_operator(value, operator_value, attr_rep, expected, fake_schema):
    operator = GreaterThanOrEqual(attr_rep, operator_value)

    actual = operator.match(SCIMData({attr_rep: value}), fake_schema)

    assert actual == expected


@pytest.mark.parametrize(
    ("value", "operator_value", "attr_rep", "expected"),
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
def test_lesser_than_operator(value, operator_value, attr_rep, expected, fake_schema):
    operator = LesserThan(attr_rep, operator_value)

    actual = operator.match(SCIMData({attr_rep: value}), fake_schema)

    assert actual == expected


@pytest.mark.parametrize(
    ("value", "operator_value", "attr_rep", "expected"),
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
def test_lesser_than_or_equal_operator(value, operator_value, attr_rep, expected, fake_schema):
    operator = LesserThanOrEqual(attr_rep, operator_value)

    actual = operator.match(SCIMData({attr_rep: value}), fake_schema)

    assert actual == expected


def test_binary_operator_does_not_match_if_non_matching_attribute_type(fake_schema):
    attr_rep = AttrRep(attr="int")
    operator = Equal(attr_rep, "1")

    match = operator.match(SCIMData({attr_rep: 1}), fake_schema)

    assert not match


def test_binary_operator_does_not_match_if_attr_missing_in_schema(fake_schema):
    attr_rep = AttrRep(attr="other_int")
    operator = Equal(AttrRep(attr="other_int"), 1)

    match = operator.match(SCIMData({attr_rep: 1}), fake_schema)

    assert not match


def test_binary_operator_does_not_match_if_not_supported_scim_type(fake_schema):
    attr_rep = AttrRep(attr="scim_ref")
    operator = GreaterThan(AttrRep(attr="scim_ref"), chr(0))

    match = operator.match(SCIMData({attr_rep: "Users"}), fake_schema)

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
def test_case_insensitive_attributes_are_compared_correctly(operator_cls, expected, fake_schema):
    attr_rep = AttrRep(attr="str")
    operator = operator_cls(attr_rep, "A")

    actual = operator.match(SCIMData({attr_rep: "a"}), fake_schema)

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
def test_contains_operator(value, operator_value, expected, fake_schema):
    attr_rep = AttrRep(attr="str_cs")
    operator = Contains(attr_rep, operator_value)

    actual = operator.match(SCIMData({attr_rep: value}), fake_schema)

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
def test_starts_with_operator(value, operator_value, expected, fake_schema):
    attr_rep = AttrRep(attr="str_cs")
    operator = StartsWith(attr_rep, operator_value)

    actual = operator.match(SCIMData({attr_rep: value}), fake_schema)

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
def test_ends_with_operator(value, operator_value, expected, fake_schema):
    attr_rep = AttrRep(attr="str_cs")
    operator = EndsWith(attr_rep, operator_value)

    actual = operator.match(SCIMData({attr_rep: value}), fake_schema)

    assert actual == expected


def test_multi_value_attribute_is_matched_if_one_of_values_match(fake_schema):
    attr_rep = AttrRep(attr="str_cs_mv")
    operator = Equal(AttrRep(attr="str_cs_mv"), "abc")

    match = operator.match(SCIMData({attr_rep: ["b", "c", "ab", "abc", "ca"]}), fake_schema)

    assert match


def test_multi_value_attribute_is_matched_if_one_of_case_insensitive_values_match(fake_schema):
    attr_rep = AttrRep(attr="str_mv")
    operator = Equal(attr_rep, "abc")

    match = operator.match(SCIMData({attr_rep: ["b", "c", "ab", "ABc", "ca"]}), fake_schema)

    assert match


@pytest.mark.parametrize(
    ("value", "attr_rep", "expected"),
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
def test_present_operator(value, attr_rep, expected, fake_schema):
    operator = Present(attr_rep)

    actual = operator.match(SCIMData({attr_rep: value}), fake_schema)

    assert actual == expected


def test_complex_attribute_matches_binary_operator_if_one_of_values_matches(fake_schema):
    attr_rep = AttrRep(attr="c_mv")
    operator = StartsWith(attr_rep, "abc")

    match = operator.match(
        SCIMData({attr_rep: [{"value": "a"}, {"value": "bac"}, {"value": "abcd"}]}),
        fake_schema,
    )

    assert match


def test_complex_attribute_does_not_match_binary_operator_if_not_any_of_values_matches(fake_schema):
    attr_rep = AttrRep(attr="c_mv")
    operator = StartsWith(attr_rep, "abc")

    match = operator.match(
        SCIMData({attr_rep: [{"value": "a"}, {"value": "bac"}, {"value": "bcdd"}]}),
        fake_schema,
    )

    assert not match


@pytest.mark.parametrize(
    ("str_cs_value", "expected"),
    (
        ("a", True),
        ("b", False),
    ),
)
def test_and_operator_matches(str_cs_value, expected, fake_schema):
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
        SCIMData(
            {
                "int": 1,
                "decimal": 1.1,
                "str": "2",
                "bool": False,
                "str_cs": str_cs_value,
            }
        ),
        fake_schema,
    )

    assert actual == expected


@pytest.mark.parametrize(
    ("str_cs_value", "expected"),
    (
        ("a", True),
        ("b", False),
    ),
)
def test_or_operator_matches(str_cs_value, expected, fake_schema):
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
        SCIMData(
            {
                "int": 2,
                "decimal": 1.0,
                "str": "1",
                "bool": False,
                "str_cs": str_cs_value,
            }
        ),
        fake_schema,
    )

    assert actual == expected


def test_complex_attribute_operator_matches_all_complex_sub_attrs(fake_schema):
    attr_rep = AttrRep(attr="c2")
    operator = ComplexAttributeOperator(
        attr_rep,
        sub_operator=And(
            Equal(AttrRep(attr="str"), "admin"),
            GreaterThan(AttrRep(attr="int"), 18),
            NotEqual(AttrRep(attr="bool"), True),
        ),
    )

    match = operator.match(
        SCIMData({attr_rep: {"str": "admin", "int": 19, "bool": False}}), fake_schema
    )

    assert match


def test_complex_attribute_operator_does_not_match_all_complex_sub_attrs(fake_schema):
    operator = ComplexAttributeOperator(
        attr_rep=AttrRep(attr="c2"),
        sub_operator=Or(
            Equal(AttrRep(attr="str"), "admin"),
            GreaterThan(AttrRep(attr="int"), 18),
            NotEqual(AttrRep(attr="bool"), True),
        ),
    )

    match = operator.match(SCIMData({"str": "user", "int": 18, "bool": True}), fake_schema)

    assert not match


def test_complex_attr_op_matches_some_of_sub_attrs_of_multi_valued_complex_attr(fake_schema):
    attr_rep = AttrRep(attr="c2_mv")
    operator = ComplexAttributeOperator(
        attr_rep,
        sub_operator=And(
            Equal(AttrRep(attr="str"), "admin"),
            GreaterThan(AttrRep(attr="int"), 18),
            NotEqual(AttrRep(attr="bool"), True),
        ),
    )

    match = operator.match(
        SCIMData(
            {
                attr_rep: [
                    SCIMData({"str": "admin", "int": 19, "bool": False}),
                    SCIMData({"str": "user", "int": 18, "bool": True}),
                    SCIMData({"str": "user", "int": 19, "bool": False}),
                ]
            }
        ),
        fake_schema,
    )

    assert match


def test_complex_attr_op_does_not_match_any_of_multi_valued_complex_sub_attrs(fake_schema):
    attr_rep = AttrRep(attr="c2_mv")
    operator = ComplexAttributeOperator(
        attr_rep,
        sub_operator=Or(
            Equal(AttrRep(attr="str"), "admin"),
            GreaterThan(AttrRep(attr="int"), 18),
            NotEqual(AttrRep(attr="bool"), True),
        ),
    )

    match = operator.match(
        SCIMData(
            {
                attr_rep: [
                    SCIMData({"str": "user", "int": 16, "bool": True}),
                    SCIMData({"str": "customer", "int": 18, "bool": True}),
                    SCIMData({"str": "santa-claus", "int": 12, "bool": True}),
                ],
            }
        ),
        fake_schema,
    )

    assert not match


@pytest.mark.parametrize(
    ("value", "is_multivalued", "expected"),
    (
        (
            SCIMData({"str": "admin", "int": 19, "bool": False}),
            False,
            True,
        ),
        (
            SCIMData({"str": "user", "int": 18, "bool": True}),
            False,
            False,
        ),
        (
            [
                SCIMData({"str": "admin", "int": 19, "bool": False}),
                SCIMData({"str": "user", "int": 18, "bool": True}),
                SCIMData({"str": "user", "int": 19, "bool": False}),
            ],
            True,
            True,
        ),
        (
            [
                SCIMData({"str": "user", "int": 16, "bool": True}),
                SCIMData({"str": "customer", "int": 18, "bool": True}),
                SCIMData({"str": "santa-claus", "int": 12, "bool": True}),
            ],
            True,
            False,
        ),
    ),
)
def test_attribute_operator_matches_single_complex_sub_attr(
    value, is_multivalued, expected, fake_schema
):
    attr_rep = AttrRep(attr="c2_mv") if is_multivalued else AttrRep(attr="c2")
    operator = ComplexAttributeOperator(
        attr_rep=attr_rep,
        sub_operator=Equal(AttrRep(attr="str"), "admin"),
    )

    actual = operator.match(SCIMData({attr_rep: value}), fake_schema)

    assert actual == expected


def test_binary_op_does_not_match_if_no_value_provided(fake_schema):
    operator = Equal(AttrRep(attr="str"), "abc")

    match = operator.match(None, fake_schema)

    assert not match


def test_complex_op_does_not_matches_if_sub_attribute_not_provided(fake_schema):
    operator = ComplexAttributeOperator(
        attr_rep=AttrRep(attr="c"),
        sub_operator=Equal(AttrRep(attr="str"), "abc"),
    )

    match = operator.match(SCIMData({}), fake_schema)

    assert not match


def test_or_op_does_not_match_if_no_sub_attr_matched(fake_schema):
    operator = Or(
        Equal(AttrRep(attr="int"), 1),
        Equal(AttrRep(attr="str"), "abc"),
    )

    match = operator.match(SCIMData({"int": 2}), fake_schema)

    assert not match


def test_or_op_matches_if_any_sub_attr_matched(fake_schema):
    operator = Or(
        Equal(AttrRep(attr="int"), 1),
        Equal(AttrRep(attr="str"), "abc"),
    )

    match = operator.match(SCIMData({"int": 1}), fake_schema)

    assert match


def test_and_op_does_not_match_if_any_sub_attr_is_without_data(fake_schema):
    operator = And(
        Equal(AttrRep(attr="int"), 1),
        Equal(AttrRep(attr="str"), "abc"),
    )
    value = {"int": 1}  # value for this attr is correct, but missing 'str'

    match = operator.match(SCIMData(value), fake_schema)

    assert not match


def test_and_op_does_not_match_if_any_sub_attr_does_not_match(fake_schema):
    operator = And(
        Equal(AttrRep(attr="int"), 1),
        Equal(AttrRep(attr="str"), "abc"),
    )

    match = operator.match(SCIMData({"int": 1, "str": "cba"}), fake_schema)

    assert not match


def test_not_op_matches_if_missing_value_in_logical_sub_op(fake_schema):
    operator = Not(
        Or(
            Equal(AttrRep(attr="int"), 1),
            Equal(AttrRep(attr="str"), "abc"),
        ),
    )

    match = operator.match(SCIMData({"int": 2}), fake_schema)

    assert match


def test_not_op_matches_for_missing_value_in_attr_sub_op(fake_schema):
    operator = Not(Equal(AttrRep(attr="int"), 1))

    match = operator.match(SCIMData({}), fake_schema)

    assert match


def test_not_op_matches_if_op_attr_not_in_attrs(fake_schema):
    operator = Not(Equal(AttrRep(attr="other_attr"), 1))

    match = operator.match(SCIMData({"other_attr": 2}), fake_schema)

    assert match


def test_not_op_matches_if_no_data_for_pr_sub_op(fake_schema):
    operator = Not(Present(AttrRep(attr="int")))

    match = operator.match(SCIMData({}), fake_schema)

    assert match


@pytest.mark.parametrize(("value", "expected"), ((1.0, True), (2.0, False)))
def test_binary_attributes_allows_to_compare_int_with_decimal(value, expected, fake_schema):
    attr_rep = AttrRep(attr="decimal")
    operator = Equal(attr_rep, 1)

    match = operator.match(SCIMData({attr_rep: value}), fake_schema)

    assert bool(match) is expected


@pytest.mark.parametrize(("value", "expected"), ((1, True), (2, False)))
def test_binary_attributes_allows_to_compare_decimal_with_int(value, expected, fake_schema):
    attr_rep = AttrRep(attr="int")
    operator = Equal(attr_rep, 1.0)

    match = operator.match(SCIMData({attr_rep: value}), fake_schema)

    assert bool(match) is expected


def test_complex_op_can_be_used_with_logical_op(fake_schema):
    attr_rep = AttrRep(attr="c2")
    operator = ComplexAttributeOperator(
        attr_rep,
        sub_operator=And(Equal(AttrRep(attr="int"), 1), Equal(AttrRep(attr="str"), "abc")),
    )

    match = operator.match(SCIMData({attr_rep: {"int": 1, "str": "abc"}}), fake_schema)

    assert match


def test_complex_op_used_with_or_op_matches_if_at_least_one_sub_attr_matches(fake_schema):
    attr_rep = AttrRep(attr="c2")
    operator = ComplexAttributeOperator(
        attr_rep,
        sub_operator=Or(Equal(AttrRep(attr="int"), 1), Equal(AttrRep(attr="str"), "abc")),
    )

    match = operator.match(SCIMData({attr_rep: {"int": 1}}), fake_schema)

    assert match


def test_complex_op_used_with_or_op_does_not_match_if_no_values_provided(fake_schema):
    operator = ComplexAttributeOperator(
        attr_rep=AttrRep(attr="c2"),
        sub_operator=Or(Equal(AttrRep(attr="int"), 1), Equal(AttrRep(attr="str"), "abc")),
    )

    match = operator.match(SCIMData({}), fake_schema)

    assert not match


def test_multivalued_complex_op_can_be_used_with_logical_op(fake_schema):
    attr_rep = AttrRep(attr="c2_mv")
    operator = ComplexAttributeOperator(
        attr_rep,
        sub_operator=And(Equal(AttrRep(attr="int"), 1), Equal(AttrRep(attr="str"), "abc")),
    )

    match = operator.match(
        SCIMData(
            {
                attr_rep: [
                    SCIMData({"int": 2, "str": "abc"}),
                    SCIMData({"int": 1, "str": "cba"}),
                    SCIMData({"int": 1, "str": "abc"}),
                ]
            }
        ),
        fake_schema,
    )

    assert match


def test_operator_values_are_converted_if_deserializer_registered(fake_schema):
    DateTime.set_deserializer(datetime.fromisoformat)
    attr_rep = AttrRep(attr="datetime")
    operator = GreaterThan(attr_rep, value="2024-04-29T18:14:15.189594")

    match = operator.match(SCIMData({attr_rep: datetime.now()}), fake_schema)

    assert match

    DateTime.set_deserializer(str)


def test_value_is_not_matched_if_bad_input_value_type(fake_schema):
    attr_rep = AttrRep(attr="str")
    operator = GreaterThan(attr_rep, value="abc")

    match = operator.match(SCIMData({attr_rep: 1}), fake_schema)

    assert not match


def test_value_is_not_matched_if_bad_operator_value_type(fake_schema):
    attr_rep = AttrRep(attr="str")
    operator = GreaterThan(attr_rep, value=1)

    match = operator.match(SCIMData({attr_rep: "abc"}), fake_schema)

    assert not match


def test_matching_unary_operator_fails_if_missing_attr():
    op = Present(AttrRep("attr"))
    complex_attr = Complex("complex")

    assert op.match(SCIMData({"complex": {"attr": "I'm here!"}}), complex_attr) is False


def test_matching_unary_operator_fails_if_attr_scim_type_is_not_supported():
    class CustomAttribute(Attribute):
        @classmethod
        def scim_type(cls) -> str:
            return "dontYouEverDoThat"

        @classmethod
        def base_types(cls) -> tuple[type, ...]:
            return (str,)

    op = Present(attr_rep=AttrRep("attr"))

    complex_attr = Complex("complex", sub_attributes=[CustomAttribute("attr")])

    assert op.match(SCIMData({"complex": {"attr": "I'm here!"}}), complex_attr) is False


def test_matching_unary_operator_fails_if_attr_multivalued_but_value_is_not_list():
    op = Present(attr_rep=AttrRep("attr"))

    complex_attr = Complex("complex", sub_attributes=[String("attr", multi_valued=True)])

    assert op.match(SCIMData({"complex": {"attr": "I'm here!"}}), complex_attr) is False


def test_binary_operator_does_not_match_complex_attr_if_no_value_sub_attr(fake_schema):
    attr_rep = AttrRep(attr="c2")
    op = Equal(attr_rep, value="test")

    # c2 has no 'value' sub-attr in 'fake_schema'
    match = op.match(SCIMData({attr_rep: [{"value": "test"}]}), fake_schema)

    assert match is False


def test_binary_operator_does_not_match_complex_attr_if_not_multivalued(fake_schema):
    attr_rep = AttrRep(attr="c")
    op = Equal(attr_rep, value="test")

    # c is not multivalued in 'fake_schema'
    match = op.match(SCIMData({attr_rep: {"value": "test"}}), fake_schema)

    assert match is False


def test_complex_operator_does_not_match_if_no_attr_in_schema(user_schema):
    attr_rep = AttrRep(attr="non_existing")
    op = ComplexAttributeOperator(
        attr_rep=AttrRep(attr="non_existing"),
        sub_operator=Equal(attr_rep=AttrRep(attr="sub_attr"), value="test"),
    )

    assert op.match(SCIMData({attr_rep: {"sub_attr": "test"}}), user_schema) is False


def test_complex_operator_does_not_match_if_attr_is_not_complex(user_schema):
    attr_rep = AttrRep(attr="userName")
    op = ComplexAttributeOperator(
        attr_rep,
        sub_operator=Equal(attr_rep=AttrRep(attr="formatted"), value="test"),
    )

    assert op.match(SCIMData({attr_rep: {"formatted": "test"}}), user_schema) is False


def test_complex_operator_does_not_match_if_provided_list_for_single_valued_attr(user_schema):
    attr_rep = AttrRep(attr="name")
    op = ComplexAttributeOperator(
        attr_rep,
        sub_operator=Equal(attr_rep=AttrRep(attr="formatted"), value="test"),
    )

    assert op.match(SCIMData({attr_rep: [{"formatted": "test"}]}), user_schema) is False


def test_complex_operator_does_not_match_if_provided_mapping_for_multi_valued_attr(user_schema):
    attr_rep = AttrRep(attr="emails")
    op = ComplexAttributeOperator(
        attr_rep,
        sub_operator=Equal(attr_rep=AttrRep(attr="value"), value="test@example.com"),
    )

    assert op.match(SCIMData({attr_rep: {"value": "test@example.com"}}), user_schema) is False
