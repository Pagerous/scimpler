import pytest

from src.data import type as at
from src.data.attributes import Attribute, ComplexAttribute
from src.data.container import AttrRep, SCIMDataContainer


def test_validation_is_skipped_if_value_not_provided():
    attr = Attribute(name="some_attr", type_=at.String, required=True)

    issues = attr.validate(value=None)

    assert issues.to_dict(msg=True) == {}


def test_multi_valued_attribute_validation_fails_if_not_provided_list():
    attr = Attribute(name="some_attr", type_=at.String, multi_valued=True)

    issues = attr.validate("non-list")

    assert issues.to_dict() == {"_errors": [{"code": 2}]}


def test_multi_valued_attribute_validation_succeeds_if_provided_list_or_tuple():
    attr = Attribute(name="some_attr", type_=at.String, multi_valued=True)

    issues = attr.validate(["a", "b", "c"])

    assert issues.to_dict(msg=True) == {}


def test_multi_valued_attribute_values_are_validate_separately():
    attr = Attribute(name="some_attr", type_=at.String, multi_valued=True)

    issues = attr.validate(["a", 123])

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

    issues = attr.validate(SCIMDataContainer({"sub_attr_1": "123", "sub_attr_2": "123"}))

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
        value=[
            SCIMDataContainer({"sub_attr_1": 123, "sub_attr_2": "123"}),
            SCIMDataContainer({"sub_attr_1": 123, "sub_attr_2": 123}),
        ],
    )

    assert issues.to_dict() == expected_issues


@pytest.mark.parametrize(
    (
        "input_",
        "expected_schema",
        "expected_full_attr",
        "expected_attr",
        "expected_sub_attr",
    ),
    (
        ("userName", "", "userName", "userName", ""),
        ("name.firstName", "", "name", "name", "firstName"),
        (
            "urn:ietf:params:scim:schemas:core:2.0:User:userName",
            "urn:ietf:params:scim:schemas:core:2.0:User",
            "urn:ietf:params:scim:schemas:core:2.0:User:userName",
            "userName",
            "",
        ),
        (
            "urn:ietf:params:scim:schemas:core:2.0:User:name.firstName",
            "urn:ietf:params:scim:schemas:core:2.0:User",
            "urn:ietf:params:scim:schemas:core:2.0:User:name",
            "name",
            "firstName",
        ),
    ),
)
def test_attribute_identifier_is_parsed(
    input_, expected_schema, expected_full_attr, expected_attr, expected_sub_attr
):
    issues = AttrRep.validate(input_)
    assert issues.to_dict(msg=True) == {}

    attr_rep = AttrRep.parse(input_)
    assert attr_rep.schema == expected_schema
    assert attr_rep.attr_with_schema == expected_full_attr
    assert attr_rep.attr == expected_attr
    assert attr_rep.sub_attr == expected_sub_attr


@pytest.mark.parametrize(
    "input_",
    (
        "attr_1.sub_attr_1.sub_attr_2",
        "",
        "attr with spaces",
        'emails[type eq "work"]',
        "(attr_with_parenthesis)",
        "urn:ietf:params:scim:schemas:core:2.0:User:name.firstName.blahblah",
    ),
)
def test_attribute_identifier_is_not_parsed_when_bad_input(input_):
    issues = AttrRep.validate(input_)
    assert issues.to_dict() == {"_errors": [{"code": 111}]}

    with pytest.raises(ValueError):
        AttrRep.parse(input_)
