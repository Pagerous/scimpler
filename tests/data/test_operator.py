from datetime import datetime

import pytest

from src.data.container import AttrRep, SCIMDataContainer
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
    MatchStatus,
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
        (1, 1, AttrRep.parse("int"), True),
        (1, 2, AttrRep.parse("int"), False),
        ("a", "a", AttrRep.parse("str_cs"), True),
        ("A", "a", AttrRep.parse("str_cs"), False),
        (True, True, AttrRep.parse("bool"), True),
        (True, False, AttrRep.parse("bool"), False),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            AttrRep.parse("datetime"),
            True,
        ),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 2).isoformat(),
            AttrRep.parse("datetime"),
            False,
        ),
        (3.14, 3.14, AttrRep.parse("decimal"), True),
        (3.14, 3.141, AttrRep.parse("decimal"), False),
        (
            "YQ==",
            "YQ==",
            AttrRep.parse("binary"),
            True,
        ),
        (
            "YQ==",
            "Yg==",
            AttrRep.parse("binary"),
            False,
        ),
        (
            "https://www.example.com",
            "https://www.example.com",
            AttrRep.parse("external_ref"),
            True,
        ),
        (
            "https://www.example.com",
            "https://www.bad_example.com",
            AttrRep.parse("external_ref"),
            False,
        ),
        (
            "whatever/some/location/",
            "whatever/some/location/",
            AttrRep.parse("uri_ref"),
            True,
        ),
        (
            "whatever/some/location/",
            "whatever/some/other/location/",
            AttrRep.parse("uri_ref"),
            False,
        ),
        (
            "Users",
            "Users",
            AttrRep.parse("scim_ref"),
            True,
        ),
        (
            "Users",
            "Groups",
            AttrRep.parse("scim_ref"),
            False,
        ),
    ),
)
def test_equal_operator(value, operator_value, attr_rep, expected):
    operator = Equal(attr_rep, operator_value)

    actual = operator.match(value, SchemaForTests.attrs)

    assert actual == expected


@pytest.mark.parametrize(
    ("value", "operator_value", "attribute_name", "expected"),
    (
        (1, 1, AttrRep.parse("int"), False),
        (1, 2, AttrRep.parse("int"), True),
        ("a", "a", AttrRep.parse("str_cs"), False),
        ("A", "a", AttrRep.parse("str_cs"), True),
        (True, True, AttrRep.parse("bool"), False),
        (True, False, AttrRep.parse("bool"), True),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            AttrRep.parse("datetime"),
            False,
        ),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 2).isoformat(),
            AttrRep.parse("datetime"),
            True,
        ),
        (3.14, 3.14, AttrRep.parse("decimal"), False),
        (3.14, 3.141, AttrRep.parse("decimal"), True),
        (
            "YQ==",
            "YQ==",
            AttrRep.parse("binary"),
            False,
        ),
        (
            "YQ==",
            "Yg==",
            AttrRep.parse("binary"),
            True,
        ),
        (
            "https://www.example.com",
            "https://www.example.com",
            AttrRep.parse("external_ref"),
            False,
        ),
        (
            "https://www.example.com",
            "https://www.bad_example.com",
            AttrRep.parse("external_ref"),
            True,
        ),
        (
            "whatever/some/location/",
            "whatever/some/location/",
            AttrRep.parse("uri_ref"),
            False,
        ),
        (
            "whatever/some/location/",
            "whatever/some/other/location/",
            AttrRep.parse("uri_ref"),
            True,
        ),
        (
            "Users",
            "Users",
            AttrRep.parse("scim_ref"),
            False,
        ),
        (
            "Users",
            "Groups",
            AttrRep.parse("scim_ref"),
            True,
        ),
    ),
)
def test_not_equal_operator(value, operator_value, attribute_name, expected):
    operator = NotEqual(attribute_name, operator_value)

    actual = operator.match(value, SchemaForTests.attrs)

    assert actual == expected


@pytest.mark.parametrize(
    ("value", "operator_value", "attribute_name", "expected"),
    (
        (1, 1, AttrRep.parse("int"), False),
        (2, 1, AttrRep.parse("int"), True),
        ("a", "a", AttrRep.parse("str_cs"), False),
        ("a", "A", AttrRep.parse("str_cs"), True),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            AttrRep.parse("datetime"),
            False,
        ),
        (
            datetime(2023, 10, 10, 21, 27, 2).isoformat(),
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            AttrRep.parse("datetime"),
            True,
        ),
        (3.14, 3.14, AttrRep.parse("decimal"), False),
        (3.141, 3.14, AttrRep.parse("decimal"), True),
    ),
)
def test_greater_than_operator(value, operator_value, attribute_name, expected):
    operator = GreaterThan(attribute_name, operator_value)

    actual = operator.match(value, SchemaForTests.attrs)

    assert actual == expected


@pytest.mark.parametrize(
    ("value", "operator_value", "attribute_name", "expected"),
    (
        (1, 2, AttrRep.parse("int"), False),
        (1, 1, AttrRep.parse("int"), True),
        (2, 1, AttrRep.parse("int"), True),
        ("A", "a", AttrRep.parse("str_cs"), False),
        ("a", "a", AttrRep.parse("str_cs"), True),
        ("a", "A", AttrRep.parse("str_cs"), True),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 2).isoformat(),
            AttrRep.parse("datetime"),
            False,
        ),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            AttrRep.parse("datetime"),
            True,
        ),
        (
            datetime(2023, 10, 10, 21, 27, 2).isoformat(),
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            AttrRep.parse("datetime"),
            True,
        ),
        (3.14, 3.141, AttrRep.parse("decimal"), False),
        (3.14, 3.14, AttrRep.parse("decimal"), True),
        (3.141, 3.14, AttrRep.parse("decimal"), True),
    ),
)
def test_greater_than_or_equal_operator(value, operator_value, attribute_name, expected):
    operator = GreaterThanOrEqual(attribute_name, operator_value)

    actual = operator.match(value, SchemaForTests.attrs)

    assert actual == expected


@pytest.mark.parametrize(
    ("value", "operator_value", "attribute_name", "expected"),
    (
        (1, 1, AttrRep.parse("int"), False),
        (1, 2, AttrRep.parse("int"), True),
        ("a", "a", AttrRep.parse("str_cs"), False),
        ("A", "a", AttrRep.parse("str_cs"), True),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            AttrRep.parse("datetime"),
            False,
        ),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 2).isoformat(),
            AttrRep.parse("datetime"),
            True,
        ),
        (3.14, 3.14, AttrRep.parse("decimal"), False),
        (3.14, 3.141, AttrRep.parse("decimal"), True),
    ),
)
def test_lesser_than_operator(value, operator_value, attribute_name, expected):
    operator = LesserThan(attribute_name, operator_value)

    actual = operator.match(value, SchemaForTests.attrs)

    assert actual == expected


@pytest.mark.parametrize(
    ("value", "operator_value", "attribute_name", "expected"),
    (
        (1, 2, AttrRep.parse("int"), True),
        (1, 1, AttrRep.parse("int"), True),
        (2, 1, AttrRep.parse("int"), False),
        ("A", "a", AttrRep.parse("str_cs"), True),
        ("a", "a", AttrRep.parse("str_cs"), True),
        ("a", "A", AttrRep.parse("str_cs"), False),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 2).isoformat(),
            AttrRep.parse("datetime"),
            True,
        ),
        (
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            AttrRep.parse("datetime"),
            True,
        ),
        (
            datetime(2023, 10, 10, 21, 27, 2).isoformat(),
            datetime(2023, 10, 10, 21, 27, 1).isoformat(),
            AttrRep.parse("datetime"),
            False,
        ),
        (3.14, 3.141, AttrRep.parse("decimal"), True),
        (3.14, 3.14, AttrRep.parse("decimal"), True),
        (3.141, 3.14, AttrRep.parse("decimal"), False),
    ),
)
def test_lesser_than_or_equal_operator(value, operator_value, attribute_name, expected):
    operator = LesserThanOrEqual(attribute_name, operator_value)

    actual = operator.match(value, SchemaForTests.attrs)

    assert actual == expected


def test_binary_operator_does_not_match_if_non_matching_attribute_type():
    operator = Equal(AttrRep.parse("int"), "1")

    match = operator.match(1, SchemaForTests.attrs)

    assert not match


def test_binary_operator_does_not_match_if_attr_missing_in_schema():
    operator = Equal(AttrRep.parse("other_int"), 1)

    match = operator.match(1, SchemaForTests.attrs)

    assert not match


def test_binary_operator_does_not_match_if_not_supported_scim_type():
    operator = GreaterThan(AttrRep.parse("scim_ref"), chr(0))

    match = operator.match("Users", SchemaForTests.attrs)

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
    operator = operator_cls(AttrRep.parse("str"), "A")

    actual = operator.match("a", SchemaForTests.attrs)

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
    operator = Contains(AttrRep.parse("str_cs"), operator_value)

    actual = operator.match(value, SchemaForTests.attrs)

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
    operator = StartsWith(AttrRep.parse("str_cs"), operator_value)

    actual = operator.match(value, SchemaForTests.attrs)

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
    operator = EndsWith(AttrRep.parse("str_cs"), operator_value)

    actual = operator.match(value, SchemaForTests.attrs)

    assert actual == expected


def test_multi_value_attribute_is_matched_if_one_of_values_match():
    operator = Equal(AttrRep.parse("str_cs_mv"), "abc")

    match = operator.match(["b", "c", "ab", "abc", "ca"], SchemaForTests.attrs)

    assert match


def test_multi_value_attribute_is_matched_if_one_of_case_insensitive_values_match():
    operator = Equal(AttrRep.parse("str_mv"), "abc")

    match = operator.match(["b", "c", "ab", "ABc", "ca"], SchemaForTests.attrs)

    assert match


@pytest.mark.parametrize(
    ("value", "attribute_name", "expected"),
    (
        ("", AttrRep.parse("str"), False),
        ("abc", AttrRep.parse("str"), True),
        (None, AttrRep.parse("bool"), False),
        (False, AttrRep.parse("bool"), True),
        ([], AttrRep.parse("str_mv"), False),
        (
            ["a", "b", "c"],
            AttrRep.parse("str_mv"),
            True,
        ),
        (
            {
                "value": "",
            },
            AttrRep.parse("c"),
            False,
        ),
        (
            {
                "value": "abc",
            },
            AttrRep.parse("c"),
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
            AttrRep.parse("c_mv"),
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
            AttrRep.parse("c_mv"),
            True,
        ),
    ),
)
def test_present_operator(value, attribute_name, expected):
    operator = Present(attribute_name)

    actual = operator.match(value, SchemaForTests.attrs)

    assert actual == expected


def test_complex_attribute_matches_binary_operator_if_one_of_values_matches():
    operator = StartsWith(AttrRep.parse("c_mv"), "abc")

    match = operator.match(
        [{"value": "a"}, {"value": "bac"}, {"value": "abcd"}], SchemaForTests.attrs
    )

    assert match


def test_complex_attribute_does_not_match_binary_operator_if_not_any_of_values_matches():
    operator = StartsWith(AttrRep.parse("c_mv"), "abc")

    match = operator.match(
        [{"value": "a"}, {"value": "bac"}, {"value": "bcdd"}], SchemaForTests.attrs
    )

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
        Equal(AttrRep.parse("int"), 1),
        And(
            GreaterThan(AttrRep.parse("decimal"), 1.0),
            NotEqual(AttrRep.parse("str"), "1"),
        ),
        Or(
            Equal(AttrRep.parse("bool"), True),
            StartsWith(AttrRep.parse("str_cs"), "a"),
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
        SchemaForTests.attrs,
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
        Equal(AttrRep.parse("int"), 1),
        And(
            GreaterThan(AttrRep.parse("decimal"), 1.0),
            NotEqual(AttrRep.parse("str"), "1"),
        ),
        Or(
            Equal(AttrRep.parse("bool"), True),
            StartsWith(AttrRep.parse("str_cs"), "a"),
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
        SchemaForTests.attrs,
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
        SCIMDataContainer({"str": "admin", "int": 19, "bool": False}), SchemaForTests.attrs
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
        SCIMDataContainer({"str": "user", "int": 18, "bool": True}), SchemaForTests.attrs
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
        SchemaForTests.attrs,
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
        SchemaForTests.attrs,
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

    actual = operator.match(value, SchemaForTests.attrs)

    assert actual == expected


def test_binary_op_returns_missing_data_if_no_value_provided_with_strict():
    operator = Equal(AttrRep.parse("str"), "abc")

    match = operator.match(None, SchemaForTests.attrs, True)

    assert match.status == MatchStatus.MISSING_DATA


def test_binary_op_returns_matches_if_no_value_provided_without_strict():
    operator = Equal(AttrRep.parse("str"), "abc")

    match = operator.match(None, SchemaForTests.attrs, False)

    assert match


def test_complex_op_matches_if_sub_attr_value_not_provided_without_strict():
    operator = ComplexAttributeOperator(
        attr_rep=AttrRep(attr="c"),
        sub_operator=Equal(AttrRep(attr="str"), "abc"),
    )

    match = operator.match(SCIMDataContainer({}), SchemaForTests.attrs, False)

    assert match


def test_complex_op_does_not_matches_if_sub_attribute_not_provided_with_strict():
    operator = ComplexAttributeOperator(
        attr_rep=AttrRep(attr="c"),
        sub_operator=Equal(AttrRep(attr="str"), "abc"),
    )

    match = operator.match(SCIMDataContainer({}), SchemaForTests.attrs, True)

    assert not match


def test_or_op_returns_missing_data_if_no_sub_attr_matched_with_strict():
    operator = Or(
        Equal(AttrRep.parse("int"), 1),
        Equal(AttrRep.parse("str"), "abc"),
    )

    match = operator.match(SCIMDataContainer({"int": 2}), SchemaForTests.attrs, True)

    assert match.status == MatchStatus.MISSING_DATA


@pytest.mark.parametrize("strict", (True, False))
def test_or_op_matches_if_any_sub_attr_matched(strict):
    operator = Or(
        Equal(AttrRep.parse("int"), 1),
        Equal(AttrRep.parse("str"), "abc"),
    )

    match = operator.match(SCIMDataContainer({"int": 1}), SchemaForTests.attrs, strict)

    assert match


def test_and_op_returns_missing_data_if_any_sub_attr_is_without_data_with_strict():
    operator = And(
        Equal(AttrRep.parse("int"), 1),
        Equal(AttrRep.parse("str"), "abc"),
    )
    value = {"int": 1}  # value for this attr is correct, but missing 'str'

    match = operator.match(SCIMDataContainer(value), SchemaForTests.attrs, True)

    assert match.status == MatchStatus.MISSING_DATA


def test_and_op_does_not_match_if_any_sub_attr_does_not_match_with_strict():
    operator = And(
        Equal(AttrRep.parse("int"), 1),
        Equal(AttrRep.parse("str"), "abc"),
    )

    match = operator.match(SCIMDataContainer({"int": 1, "str": "cba"}), SchemaForTests.attrs, True)

    assert not match


def test_and_operator_matches_if_non_of_sub_attrs_fail_without_strict():
    operator = And(
        Equal(AttrRep.parse("int"), 1),
        Equal(
            AttrRep.parse("str"),
            "abc",
        ),
    )
    value = {"int": 1}  # value for this attr is correct, 'str' is missing, but no strict

    match = operator.match(SCIMDataContainer(value), SchemaForTests.attrs, False)

    assert match


def test_not_op_matches_for_missing_value_in_logical_sub_op_without_strict():
    operator = Not(
        Or(
            Equal(AttrRep.parse("int"), 1),
            Equal(AttrRep.parse("str"), "abc"),
        ),
    )

    match = operator.match(SCIMDataContainer({"int": 2}), SchemaForTests.attrs, False)

    assert match


def test_not_op_does_not_match_for_missing_value_in_logical_sub_op_with_strict():
    operator = Not(
        Or(
            Equal(AttrRep.parse("int"), 1),
            Equal(AttrRep.parse("str"), "abc"),
        ),
    )

    match = operator.match(SCIMDataContainer({"int": 2}), SchemaForTests.attrs, True)

    assert not match


def test_not_op_matches_for_missing_value_in_attr_sub_op_without_strict():
    operator = Not(Equal(AttrRep.parse("int"), 1))

    match = operator.match(SCIMDataContainer({}), SchemaForTests.attrs, False)

    assert match


def test_not_op_does_not_match_for_missing_value_in_attr_sub_op_with_strict():
    operator = Not(Equal(AttrRep.parse("int"), 1))

    match = operator.match(SCIMDataContainer({}), SchemaForTests.attrs, True)

    assert not match


def test_not_op_does_not_match_if_op_attr_not_in_attrs():
    operator = Not(Equal(AttrRep.parse("other_attr"), 1))

    match = operator.match(SCIMDataContainer({"other_attr": 2}), SchemaForTests.attrs)

    assert not match


@pytest.mark.parametrize("strict", (True, False))
def test_not_op_matches_if_no_data_for_pr_sub_op_with_strict(strict):
    operator = Not(Present(AttrRep.parse("int")))

    match = operator.match(SCIMDataContainer({}), SchemaForTests.attrs, strict)

    assert match


@pytest.mark.parametrize("strict", (True, False))
@pytest.mark.parametrize(("value", "expected"), ((1.0, True), (2.0, False)))
def test_binary_attributes_allows_to_compare_int_with_decimal(strict, value, expected):
    operator = Equal(AttrRep.parse("decimal"), 1)

    match = operator.match(value, SchemaForTests.attrs, strict)

    assert bool(match) is expected


@pytest.mark.parametrize("strict", (True, False))
@pytest.mark.parametrize(("value", "expected"), ((1, True), (2, False)))
def test_binary_attributes_allows_to_compare_decimal_with_int(strict, value, expected):
    operator = Equal(AttrRep.parse("int"), 1.0)

    match = operator.match(value, SchemaForTests.attrs, strict)

    assert bool(match) is expected


def test_complex_op_can_be_used_with_logical_op():
    operator = ComplexAttributeOperator(
        attr_rep=AttrRep(attr="c2"),
        sub_operator=And(Equal(AttrRep.parse("int"), 1), Equal(AttrRep.parse("str"), "abc")),
    )

    match = operator.match(SCIMDataContainer({"int": 1, "str": "abc"}), SchemaForTests.attrs)

    assert match


def test_complex_op_used_with_or_op_matches_if_at_least_one_sub_attr_matches():
    operator = ComplexAttributeOperator(
        attr_rep=AttrRep.parse("c2"),
        sub_operator=Or(Equal(AttrRep.parse("int"), 1), Equal(AttrRep.parse("str"), "abc")),
    )

    match = operator.match(SCIMDataContainer({"int": 1}), SchemaForTests.attrs)

    assert match


def test_complex_op_used_with_or_op_does_not_match_if_no_values_provided():
    operator = ComplexAttributeOperator(
        attr_rep=AttrRep.parse("c2"),
        sub_operator=Or(Equal(AttrRep.parse("int"), 1), Equal(AttrRep.parse("str"), "abc")),
    )

    match = operator.match(SCIMDataContainer({}), SchemaForTests.attrs)

    assert not match


def test_complex_op_used_with_or_op_matches_if_no_values_provided_without_strict():
    operator = ComplexAttributeOperator(
        attr_rep=AttrRep.parse("c2"),
        sub_operator=Or(Equal(AttrRep.parse("int"), 1), Equal(AttrRep.parse("str"), "abc")),
    )

    match = operator.match(SCIMDataContainer({}), SchemaForTests.attrs, False)

    assert match


def test_multivalued_complex_op_can_be_used_with_logical_op():
    operator = ComplexAttributeOperator(
        attr_rep=AttrRep.parse("c2_mv"),
        sub_operator=And(Equal(AttrRep.parse("int"), 1), Equal(AttrRep.parse("str"), "abc")),
    )

    match = operator.match(
        [
            SCIMDataContainer({"int": 2, "str": "abc"}),
            SCIMDataContainer({"int": 1, "str": "cba"}),
            SCIMDataContainer({"int": 1, "str": "abc"}),
        ],
        SchemaForTests.attrs,
    )

    assert match
