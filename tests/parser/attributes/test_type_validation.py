import base64

from src.parser.attributes import type as at


def test_validate_invalid_string():
    errors = at.String.validate(123)

    assert errors[0].code == 2
    assert errors[0].context == {"scim_type": "string", "expected_type": "str", "provided_type": "int"}


def test_validate_valid_string():
    errors = at.String.validate("123")

    assert errors == []


def test_validate_invalid_integer():
    errors = at.Integer.validate("123")

    assert errors[0].code == 2
    assert errors[0].context == {"scim_type": "integer", "expected_type": "int", "provided_type": "str"}


def test_validate_valid_integer():
    errors = at.Integer.validate(123)

    assert errors == []


def test_validate_integer_float_without_floating_numbers_is_valid():
    errors = at.Integer.validate(1.0)

    assert errors == []


def test_validate_integer_float_with_floating_numbers_is_invalid():
    errors = at.Integer.validate(1.2)

    assert errors[0].code == 2
    assert errors[0].context == {"scim_type": "integer", "expected_type": "int", "provided_type": "float"}


def test_validate_invalid_decimal():
    errors = at.Decimal.validate("123")

    assert errors[0].code == 2
    assert errors[0].context == {"scim_type": "decimal", "expected_type": "float", "provided_type": "str"}


def test_validate_valid_decimal():
    errors = at.Decimal.validate(1.2)

    assert errors == []


def test_validate_integer_is_valid_decimal():
    errors = at.Decimal.validate(1)

    assert errors == []


def test_validate_invalid_boolean():
    errors = at.Boolean.validate("Bad")

    assert errors[0].code == 2
    assert errors[0].context == {"scim_type": "boolean", "expected_type": "bool", "provided_type": "str"}


def test_validate_valid_boolean():
    errors = at.Boolean.validate(True)

    assert errors == []


def test_validate_invalid_uri_reference():
    errors = at.URIReference.validate(123)

    assert errors[0].code == 2
    assert errors[0].context == {"scim_type": "reference", "expected_type": "str", "provided_type": "int"}


def test_validate_valid_uri_reference():
    errors = at.URIReference.validate("any:unique:resource:identifier")

    assert errors == []


def test_validate_invalid_scim_reference():
    errors = at.SCIMReference.validate(123)

    assert errors[0].code == 2
    assert errors[0].context == {"scim_type": "reference", "expected_type": "str", "provided_type": "int"}


def test_validate_valid_scim_reference():
    errors = at.URIReference.validate("Users")

    assert errors == []


def test_validate_invalid_external_reference_type():
    errors = at.ExternalReference.validate(123)

    assert errors[0].code == 2
    assert errors[0].context == {"scim_type": "reference", "expected_type": "str", "provided_type": "int"}


def test_validate_external_reference_invalid_absolute_url():
    errors = at.ExternalReference.validate("/not/absolute/url")

    assert errors[0].code == 8
    assert errors[0].context == {"value": "/not/absolute/url"}


def test_validate_external_reference_valid_absolute_url():
    errors = at.ExternalReference.validate("https://www.example.com/absolute/url")

    assert errors == []


def test_validate_invalid_binary_type():
    errors = at.Binary.validate(123)

    assert errors[0].code == 2
    assert errors[0].context == {"scim_type": "binary", "expected_type": "str", "provided_type": "int"}


def test_validate_binary_invalid_encoding():
    errors = at.Binary.validate("blablabl")

    assert errors[0].code == 3
    assert errors[0].context == {"scim_type": "binary"}


def test_validate_binary_valid_encoding():
    errors = at.Binary.validate(base64.b64encode("blablabl".encode()).decode("utf-8"))

    assert errors == []


def test_validate_invalid_datetime_type():
    errors = at.DateTime.validate(123)

    assert errors[0].code == 2
    assert errors[0].context == {"scim_type": "dateTime", "expected_type": "str", "provided_type": "int"}


def test_validate_invalid_datetime_format():
    errors = at.DateTime.validate("2022/05/05 12:34:56")

    assert errors[0].code == 4
    assert errors[0].context == {"scim_type": "dateTime"}


def test_validate_valid_datetime_format():
    errors = at.DateTime.validate("2022-05-05T12:34:56")

    assert errors == []


def test_validate_invalid_complex_type():
    errors = at.Complex.validate(123)

    assert errors[0].code == 2
    assert errors[0].context == {"scim_type": "complex", "expected_type": "dict", "provided_type": "int"}


def test_validate_invalid_complex_sub_attribute_type():
    errors = at.Complex.validate({"sub_attr_1": {}, "sub_attr_2": []})

    assert errors[0].code == 5
    assert errors[1].code == 5


def test_validate_valid_complex():
    errors = at.Complex.validate({"sub_attr_1": 1, "sub_attr_2": "2"})

    assert errors == []
