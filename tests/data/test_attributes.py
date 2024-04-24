import base64

import pytest

from src.assets.schemas import User  # noqa; schema must be registered
from src.data.attributes import (
    Binary,
    Boolean,
    Complex,
    DateTime,
    Decimal,
    ExternalReference,
    Integer,
    SCIMReference,
    String,
    URIReference,
)
from src.data.container import BoundedAttrRep, SCIMDataContainer


def test_validation_is_skipped_if_value_not_provided():
    attr = String(name="some_attr", required=True)

    issues = attr.validate(value=None)

    assert issues.to_dict(msg=True) == {}


def test_multi_valued_attribute_validation_fails_if_not_provided_list():
    attr = String(name="some_attr", multi_valued=True)

    issues = attr.validate("non-list")

    assert issues.to_dict() == {"_errors": [{"code": 2}]}


def test_multi_valued_attribute_validation_succeeds_if_provided_list_or_tuple():
    attr = String(name="some_attr", multi_valued=True)

    issues = attr.validate(["a", "b", "c"])

    assert issues.to_dict(msg=True) == {}


def test_multi_valued_attribute_values_are_validate_separately():
    attr = String(name="some_attr", multi_valued=True)

    issues = attr.validate(["a", 123])

    assert issues.to_dict() == {"1": {"_errors": [{"code": 2}]}}


def test_complex_attribute_sub_attributes_are_validated_separately():
    attr = Complex(
        sub_attributes=[
            Integer(name="sub_attr_1", required=True),
            Integer(name="sub_attr_2"),
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
    attr = Complex(
        sub_attributes=[
            String("sub_attr_1", required=True),
            Integer("sub_attr_2"),
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
        "expected_attr_with_schema",
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
        ("weirdo-$", "", "weirdo-$", "weirdo-$", ""),
        ("attr.weirdo-$", "", "attr", "attr", "weirdo-$"),
    ),
)
def test_attribute_identifier_is_deserialized(
    input_, expected_schema, expected_attr_with_schema, expected_attr, expected_sub_attr
):
    issues = BoundedAttrRep.validate(input_)
    assert issues.to_dict(msg=True) == {}

    attr_rep = BoundedAttrRep.deserialize(input_)
    assert attr_rep.schema == expected_schema
    assert attr_rep.attr_with_schema == expected_attr_with_schema
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
def test_attribute_identifier_is_not_deserialized_when_bad_input(input_):
    issues = BoundedAttrRep.validate(input_)
    assert issues.to_dict() == {"_errors": [{"code": 111}]}

    with pytest.raises(ValueError):
        BoundedAttrRep.deserialize(input_)


def test_validation_fails_in_not_one_of_canonical_values():
    attr = String(
        name="attr",
        canonical_values=["A", "B", "C"],
        restrict_canonical_values=True,
    )
    expected_issues = {"_errors": [{"code": 14}]}

    assert attr.validate("D").to_dict() == expected_issues


def test_validation_fails_in_not_one_of_canonical_values__multivalued():
    attr = String(
        name="attr",
        canonical_values=["A", "B", "C"],
        restrict_canonical_values=True,
        multi_valued=True,
    )
    expected_issues = {"1": {"_errors": [{"code": 14}]}}

    assert attr.validate(["A", "D", "C"]).to_dict() == expected_issues


def test_validation_returns_warning_in_not_one_of_canonical_values():
    attr = String(
        name="attr",
        canonical_values=["A", "B", "C"],
        restrict_canonical_values=False,
    )
    expected_issues = {"_warnings": [{"code": 1}]}

    assert attr.validate("D").to_dict() == expected_issues


def test_validation_returns_warning_in_not_one_of_canonical_values__multivalued():
    attr = String(
        name="attr",
        canonical_values=["A", "B", "C"],
        restrict_canonical_values=False,
        multi_valued=True,
    )
    expected_issues = {"1": {"_warnings": [{"code": 1}]}}

    assert attr.validate(["A", "D", "C"]).to_dict() == expected_issues


@pytest.mark.parametrize(
    ("input_value", "attr", "expected_issues"),
    (
        (
            1.0,
            Integer("int"),
            {
                "_errors": [
                    {
                        "code": 2,
                        "context": {
                            "expected": "integer",
                            "provided": "decimal",
                        },
                    }
                ]
            },
        ),
        (
            123,
            String("str"),
            {
                "_errors": [
                    {
                        "code": 2,
                        "context": {
                            "expected": "string",
                            "provided": "integer",
                        },
                    }
                ]
            },
        ),
        (
            "123",
            Integer("int"),
            {
                "_errors": [
                    {
                        "code": 2,
                        "context": {
                            "expected": "integer",
                            "provided": "string",
                        },
                    }
                ]
            },
        ),
        (
            1.2,
            Integer("int"),
            {
                "_errors": [
                    {
                        "code": 2,
                        "context": {
                            "expected": "integer",
                            "provided": "decimal",
                        },
                    }
                ]
            },
        ),
        (
            "123",
            Decimal("decimal"),
            {
                "_errors": [
                    {
                        "code": 2,
                        "context": {
                            "expected": "decimal",
                            "provided": "string",
                        },
                    }
                ]
            },
        ),
        (
            "Bad",
            Boolean("bool"),
            {
                "_errors": [
                    {
                        "code": 2,
                        "context": {
                            "expected": "boolean",
                            "provided": "string",
                        },
                    }
                ]
            },
        ),
        (
            123,
            URIReference("uri"),
            {
                "_errors": [
                    {
                        "code": 2,
                        "context": {
                            "expected": "string",
                            "provided": "integer",
                        },
                    }
                ]
            },
        ),
        (
            123,
            SCIMReference("scim", reference_types=["Users"]),
            {
                "_errors": [
                    {
                        "code": 2,
                        "context": {
                            "expected": "string",
                            "provided": "integer",
                        },
                    }
                ]
            },
        ),
        (
            "/Groups/123",
            SCIMReference("scim", reference_types=["User"]),
            {
                "_errors": [
                    {
                        "code": 40,
                        "context": {
                            "allowed_resources": ["User"],
                        },
                    }
                ]
            },
        ),
        (
            123,
            ExternalReference("external"),
            {
                "_errors": [
                    {
                        "code": 2,
                        "context": {
                            "expected": "string",
                            "provided": "integer",
                        },
                    }
                ]
            },
        ),
        (
            "/not/absolute/url",
            ExternalReference("external"),
            {"_errors": [{"code": 8, "context": {"value": "/not/absolute/url"}}]},
        ),
        (
            123,
            Binary("binary"),
            {
                "_errors": [
                    {
                        "code": 2,
                        "context": {
                            "expected": "string",
                            "provided": "integer",
                        },
                    }
                ]
            },
        ),
        ("bad", Binary("binary"), {"_errors": [{"code": 3, "context": {"scim_type": "binary"}}]}),
        (
            123,
            DateTime("datetime"),
            {
                "_errors": [
                    {
                        "code": 2,
                        "context": {
                            "expected": "string",
                            "provided": "integer",
                        },
                    }
                ]
            },
        ),
        (
            "2022/05/05 12:34:56",
            DateTime("datetime"),
            {"_errors": [{"code": 1, "context": {}}]},
        ),
        (
            123,
            Complex("complex", sub_attributes=[]),
            {
                "_errors": [
                    {
                        "code": 2,
                        "context": {
                            "expected": "complex",
                            "provided": "integer",
                        },
                    }
                ]
            },
        ),
    ),
)
def test_validate_bad_type(input_value, attr, expected_issues):
    issues = attr.validate(input_value)

    assert issues.to_dict(ctx=True) == expected_issues


@pytest.mark.parametrize(
    ("input_value", "attr"),
    (
        (
            "123",
            String("str"),
        ),
        (
            123,
            Integer("int"),
        ),
        (
            1,
            Decimal("decimal"),
        ),
        (
            1.2,
            Decimal("decimal"),
        ),
        (
            True,
            Boolean("bool"),
        ),
        (
            "any:unique:resource:identifier",
            URIReference("uri"),
        ),
        (
            "/Users/123",
            SCIMReference("scim", reference_types=["User"]),
        ),
        (
            "https://www.example.com/absolute/url",
            ExternalReference("external"),
        ),
        (
            base64.b64encode("blahblah".encode()).decode("utf-8"),
            Binary("binary"),
        ),
        (
            "2024-01-06T00:00:00",
            DateTime("datetime"),
        ),
        (
            SCIMDataContainer({"sub_attr_1": 1, "sub_attr_2": "2"}),
            Complex("complex", sub_attributes=[]),
        ),
    ),
)
def test_validate_correct_type(input_value, attr):
    issues = attr.validate(input_value)

    assert issues.to_dict(msg=True) == {}


def test_complex_mv_attr_fails_if_multiple_primary_items():
    attr = Complex("complex", multi_valued=True)
    expected_issues = {"_errors": [{"code": 9}]}

    issues = attr.validate(
        [
            SCIMDataContainer({"value": 1, "primary": True}),
            SCIMDataContainer({"value": "abc", "primary": True}),
        ]
    )

    assert issues.to_dict() == expected_issues


def test_warning_is_returned_if_multiple_type_value_pairs():
    attr = Complex("complex", multi_valued=True)
    expected_issues = {"_warnings": [{"code": 2}]}

    issues = attr.validate(
        [
            SCIMDataContainer({"value": 1, "type": "work"}),
            SCIMDataContainer({"value": 1, "type": "work"}),
        ]
    )

    assert issues.to_dict() == expected_issues


def test_invalid_items_dont_count_in_type_value_pairs():
    attr = Complex("complex", multi_valued=True)
    expected_issues = {"0": {"_errors": [{"code": 2}]}}

    issues = attr.validate(
        [
            {"value": 1, "type": "work"},
            SCIMDataContainer({"value": 1, "type": "work"}),
        ]
    )

    assert issues.to_dict() == expected_issues
