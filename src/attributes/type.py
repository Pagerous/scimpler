import abc
import base64
import binascii
import typing as t
from datetime import datetime

from ..error import ValidationError, ValidationIssues
from . import validators


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
                issue=ValidationError.bad_scim_parse_type(
                    scim_type=cls.SCIM_NAME,
                    expected_type=cls.PARSE_TYPE,
                    provided_type=type(value),
                ),
                proceed=False,
            )
            value = None
        return value, issues

    @classmethod
    def dump(cls, value: t.Any) -> t.Tuple[t.Any, ValidationIssues]:
        issues = ValidationIssues()
        if not isinstance(value, cls.DUMP_TYPE):
            issues.add(
                issue=ValidationError.bad_scim_dump_type(
                    scim_type=cls.SCIM_NAME,
                    expected_type=cls.DUMP_TYPE,
                    provided_type=type(value),
                ),
                proceed=False,
            )
            value = None
        return value, issues


class Any(AttributeType):
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
            if value is not None:
                value = float(value)
            return value, issues
        return super().parse(value)

    @classmethod
    def dump(cls, value: t.Any) -> t.Tuple[t.Optional[float], ValidationIssues]:
        if isinstance(value, int):
            value, issues = Integer.dump(value)
            if value is not None:
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
            return None, issues
        cls._validate_encoding(value, issues)
        if not issues.can_proceed():
            return None, issues
        return value, issues

    @classmethod
    def dump(cls, value: t.Any) -> t.Tuple[t.Optional[str], ValidationIssues]:
        value, issues = super().dump(value)
        if not issues.can_proceed():
            return None, issues
        cls._validate_encoding(value, issues)
        if not issues.can_proceed():
            return None, issues
        return value, issues

    @classmethod
    def _validate_encoding(cls, value: t.Any, issues: ValidationIssues) -> ValidationIssues:
        try:
            if (
                base64.b64encode(base64.b64decode(value).decode("utf-8").encode("utf-8")).decode(
                    "utf-8"
                )
                != value
            ):
                issues.add(
                    issue=ValidationError.base_64_encoding_required(cls.SCIM_NAME),
                    proceed=False,
                )
        except (binascii.Error, UnicodeDecodeError):
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
            value, issues_ = validators.validate_absolute_url(value)
            issues.merge(issues=issues_)
        if issues.can_proceed():
            return value, issues
        return None, issues

    @classmethod
    def dump(cls, value: t.Any) -> t.Tuple[t.Optional[str], ValidationIssues]:
        value, issues = super().dump(value)
        if issues.can_proceed():
            value, issues_ = validators.validate_absolute_url(value)
            issues.merge(issues=issues_)
        if issues.can_proceed():
            return value, issues
        return None, issues


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
            return None, issues
        value = cls._parse_xsd_datetime(value)
        if value is None:
            issues.add(
                issue=ValidationError.xsd_datetime_format_required(cls.SCIM_NAME),
                proceed=False,
            )
        return value, issues

    @classmethod
    def dump(cls, value: t.Any) -> t.Tuple[t.Optional[str], ValidationIssues]:
        value, issues = super().dump(value)
        if not issues.can_proceed():
            return None, issues
        return value.isoformat(), issues

    @staticmethod
    def _parse_xsd_datetime(value: str) -> t.Optional[datetime]:
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None


class Complex(AttributeType):
    SCIM_NAME = "complex"
    PARSE_TYPE = dict
    DUMP_TYPE = dict
