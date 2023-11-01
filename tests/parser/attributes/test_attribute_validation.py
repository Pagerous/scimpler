from src.parser.attributes import type as at
from src.parser.attributes.attributes import (
    Attribute,
    AttributeReturn,
    ComplexAttribute,
)


def test_validation_is_skipped_if_value_not_provided():
    attr = Attribute(name="some_attr", type_=at.String, required=True)

    issues = attr.validate(
        value=None,
    )

    assert issues.to_dict() == {}


def test_multi_valued_attribute_validation_fails_if_not_provided_list_or_tuple():
    attr = Attribute(name="some_attr", type_=at.String, multi_valued=True)

    issues = attr.validate(
        value="non-list",
    )

    assert issues.to_dict() == {"_errors": [{"code": 6}]}


def test_multi_valued_attribute_validation_succeeds_if_provided_list_or_tuple():
    attr = Attribute(name="some_attr", type_=at.String, multi_valued=True)

    issues = attr.validate(
        value=["a", "b", "c"],
    )

    assert not issues


def test_multi_valued_attribute_values_are_validated_separately():
    attr = Attribute(name="some_attr", type_=at.String, multi_valued=True)

    issues = attr.validate(
        value=["a", 123],
    )

    assert issues.to_dict() == {"1": {"_errors": [{"code": 2}]}}


def test_complex_attribute_sub_attributes_are_validated_separately():
    attr = ComplexAttribute(
        sub_attributes=[
            Attribute(name="sub_attr_1", type_=at.Integer, required=True),
            Attribute(name="sub_attr_2", type_=at.Integer),
        ],
        name="complex_attr",
    )
    expected_issues = {
        "sub_attr_1": {
            "_errors": [
                {
                    "code": 2,
                }
            ]
        },
        "sub_attr_2": {
            "_errors": [
                {
                    "code": 2,
                }
            ]
        },
    }

    issues = attr.validate(value={"sub_attr_1": "123", "sub_attr_2": "123"})

    assert issues.to_dict() == expected_issues


def test_multivalued_complex_attribute_sub_attributes_are_validated_separately():
    attr = ComplexAttribute(
        sub_attributes=[
            Attribute(name="sub_attr_1", type_=at.String, required=True),
            Attribute(name="sub_attr_2", type_=at.Integer),
        ],
        multi_valued=True,
        name="complex_attr",
    )
    expected_issues = {
        "0": {
            "sub_attr_1": {
                "_errors": [
                    {
                        "code": 2,
                    }
                ]
            },
            "sub_attr_2": {
                "_errors": [
                    {
                        "code": 2,
                    }
                ]
            },
        },
        "1": {
            "sub_attr_1": {
                "_errors": [
                    {
                        "code": 2,
                    }
                ]
            },
        },
    }

    issues = attr.validate(
        value=[{"sub_attr_1": 123, "sub_attr_2": "123"}, {"sub_attr_1": 123, "sub_attr_2": 123}],
    )

    assert issues.to_dict() == expected_issues


def test_providing_no_value_for_required_attribute_if_should_not_be_returned_succeeds():
    attr = Attribute(
        name="some_attr",
        type_=at.String,
        required=True,
        returned=AttributeReturn.NEVER,
    )

    issues = attr.validate(
        value=None,
    )

    assert not issues
