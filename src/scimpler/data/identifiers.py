import re
from typing import Any, Optional, Union, cast

from scimpler._registry import schemas
from scimpler.error import ValidationError, ValidationIssues

_ATTR_NAME = re.compile(r"([a-zA-Z][\w$-]*|\$ref)")
_URI_PREFIX = re.compile(r"(?:[\w.-]+:)*")
_ATTR_REP = re.compile(
    rf"({_URI_PREFIX.pattern})?({_ATTR_NAME.pattern}(\.([a-zA-Z][\w$-]*|\$ref))?)"
)


class AttrName(str):
    """
    Represents unbounded attribute name. Must conform attribute name notation, as
    specified in RFC-7643.

    Attribute names are case-insensitive.

    Raises:
        ValueError: If the provided value is not valid attribute name.
    """

    def __repr__(self):
        return f"AttrName({self})"

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


class SchemaUri(str):
    """
    Represents schema URI.

    Schema URIs are case-insensitive.

    Raises:
        ValueError: If the provided value is not valid schema URI.
    """

    def __new__(cls, value: str) -> "SchemaUri":
        if not isinstance(value, SchemaUri) and not _URI_PREFIX.fullmatch(value + ":"):
            raise ValueError(f"{value!r} is not a valid schema URI")
        return cast(SchemaUri, str.__new__(cls, value))

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, str):
            other = other.lower()
        return self.lower() == other

    def __hash__(self):
        return hash(self.lower())


class AttrRep:
    """
    Representation of an unbounded attribute or sub-attribute (no schema association).
    """

    def __init__(self, attr: str, sub_attr: Optional[str] = None):
        """
        Args:
            attr: The attribute name.
            sub_attr: The sub-attribute name.
        """
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
        """
        The attribute name.
        """
        return self._attr

    @property
    def sub_attr(self) -> AttrName:
        """
        The sub-attribute name.
        Raises:
            AttributeError: If `AttrRep` has no sub-attribute name assigned, meaning it represents
                top-level attribute.
        """
        if self._sub_attr is None:
            raise AttributeError(f"{self!r} has no sub-attribute")
        return self._sub_attr

    @property
    def is_sub_attr(self) -> bool:
        """
        Flag indicating whether `AttrRep` represents sub-attribute.
        """
        return self._sub_attr is not None

    @property
    def location(self) -> tuple[str, ...]:
        if self._sub_attr:
            return self._attr, self._sub_attr
        return (self._attr,)


class BoundedAttrRep(AttrRep):
    """
    Representation of a bounded attribute or sub-attribute (with schema association).
    """

    def __init__(
        self,
        schema: str,
        attr: str,
        sub_attr: Optional[str] = None,
    ):
        """
        Args:
            schema: The schema URI to which the attribute or sub-attribute belongs.
            attr: The attribute name.
            sub_attr: The sub-attribute name.

        Raises:
            ValueError: If the provided `schema` is not recognized in the system registry.
        """
        super().__init__(attr, sub_attr)
        schema = SchemaUri(schema)
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
    def schema(self) -> SchemaUri:
        """
        The schema URI to which the attribute or sub-attribute belongs.
        """
        return self._schema

    @property
    def extension(self) -> bool:
        """
        Flag indicating whether the represented attribute or sub-attribute belongs to a
        schema extension.
        """
        return self._extension

    @property
    def location(self) -> tuple[str, ...]:
        return ((self._schema,) if self.extension else tuple()) + super().location


class AttrRepFactory:
    """
    Attribute representation factory. Able to validate string-based representations and
    deserialize them to `AttrRep` or `BoundedAttrRep`.
    """

    @classmethod
    def validate(cls, value: str) -> ValidationIssues:
        """
        Validates if the provided `value` is valid attribute representation and returns
        validation issues.
        """
        issues = ValidationIssues()
        match = _ATTR_REP.fullmatch(value)
        if match is not None:
            schema = match.group(1)
            schema = schema[:-1] if schema else ""
            if not schema or SchemaUri(schema) in schemas:
                return issues
        issues.add_error(
            issue=ValidationError.bad_attribute_name(value),
            proceed=False,
        )
        return issues

    @classmethod
    def deserialize(cls, value: str) -> Union[AttrRep, BoundedAttrRep]:
        """
        Deserializes the provided `value` to `AttrRep` or `BoundedAttrRep`.

        Args:
            value: The value to deserialize.

        Raises:
            ValueError: If the provided `value` is not valid attribute representation.

        Returns:
            Attribute representation. The type depends on the `value` content.

        Examples:
            >>> AttrRepFactory.deserialize("name.formatted")
            "AttrRep(attr='name', sub_attr='formatted')"
            >>> AttrRepFactory.deserialize(
            >>>     "urn:ietf:params:scim:schemas:core:2.0:Group:members.type"
            >>> )
            "BoundedAttrRep(
                schema='urn:ietf:params:scim:schemas:core:2.0:Group:members.type',
                attr='members',
                sub_attr='type'
            )"
        """
        try:
            return cls._deserialize(value)
        except Exception:
            raise ValueError(f"{value!r} is not valid attribute representation")

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
