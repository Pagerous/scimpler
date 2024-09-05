import re
from typing import Any, Optional, Union, cast

from scimpler.error import ValidationError, ValidationIssues
from scimpler.registry import schemas

_ATTR_NAME = re.compile(r"([a-zA-Z][\w$-]*|\$ref)")
_URI_PREFIX = re.compile(r"(?:[\w.-]+:)*")
_ATTR_REP = re.compile(
    rf"({_URI_PREFIX.pattern})?({_ATTR_NAME.pattern}(\.([a-zA-Z][\w$-]*|\$ref))?)"
)


class AttrName(str):
    def __new__(cls, value: str) -> "AttrName":
        if not isinstance(value, AttrName) and not _ATTR_NAME.fullmatch(value):
            raise ValueError(f"{value!r} is not valid attr name")
        return cast(AttrName, str.__new__(cls, value))

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, str):
            other = other.lower()
        return self.lower() == other

    def __hash__(self):
        return hash(self.lower())


class SchemaURI(str):
    def __new__(cls, value: str) -> "SchemaURI":
        if not isinstance(value, SchemaURI) and not _URI_PREFIX.fullmatch(value + ":"):
            raise ValueError(f"{value!r} is not a valid schema URI")
        return cast(SchemaURI, str.__new__(cls, value))

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, str):
            other = other.lower()
        return self.lower() == other

    def __hash__(self):
        return hash(self.lower())


class AttrRep:
    def __init__(self, attr: str, sub_attr: Optional[str] = None):
        attr = AttrName(attr)
        str_: str = attr
        if sub_attr is not None:
            sub_attr = AttrName(sub_attr)
            str_ += "." + sub_attr

        self._attr = attr
        self._sub_attr = sub_attr
        self._str = str_

    def __str__(self) -> str:
        return self._str

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({str(self)})"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, AttrRep):
            return False

        return bool(self._attr == other._attr and self._sub_attr == other._sub_attr)

    def __hash__(self):
        return hash((self._attr, self._sub_attr))

    @property
    def attr(self) -> AttrName:
        return self._attr

    @property
    def sub_attr(self) -> AttrName:
        if self._sub_attr is None:
            raise AttributeError(f"{self!r} has no sub-attribute")
        return self._sub_attr

    @property
    def is_sub_attr(self) -> bool:
        return self._sub_attr is not None

    @property
    def location(self) -> tuple[str, ...]:
        if self._sub_attr:
            return self._attr, self._sub_attr
        return (self._attr,)


class BoundedAttrRep(AttrRep):
    def __init__(
        self,
        schema: str,
        attr: str,
        sub_attr: Optional[str] = None,
    ):
        super().__init__(attr, sub_attr)
        schema = SchemaURI(schema)
        is_extension = schemas.get(schema)
        if is_extension is None:
            raise ValueError(f"unknown schema {schema!r}")

        self._str = f"{schema}:{self._str}"
        self._schema = schema
        self._extension = is_extension

    def __eq__(self, other: Any) -> bool:
        parent_equals = super().__eq__(other)
        if not isinstance(other, BoundedAttrRep):
            return parent_equals

        return parent_equals and self._schema == other._schema

    def __hash__(self):
        return hash((self._attr, self._schema, self._sub_attr))

    @property
    def schema(self) -> SchemaURI:
        return self._schema

    @property
    def extension(self) -> bool:
        return self._extension

    @property
    def location(self) -> tuple[str, ...]:
        return ((self._schema,) if self.extension else tuple()) + super().location


class AttrRepFactory:
    @classmethod
    def validate(cls, value: str) -> ValidationIssues:
        issues = ValidationIssues()
        match = _ATTR_REP.fullmatch(value)
        if match is not None:
            schema = match.group(1)
            schema = schema[:-1] if schema else ""
            if not schema or SchemaURI(schema) in schemas:
                return issues
        issues.add_error(
            issue=ValidationError.bad_attribute_name(value),
            proceed=False,
        )
        return issues

    @classmethod
    def deserialize(cls, value: str) -> Union[AttrRep, BoundedAttrRep]:
        try:
            return cls._deserialize(value)
        except Exception as e:
            raise ValueError(f"{value!r} is not valid attribute representation") from e

    @classmethod
    def _deserialize(cls, value: str) -> Union[AttrRep, BoundedAttrRep]:
        if isinstance(value, AttrName):
            return AttrRep(attr=value)

        match = _ATTR_REP.fullmatch(value)
        if match is None:
            raise

        schema, attr = match.group(1), match.group(2)
        schema = schema[:-1] if schema else ""
        if "." in attr:
            attr, sub_attr = attr.split(".")
        else:
            attr, sub_attr = attr, None
        if schema:
            return BoundedAttrRep(
                schema=schema,
                attr=attr,
                sub_attr=sub_attr,
            )
        return AttrRep(attr=attr, sub_attr=sub_attr)
