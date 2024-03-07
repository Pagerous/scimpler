import abc
import base64
import binascii
import typing as t
from datetime import datetime
from urllib.parse import urlparse

from ..error import ValidationError, ValidationIssues
from .container import Invalid, SCIMDataContainer


class AttributeType(abc.ABC):
    PARSE_TYPE: t.Type
    DUMP_TYPE: t.Type

    SCIM_NAME: str
    COMPATIBLE_TYPES: t.Set[t.Type] = set()

    @classmethod
    def parse(cls, value: t.Any) -> t.Tuple[t.Any, ValidationIssues]:
        issues = ValidationIssues()
        if not isinstance(value, cls.PARSE_TYPE):
            issues.add(
                issue=ValidationError.bad_type(
                    expected=get_scim_type(cls.PARSE_TYPE), provided=get_scim_type(type(value))
                ),
                proceed=False,
            )
            value = Invalid
        return value, issues

    @classmethod
    def dump(cls, value: t.Any) -> t.Tuple[t.Any, ValidationIssues]:
        issues = ValidationIssues()
        if not isinstance(value, cls.DUMP_TYPE):
            issues.add(
                issue=ValidationError.bad_type(
                    expected=get_scim_type(cls.DUMP_TYPE), provided=get_scim_type(type(value))
                ),
                proceed=False,
            )
            value = Invalid
        return value, issues


class Unknown(AttributeType):
    """
    Not a standard SCIM type. To be used by variadic attributes.
    """

    _T = t.TypeVar("_T")

    @classmethod
    def parse(cls, value: _T) -> t.Tuple[_T, ValidationIssues]:
        return value, ValidationIssues()

    @classmethod
    def dump(cls, value: _T) -> t.Tuple[_T, ValidationIssues]:
        return value, ValidationIssues()


class Boolean(AttributeType):
    SCIM_NAME = "boolean"
    PARSE_TYPE = bool
    DUMP_TYPE = bool


class Decimal(AttributeType):
    SCIM_NAME = "decimal"
    PARSE_TYPE = float
    DUMP_TYPE = float
    COMPATIBLE_TYPES = {int}

    @classmethod
    def parse(cls, value: t.Any) -> t.Tuple[t.Optional[float], ValidationIssues]:
        if isinstance(value, int):
            value, issues = Integer.parse(value)
            if value is not Invalid:
                value = float(value)
            return value, issues
        return super().parse(value)

    @classmethod
    def dump(cls, value: t.Any) -> t.Tuple[t.Optional[float], ValidationIssues]:
        if isinstance(value, int):
            value, issues = Integer.dump(value)
            if value is not Invalid:
                value = float(value)
            return value, issues
        return super().dump(value)


class Integer(AttributeType):
    SCIM_NAME = "integer"
    PARSE_TYPE = int
    DUMP_TYPE = int
    COMPATIBLE_TYPES = {float}

    @classmethod
    def parse(cls, value: t.Any) -> t.Tuple[t.Optional[int], ValidationIssues]:
        if isinstance(value, float) and int(value) == value:
            return int(value), ValidationIssues()
        return super().parse(value)

    @classmethod
    def dump(cls, value: t.Any) -> t.Tuple[t.Optional[int], ValidationIssues]:
        if isinstance(value, float) and int(value) == value:
            return int(value), ValidationIssues()
        return super().dump(value)


class String(AttributeType):
    SCIM_NAME = "string"
    PARSE_TYPE = str
    DUMP_TYPE = str


class Binary(String):
    SCIM_NAME = "binary"
    PARSE_TYPE = str
    DUMP_TYPE = str

    @classmethod
    def parse(cls, value: t.Any) -> t.Tuple[t.Optional[str], ValidationIssues]:
        value, issues = super().parse(value)
        if not issues.can_proceed():
            return Invalid, issues
        cls._validate_encoding(value, issues)
        if not issues.can_proceed():
            return Invalid, issues
        return value, issues

    @classmethod
    def dump(cls, value: t.Any) -> t.Tuple[t.Optional[str], ValidationIssues]:
        value, issues = super().dump(value)
        if not issues.can_proceed():
            return Invalid, issues
        cls._validate_encoding(value, issues)
        if not issues.can_proceed():
            return Invalid, issues
        return value, issues

    @classmethod
    def _validate_encoding(cls, value: t.Any, issues: ValidationIssues) -> ValidationIssues:
        try:
            value = bytes(value, "ascii")
            if base64.b64encode(base64.b64decode(value)) != value:
                issues.add(
                    issue=ValidationError.base_64_encoding_required(cls.SCIM_NAME),
                    proceed=False,
                )
        except binascii.Error:
            issues.add(
                issue=ValidationError.base_64_encoding_required(cls.SCIM_NAME),
                proceed=False,
            )
        return issues


class ExternalReference(String):
    SCIM_NAME = "reference"
    PARSE_TYPE = str
    DUMP_TYPE = str

    @classmethod
    def parse(cls, value: t.Any) -> t.Tuple[t.Optional[str], ValidationIssues]:
        value, issues = super().parse(value)
        if issues.can_proceed():
            issues_ = validate_absolute_url(value)
            issues.merge(issues=issues_)
        if issues.can_proceed():
            return value, issues
        return Invalid, issues

    @classmethod
    def dump(cls, value: t.Any) -> t.Tuple[t.Optional[str], ValidationIssues]:
        value, issues = super().dump(value)
        if issues.can_proceed():
            issues_ = validate_absolute_url(value)
            issues.merge(issues=issues_)
        if issues.can_proceed():
            return value, issues
        return Invalid, issues


class URIReference(String):
    SCIM_NAME = "reference"
    PARSE_TYPE = str
    DUMP_TYPE = str


class SCIMReference(String):
    SCIM_NAME = "reference"
    PARSE_TYPE = str
    DUMP_TYPE = str


class DateTime(String):
    SCIM_NAME = "dateTime"
    PARSE_TYPE = str
    DUMP_TYPE = datetime

    @classmethod
    def parse(cls, value: t.Any) -> t.Tuple[t.Optional[datetime], ValidationIssues]:
        value, issues = super().parse(value)
        if not issues.can_proceed():
            return Invalid, issues
        value = cls._parse_xsd_datetime(value)
        if value is None:
            issues.add(
                issue=ValidationError.xsd_datetime_format_required(cls.SCIM_NAME),
                proceed=False,
            )
            return Invalid, issues
        return value, issues

    @classmethod
    def dump(cls, value: t.Any) -> t.Tuple[t.Optional[str], ValidationIssues]:
        value, issues = super().dump(value)
        if not issues.can_proceed():
            return Invalid, issues
        return value.isoformat(), issues

    @staticmethod
    def _parse_xsd_datetime(value: str) -> t.Optional[datetime]:
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None


class Complex(AttributeType):
    SCIM_NAME = "complex"
    PARSE_TYPE = SCIMDataContainer
    DUMP_TYPE = SCIMDataContainer


_TYPE_TO_SCIM_TYPE: t.Dict[t.Type, str] = {
    bool: Boolean.SCIM_NAME,
    int: Integer.SCIM_NAME,
    float: Decimal.SCIM_NAME,
    str: String.SCIM_NAME,
    SCIMDataContainer: Complex.SCIM_NAME,
    list: "list",
    datetime: "datetime",
}


def get_scim_type(type_: t.Type) -> str:
    return _TYPE_TO_SCIM_TYPE.get(type_, "unknown")


def validate_absolute_url(value: str) -> ValidationIssues:
    issues = ValidationIssues()
    try:
        result = urlparse(value)
        is_valid = all([result.scheme, result.netloc])
        if not is_valid:
            issues.add(
                issue=ValidationError.bad_url(value),
                proceed=False,
            )
            return issues
    except ValueError:
        issues.add(
            issue=ValidationError.bad_url(value),
            proceed=False,
        )
        return issues
    return issues
