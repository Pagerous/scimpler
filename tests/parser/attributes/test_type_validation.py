import base64

from src.parser.attributes import type as at


def test_validate_invalid_string():
    expected_issues = {
        "_errors": [
            {
                "code": 2,
                "context": {
                    "scim_type": "string",
                    "expected_type": "str",
                    "provided_type": "int",
                },
            }
        ]
    }

    issues = at.String.validate(123)

    assert issues.to_dict(ctx=True) == expected_issues


def test_validate_valid_string():
    issues = at.String.validate("123")

    assert not issues


def test_validate_invalid_integer():
    expected_issues = {
        "_errors": [
            {
                "code": 2,
                "context": {
                    "scim_type": "integer",
                    "expected_type": "int",
                    "provided_type": "str",
                },
            }
        ]
    }

    issues = at.Integer.validate("123")

    assert issues.to_dict(ctx=True) == expected_issues


def test_validate_valid_integer():
    issues = at.Integer.validate(123)

    assert not issues


def test_validate_integer_float_without_floating_numbers_is_valid():
    issues = at.Integer.validate(1.0)

    assert not issues


def test_validate_integer_float_with_floating_numbers_is_invalid():
    expected_issues = {
        "_errors": [
            {
                "code": 2,
                "context": {
                    "scim_type": "integer",
                    "expected_type": "int",
                    "provided_type": "float",
                },
            }
        ]
    }

    issues = at.Integer.validate(1.2)

    assert issues.to_dict(ctx=True) == expected_issues


def test_validate_invalid_decimal():
    expected_issues = {
        "_errors": [
            {
                "code": 2,
                "context": {
                    "scim_type": "decimal",
                    "expected_type": "float",
                    "provided_type": "str",
                },
            }
        ]
    }

    issues = at.Decimal.validate("123")

    assert issues.to_dict(ctx=True) == expected_issues


def test_validate_valid_decimal():
    issues = at.Decimal.validate(1.2)

    assert not issues


def test_validate_integer_is_valid_decimal():
    issues = at.Decimal.validate(1)

    assert not issues


def test_validate_invalid_boolean():
    expected_issues = {
        "_errors": [
            {
                "code": 2,
                "context": {
                    "scim_type": "boolean",
                    "expected_type": "bool",
                    "provided_type": "str",
                },
            }
        ]
    }

    issues = at.Boolean.validate("Bad")

    assert issues.to_dict(ctx=True) == expected_issues


def test_validate_valid_boolean():
    issues = at.Boolean.validate(True)

    assert not issues


def test_validate_invalid_uri_reference():
    expected_issues = {
        "_errors": [
            {
                "code": 2,
                "context": {
                    "scim_type": "reference",
                    "expected_type": "str",
                    "provided_type": "int",
                },
            }
        ]
    }

    issues = at.URIReference.validate(123)

    assert issues.to_dict(ctx=True) == expected_issues


def test_validate_valid_uri_reference():
    issues = at.URIReference.validate("any:unique:resource:identifier")

    assert not issues


def test_validate_invalid_scim_reference():
    expected_issues = {
        "_errors": [
            {
                "code": 2,
                "context": {
                    "scim_type": "reference",
                    "expected_type": "str",
                    "provided_type": "int",
                },
            }
        ]
    }

    issues = at.SCIMReference.validate(123)

    assert issues.to_dict(ctx=True) == expected_issues


def test_validate_valid_scim_reference():
    issues = at.URIReference.validate("Users")

    assert not issues


def test_validate_invalid_external_reference_type():
    expected_issues = {
        "_errors": [
            {
                "code": 2,
                "context": {
                    "scim_type": "reference",
                    "expected_type": "str",
                    "provided_type": "int",
                },
            }
        ]
    }

    issues = at.ExternalReference.validate(123)

    assert issues.to_dict(ctx=True) == expected_issues


def test_validate_external_reference_invalid_absolute_url():
    expected_issues = {"_errors": [{"code": 8, "context": {"value": "/not/absolute/url"}}]}

    issues = at.ExternalReference.validate("/not/absolute/url")

    assert issues.to_dict(ctx=True) == expected_issues


def test_validate_external_reference_valid_absolute_url():
    issues = at.ExternalReference.validate("https://www.example.com/absolute/url")

    assert not issues


def test_validate_invalid_binary_type():
    expected_issues = {
        "_errors": [
            {
                "code": 2,
                "context": {
                    "scim_type": "binary",
                    "expected_type": "str",
                    "provided_type": "int",
                },
            }
        ]
    }

    issues = at.Binary.validate(123)

    assert issues.to_dict(ctx=True) == expected_issues


def test_validate_binary_invalid_encoding():
    expected_issues = {"_errors": [{"code": 3, "context": {"scim_type": "binary"}}]}

    issues = at.Binary.validate("blablabl")

    assert issues.to_dict(ctx=True) == expected_issues


def test_validate_binary_valid_encoding():
    issues = at.Binary.validate(base64.b64encode("blablabl".encode()).decode("utf-8"))

    assert not issues


def test_validate_invalid_datetime_type():
    expected_issues = {
        "_errors": [
            {
                "code": 2,
                "context": {
                    "scim_type": "dateTime",
                    "expected_type": "str",
                    "provided_type": "int",
                },
            }
        ]
    }

    issues = at.DateTime.validate(123)

    assert issues.to_dict(ctx=True) == expected_issues


def test_validate_invalid_datetime_format():
    expected_issues = {"_errors": [{"code": 4, "context": {"scim_type": "dateTime"}}]}

    issues = at.DateTime.validate("2022/05/05 12:34:56")

    assert issues.to_dict(ctx=True) == expected_issues


def test_validate_valid_datetime_format():
    issues = at.DateTime.validate("2022-05-05T12:34:56")

    assert not issues


def test_validate_invalid_complex_type():
    expected_issues = {
        "_errors": [
            {
                "code": 2,
                "context": {
                    "scim_type": "complex",
                    "expected_type": "dict",
                    "provided_type": "int",
                },
            }
        ]
    }

    issues = at.Complex.validate(123)

    assert issues.to_dict(ctx=True) == expected_issues


def test_validate_invalid_complex_sub_attribute_type():
    expected_issues = {
        "sub_attr_1": {
            "_errors": [
                {
                    "code": 5,
                    "context": {
                        "allowed_types": ["bool", "float", "int", "str"],
                        "provided_type": "dict",
                        "scim_type": "complex",
                    },
                }
            ]
        },
        "sub_attr_2": {
            "_errors": [
                {
                    "code": 5,
                    "context": {
                        "allowed_types": ["bool", "float", "int", "str"],
                        "provided_type": "list",
                        "scim_type": "complex",
                    },
                }
            ]
        },
    }

    issues = at.Complex.validate({"sub_attr_1": {}, "sub_attr_2": []})

    assert issues.to_dict(ctx=True) == expected_issues


def test_validate_valid_complex():
    issues = at.Complex.validate({"sub_attr_1": 1, "sub_attr_2": "2"})

    assert not issues
