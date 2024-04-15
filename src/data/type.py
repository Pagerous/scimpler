import abc
import base64
import binascii
import typing as t
from datetime import datetime
from urllib.parse import urlparse

from ..error import ValidationError, ValidationIssues
from .container import SCIMDataContainer


class AttributeType(abc.ABC):
    SCIM_NAME: str
    TYPE: t.Type

    @classmethod
    def validate(cls, value: t.Any) -> ValidationIssues:
        issues = ValidationIssues()
        if not isinstance(value, cls.TYPE):
            issues.add_error(
                issue=ValidationError.bad_type(
                    expected=get_scim_type(cls.TYPE), provided=get_scim_type(type(value))
                ),
                proceed=False,
            )
        return issues


class Unknown(AttributeType):
    """
    Not a standard SCIM type. To be used by variadic attributes.
    """

    _T = t.TypeVar("_T")

    @classmethod
    def validate(cls, value: t.Any) -> ValidationIssues:
        return ValidationIssues()


class Boolean(AttributeType):
    SCIM_NAME = "boolean"
    TYPE = bool


class Decimal(AttributeType):
    SCIM_NAME = "decimal"
    TYPE = float

    @classmethod
    def validate(cls, value: t.Any) -> ValidationIssues:
        issues = ValidationIssues()
        if not isinstance(value, (cls.TYPE, int)):
            issues.add_error(
                issue=ValidationError.bad_type(
                    expected=get_scim_type(cls.TYPE), provided=get_scim_type(type(value))
                ),
                proceed=False,
            )
        return issues


class Integer(AttributeType):
    SCIM_NAME = "integer"
    TYPE = int


class String(AttributeType):
    SCIM_NAME = "string"
    TYPE = str


class Binary(String):
    SCIM_NAME = "binary"
    TYPE = str

    @classmethod
    def validate(cls, value: t.Any) -> ValidationIssues:
        issues = super().validate(value)
        if not issues.can_proceed():
            return issues
        cls._validate_encoding(value, issues)
        if not issues.can_proceed():
            return issues
        return issues

    @classmethod
    def _validate_encoding(cls, value: t.Any, issues: ValidationIssues) -> ValidationIssues:
        try:
            value = bytes(value, "ascii")
            if base64.b64encode(base64.b64decode(value)) != value:
                issues.add_error(
                    issue=ValidationError.base_64_encoding_required(cls.SCIM_NAME),
                    proceed=False,
                )
        except binascii.Error:
            issues.add_error(
                issue=ValidationError.base_64_encoding_required(cls.SCIM_NAME),
                proceed=False,
            )
        return issues


class ExternalReference(String):
    SCIM_NAME = "reference"
    TYPE = str

    @classmethod
    def validate(cls, value: t.Any) -> ValidationIssues:
        issues = super().validate(value)
        if issues.can_proceed():
            issues_ = validate_absolute_url(value)
            issues.merge(issues=issues_)
        if issues.can_proceed():
            return issues
        return issues


class URIReference(String):
    SCIM_NAME = "reference"
    TYPE = str


class SCIMReference(String):
    SCIM_NAME = "reference"
    TYPE = str


class DateTime(String):
    SCIM_NAME = "dateTime"
    TYPE = str

    @classmethod
    def validate(cls, value: t.Any) -> ValidationIssues:
        issues = super().validate(value)
        if not issues.can_proceed():
            return issues
        value = cls._parse_xsd_datetime(value)
        if value is None:
            issues.add_error(
                issue=ValidationError.bad_value_syntax(),
                proceed=False,
            )
            return issues
        return issues

    @staticmethod
    def _parse_xsd_datetime(value: str) -> t.Optional[datetime]:
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None


class Complex(AttributeType):
    SCIM_NAME = "complex"
    TYPE = SCIMDataContainer


_TYPE_TO_SCIM_TYPE: t.Dict[t.Type, str] = {
    bool: Boolean.SCIM_NAME,
    int: Integer.SCIM_NAME,
    float: Decimal.SCIM_NAME,
    str: String.SCIM_NAME,
    SCIMDataContainer: Complex.SCIM_NAME,
    list: "list",
}


def get_scim_type(type_: t.Type) -> str:
    return _TYPE_TO_SCIM_TYPE.get(type_, "unknown")


def validate_absolute_url(value: str) -> ValidationIssues:
    issues = ValidationIssues()
    try:
        result = urlparse(value)
        is_valid = all([result.scheme, result.netloc])
        if not is_valid:
            issues.add_error(
                issue=ValidationError.bad_url(value),
                proceed=False,
            )
            return issues
    except ValueError:
        issues.add_error(
            issue=ValidationError.bad_url(value),
            proceed=False,
        )
        return issues
    return issues
