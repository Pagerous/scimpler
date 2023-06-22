from src.parser.attributes.attributes import Attribute, AttributeIssuer, ComplexAttribute
from src.parser.attributes import type as at


def test_validates_required_attribute():
    attr = Attribute(name="some_attr", type_=at.String, required=True)

    errors = attr.validate(
        value=None,
        http_method="POST",
        direction="REQUEST",
    )

    assert errors[0].code == 1
    assert errors[0].context == {"attr_name": "some_attr"}


def test_passing_no_value_for_required_attribute_succeeds_if_post_request_and_service_provider_issuer():
    attr = Attribute(name="some_attr", issuer=AttributeIssuer.SERVICE_PROVIDER, type_=at.String, required=True)

    errors = attr.validate(
        value=None,
        http_method="POST",
        direction="REQUEST",
    )

    assert errors == []


def test_multi_valued_attribute_validation_fails_if_not_provided_list_or_tuple():
    attr = Attribute(name="some_attr", type_=at.String, multi_valued=True)

    errors = attr.validate(
        value="non-list",
        http_method="POST",
        direction="REQUEST",
    )

    assert errors[0].code == 6


def test_multi_valued_attribute_validation_succeeds_if_provided_list_or_tuple():
    attr = Attribute(name="some_attr", type_=at.String, multi_valued=True)

    errors = attr.validate(
        value=["a", "b", "c"],
        http_method="POST",
        direction="REQUEST",
    )

    assert errors == []


def test_multi_valued_attribute_values_are_validated_separately():
    attr = Attribute(name="some_attr", type_=at.String, multi_valued=True)

    errors = attr.validate(
        value=["a", 123],
        http_method="POST",
        direction="REQUEST",
    )

    assert errors[0].code == 2
    assert errors[0].location == "some_attr.1"


def test_complex_attribute_sub_attributes_are_validated_separately():
    attr = ComplexAttribute(
        sub_attributes=[
            Attribute(name="sub_attr_1", type_=at.String, required=True),
            Attribute(name="sub_attr_2", type_=at.Integer),
        ],
        name="complex_attr",
        issuer=AttributeIssuer.BOTH,
    )

    errors = attr.validate(value={"sub_attr_2": "123"}, http_method="POST", direction="REQUEST")

    assert errors[0].code == 1
    assert errors[0].location == "complex_attr.sub_attr_1"
    assert errors[1].code == 2
    assert errors[1].location == "complex_attr.sub_attr_2"


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

    errors = attr.validate(
        value=[{"sub_attr_2": "123"}, {"sub_attr_1": 123, "sub_attr_2": 123}],
        http_method="POST",
        direction="REQUEST",
    )

    assert len(errors) == 3
    assert errors[0].code == 1
    assert errors[0].location == "complex_attr.0.sub_attr_1"
    assert errors[1].code == 2
    assert errors[1].location == "complex_attr.0.sub_attr_2"
    assert errors[2].code == 2
    assert errors[2].location == "complex_attr.1.sub_attr_1"
