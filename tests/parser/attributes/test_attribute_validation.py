from src.parser.attributes.attributes import (
    Attribute,
    AttributeIssuer,
    AttributeReturn,
    ComplexAttribute
)
from src.parser.attributes import type as at


def test_validates_required_attribute():
    attr = Attribute(name="some_attr", type_=at.String, required=True)

    issues = attr.validate(
        value=None,
        direction="REQUEST",
    )

    assert issues.to_dict() == {"_errors": [{"code": 1}]}


def test_passing_no_value_for_required_attribute_succeeds_if_request_and_service_provider_issuer():
    attr = Attribute(
        name="some_attr",
        issuer=AttributeIssuer.SERVICE_PROVIDER,
        type_=at.String,
        required=True,
    )

    issues = attr.validate(
        value=None,
        direction="REQUEST",
    )

    assert not issues


def test_multi_valued_attribute_validation_fails_if_not_provided_list_or_tuple():
    attr = Attribute(name="some_attr", type_=at.String, multi_valued=True)

    issues = attr.validate(
        value="non-list",
        direction="REQUEST",
    )

    assert issues.to_dict() == {"_errors": [{"code": 6}]}


def test_multi_valued_attribute_validation_succeeds_if_provided_list_or_tuple():
    attr = Attribute(name="some_attr", type_=at.String, multi_valued=True)

    issues = attr.validate(
        value=["a", "b", "c"],
        direction="REQUEST",
    )

    assert not issues


def test_multi_valued_attribute_values_are_validated_separately():
    attr = Attribute(name="some_attr", type_=at.String, multi_valued=True)

    issues = attr.validate(
        value=["a", 123],
        direction="REQUEST",
    )

    assert issues.to_dict() == {"1": {"_errors": [{"code": 2}]}}


def test_complex_attribute_sub_attributes_are_validated_separately():
    attr = ComplexAttribute(
        sub_attributes=[
            Attribute(name="sub_attr_1", type_=at.String, required=True),
            Attribute(name="sub_attr_2", type_=at.Integer),
        ],
        name="complex_attr",
        issuer=AttributeIssuer.BOTH,
    )
    expected_issues = {
        "sub_attr_1": {
            "_errors": [
                {
                    "code": 1,
                }
            ]
        },
        "sub_attr_2": {
            "_errors": [
                {
                    "code": 2,
                }
            ]
        }
    }

    issues = attr.validate(value={"sub_attr_2": "123"}, direction="REQUEST")

    assert issues.to_dict() == expected_issues


def test_multivalued_complex_attribute_sub_attributes_are_validated_separately():
    attr = ComplexAttribute(
        sub_attributes=[
            Attribute(name="sub_attr_1", type_=at.String, required=True),
            Attribute(name="sub_attr_2", type_=at.Integer),
        ],
        multi_valued=True,
        name="complex_attr",
        issuer=AttributeIssuer.BOTH,
    )
    expected_issues = {
        "0": {
            "sub_attr_1": {
                "_errors": [
                    {
                        "code": 1,
                    }
                ]
            },
            "sub_attr_2": {
                "_errors": [
                    {
                        "code": 2,
                    }
                ]
            }
        },
        "1": {
            "sub_attr_1": {
                "_errors": [
                    {
                        "code": 2,
                    }
                ]
            },
        }
    }

    issues = attr.validate(
        value=[{"sub_attr_2": "123"}, {"sub_attr_1": 123, "sub_attr_2": 123}],
        direction="REQUEST",
    )

    assert issues.to_dict() == expected_issues


def test_returning_attribute_that_should_never_be_returned_fails():
    attr = Attribute(name="some_attr", type_=at.String, returned=AttributeReturn.NEVER)

    issues = attr.validate(
        value="value",
        direction="RESPONSE",
    )

    assert issues.to_dict() == {"_errors": [{"code": 19}]}


def test_providing_no_value_for_required_attribute_if_should_not_be_returned_succeeds():
    attr = Attribute(
        name="some_attr",
        type_=at.String,
        required=True,
        returned=AttributeReturn.NEVER,
    )

    issues = attr.validate(
        value=None,
        direction="RESPONSE",
    )

    assert not issues
