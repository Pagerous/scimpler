import abc
import base64
import binascii
import re
from datetime import datetime
from typing import Any, Type

from ..error import ValidationError
from . import validators


class AttributeType(abc.ABC):
    TYPE: Type
    SCIM_NAME: str

    @classmethod
    def validate(cls, value: Any) -> list[ValidationError]:
        if not isinstance(value, cls.TYPE):
            return [
                ValidationError.bad_type(
                    scim_type=cls.SCIM_NAME,
                    expected_type=cls.TYPE,
                    provided_type=type(value),
                )
            ]
        return []


class Boolean(AttributeType):
    SCIM_NAME = "boolean"
    TYPE = bool


class Decimal(AttributeType):
    SCIM_NAME = "decimal"
    TYPE = float

    @classmethod
    def validate(cls, value: Any) -> list[ValidationError]:
        if isinstance(value, int):
            return []
        return super().validate(value)


class Integer(AttributeType):
    SCIM_NAME = "integer"
    TYPE = int

    @classmethod
    def validate(cls, value: Any) -> list[ValidationError]:
        if isinstance(value, float) and int(value) == value:
            return []
        return super().validate(value)


class String(AttributeType):
    SCIM_NAME = "string"
    TYPE = str


class Binary(String):
    SCIM_NAME = "binary"
    TYPE = str

    @classmethod
    def validate(cls, value: TYPE) -> list[ValidationError]:
        errors = super().validate(value)
        if errors:
            return errors
        try:
            if base64.b64encode(base64.b64decode(value).decode("utf-8").encode("utf-8")).decode("utf-8") != value:
                errors.append(ValidationError.base_64_encoding_required(cls.SCIM_NAME))
        except (binascii.Error, UnicodeDecodeError):
            errors.append(ValidationError.base_64_encoding_required(cls.SCIM_NAME))
        return errors


class ExternalReference(String):
    SCIM_NAME = "reference"
    TYPE = str

    @classmethod
    def validate(cls, value: TYPE) -> list[ValidationError]:
        errors = super().validate(value)
        if errors:
            return errors
        return validators.validate_absolute_url(value)


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
    def validate(cls, value: TYPE) -> list[ValidationError]:
        errors = super().validate(value)
        if errors:
            return errors
        if not cls._is_xsd_datetime(value):
            return [ValidationError.xsd_datetime_format_required(cls.SCIM_NAME)]
        return []

    @staticmethod
    def _is_xsd_datetime(value: str) -> bool:
        xsd_datetime_pattern = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?"
        match = re.fullmatch(xsd_datetime_pattern, value)
        if match is None:
            return False
        try:
            datetime.fromisoformat(value)
            return True
        except ValueError:
            return False


class Complex(AttributeType):
    SCIM_NAME = "complex"
    TYPE = dict
    ALLOWED_ITEM_TYPES = tuple(
        {
            Integer.TYPE,
            Decimal.TYPE,
            Boolean.TYPE,
            String.TYPE,
            Binary.TYPE,
            ExternalReference.TYPE,
            URIReference.TYPE,
            SCIMReference.TYPE,
            DateTime.TYPE
        }
    )

    @classmethod
    def validate(cls, value: TYPE) -> list[ValidationError]:
        errors = super().validate(value)
        if errors:
            return errors
        for k, v in value.items():
            if not isinstance(v, cls.ALLOWED_ITEM_TYPES):
                errors.append(
                    ValidationError.bad_sub_attribute_type(
                        scim_type=cls.SCIM_NAME,
                        allowed_types=cls.ALLOWED_ITEM_TYPES,
                        provided_type=type(v)
                    )
                )
        return errors

