from collections.abc import Sequence
from copy import copy
from enum import Enum
from typing import Any, Iterable, Iterator, Mapping, Optional

from typing_extensions import Self

from scimpler.data.attrs import Complex
from scimpler.data.filter import Filter
from scimpler.data.identifiers import AttrName, AttrRep, AttrRepFactory, BoundedAttrRep
from scimpler.data.operator import ComplexAttributeOperator
from scimpler.data.schemas import ResourceSchema
from scimpler.data.scim_data import Missing, ScimData
from scimpler.data.utils import decode_placeholders, encode_strings
from scimpler.error import ScimErrorType, ValidationError, ValidationIssues


class PatchPath:
    """
    Target modification path, used in PATCH requests. Supports path syntax, as specified in
    RFC-7644.
    """

    def __init__(
        self,
        attr_rep: AttrRep,
        sub_attr_name: Optional[str] = None,
        filter_: Optional[Filter[ComplexAttributeOperator]] = None,
    ):
        """
        Args:
            attr_rep: The representation of the attribute being targeted. Must not be
                a sub-attribute representation.
            sub_attr_name: The optional sub-attribute being targeted.
            filter_: Value selection filter, used for multi-valued attributes. The only supported
                operator is `ComplexAttributeOperator`. The attribute representation specified
                in the filter itself must be the same as provided `attr_rep`.

        Raises:
            ValueError: When `attr_rep` is a sub-attribute representation.
            ValueError: When `filter_` does not consist of `ComplexAttributeOperator`.
            ValueError: When attribute representation specified in the filter's operator differs
                from the `attr_rep`.
        """
        if attr_rep.is_sub_attr:
            raise ValueError("'attr_rep' must not be a sub attribute")

        if filter_ is not None:
            if not isinstance(filter_.operator, ComplexAttributeOperator):
                raise ValueError("'filter_' must consist of 'ComplexAttributeOperator'")

            if filter_.operator.attr_rep != attr_rep:
                raise ValueError(
                    f"provided filter is configured for {filter_.operator.attr_rep!r}, "
                    f"but {attr_rep!r} is required"
                )

        self._attr_rep = attr_rep
        if sub_attr_name is not None:
            sub_attr_name = AttrName(sub_attr_name)
        self._sub_attr_name = sub_attr_name
        self._filter = filter_

    @property
    def attr_rep(self) -> AttrRep:
        """
        The representation of the attribute being targeted.
        """
        return self._attr_rep

    @property
    def sub_attr_name(self) -> Optional[AttrName]:
        """
        The sub-attribute being targeted, if any.
        """
        return self._sub_attr_name

    @property
    def has_filter(self) -> bool:
        """
        Flag indicating whether the path contains the value selection filter.
        """
        return self._filter is not None

    @classmethod
    def validate(cls, path_exp: str) -> ValidationIssues:
        """
        Validates the provided path expression, according to RFC-7644.

        Args:
            path_exp: Path expression to validate.

        Returns:
            Validation issues.
        """
        path_exp, placeholders = encode_strings(path_exp)
        if (
            path_exp.count("[") > 1
            or path_exp.count("]") > 1
            or ("[" in path_exp and "]" not in path_exp)
            or ("]" in path_exp and "[" not in path_exp)
            or ("[" in path_exp and "]" in path_exp and path_exp.index("[") > path_exp.index("]"))
        ):
            issues = ValidationIssues()
            issues.add_error(issue=ValidationError.bad_value_syntax(), proceed=False)
            return issues

        elif "[" in path_exp and "]" in path_exp:
            issues = cls._validate_complex_multivalued_path(path_exp, placeholders)
        else:
            issues = ValidationIssues()
            path_exp = decode_placeholders(path_exp, placeholders)
            issues.merge(AttrRepFactory.validate(path_exp))

        for _, errors in issues.errors:
            for error in errors:
                error.scim_error = ScimErrorType.INVALID_PATH
        return issues

    @classmethod
    def _validate_complex_multivalued_path(
        cls, path_exp: str, placeholders: dict[str, Any]
    ) -> ValidationIssues:
        filter_exp = decode_placeholders(path_exp[: path_exp.index("]") + 1], placeholders)
        issues = Filter.validate(filter_exp)
        if issues.has_errors():
            return issues
        value_sub_attr_rep_exp = path_exp[path_exp.index("]") + 1 :]
        if value_sub_attr_rep_exp:
            if value_sub_attr_rep_exp.startswith("."):
                value_sub_attr_rep_exp = value_sub_attr_rep_exp[1:]
            try:
                AttrName(value_sub_attr_rep_exp)
            except ValueError:
                issues.add_error(
                    issue=ValidationError.bad_attribute_name(attribute=value_sub_attr_rep_exp),
                    proceed=False,
                )
        return issues

    @classmethod
    def deserialize(cls, path_exp: str) -> "PatchPath":
        """
        Deserializes the provided path expression into a `PatchPath`.

        Args:
            path_exp: Path expression to deserialize.

        Raises:
            ValueError: When `path_exp` is not a valid path expression.

        Returns:
            Deserialized `PatchPath`.
        """
        try:
            return cls._deserialize(path_exp)
        except Exception:
            raise ValueError("invalid path expression")

    @classmethod
    def _deserialize(cls, path_exp: str) -> "PatchPath":
        path_exp, placeholders = encode_strings(path_exp)
        if "[" in path_exp and "]" in path_exp:
            return cls._deserialize_complex_multivalued_path(path_exp, placeholders)

        if "[" in path_exp or "]" in path_exp:
            raise ValueError("invalid path expression")

        attr_rep = AttrRepFactory.deserialize(decode_placeholders(path_exp, placeholders))
        if attr_rep.is_sub_attr:
            sub_attr_name = attr_rep.sub_attr
            if isinstance(attr_rep, BoundedAttrRep):
                attr_rep = BoundedAttrRep(
                    schema=attr_rep.schema,
                    attr=attr_rep.attr,
                )
            else:
                attr_rep = AttrRep(attr=attr_rep.attr)
        else:
            sub_attr_name = None

        return PatchPath(
            attr_rep=attr_rep,
            sub_attr_name=sub_attr_name,
            filter_=None,
        )

    @classmethod
    def _deserialize_complex_multivalued_path(
        cls, path_exp: str, placeholders: dict[str, Any]
    ) -> "PatchPath":
        filter_exp = decode_placeholders(path_exp[: path_exp.index("]") + 1], placeholders)
        filter_ = Filter.deserialize(filter_exp)
        sub_attr_name = None
        sub_attr_exp = path_exp[path_exp.index("]") + 1 :]
        if sub_attr_exp:
            if sub_attr_exp.startswith("."):
                sub_attr_exp = sub_attr_exp[1:]
            sub_attr_exp = decode_placeholders(sub_attr_exp, placeholders)
            sub_attr_name = AttrName(sub_attr_exp)

        return cls(
            attr_rep=filter_.operator.attr_rep,
            sub_attr_name=sub_attr_name,
            filter_=filter_,
        )

    def serialize(self) -> str:
        """
        Serializes `PatchPath` to string expression.
        """
        if self._filter:
            serialized = self._filter.serialize()
            if self.sub_attr_name:
                serialized += f".{self.sub_attr_name}"
            return serialized

        if isinstance(self._attr_rep, BoundedAttrRep):
            return str(
                BoundedAttrRep(
                    schema=self._attr_rep.schema,
                    attr=self._attr_rep.attr,
                    sub_attr=self._sub_attr_name,
                )
            )
        return str(
            AttrRep(
                attr=self._attr_rep.attr,
                sub_attr=self._sub_attr_name,
            )
        )

    def __repr__(self):
        return f"PatchPath({self.serialize()})"

    def __eq__(self, other) -> bool:
        if not isinstance(other, PatchPath):
            return False

        return bool(
            self.attr_rep == other.attr_rep
            and self._filter == other._filter
            and self._sub_attr_name == other._sub_attr_name
        )

    def __call__(self, value: Any, schema: ResourceSchema) -> bool:
        """
        Returns the flag indicating whether the provided value matches value selection filter.

        Args:
            value: The value to test against value selection filter.
            schema: Schema that describes the provided value.

        Raises:
            ValueError: When provided `schema` does not define the attribute targeted by the path.
            AttributeError: When the path does not have value selection filter.

        Returns:
            Flag indicating whether the provided value matches value selection filter.

        Examples:
            >>> from scimpler.schemas import UserSchema
            >>>
            >>> path = PatchPath.deserialize("emails[type eq 'work']")
            >>> path({"type": "work", "display": "user@example.com"}, UserSchema())
            >>> True
            >>> path({"type": "home", "display": "user@example.com"}, UserSchema())
            >>> False

            >>> path = PatchPath.deserialize("simpleAttr[value ge 42]")
            >>> path(42, ...)  # assuming '...' is schema that contains 'simpleAttr'
            >>> True
            >>> path(41, ...)  # assuming '...' is schema that contains 'simpleAttr'
            >>> False
        """
        attr = schema.attrs.get(self.attr_rep)
        if attr is None:
            raise ValueError(f"path does not target any attribute for {schema!r} schema")

        if self._filter is None:
            raise AttributeError("path has no value selection filter")

        if isinstance(value, Mapping):
            value = ScimData(value)

        value = [value]
        if isinstance(attr, Complex):
            data = ScimData()
            data.set(self._attr_rep, value)
            return self._filter(data, schema)

        data = ScimData({"value": value})
        value_attr = copy(attr)
        value_attr._name = AttrName("value")
        return self._filter.operator.sub_operator.match(
            value=data,
            schema_or_complex=Complex(
                name=self._attr_rep.attr,
                sub_attributes=[value_attr],
            ),
        )


class PatchOperationType(str, Enum):
    ADD = "add"
    REPLACE = "replace"
    REMOVE = "remove"


class PatchOperation:
    def __init__(self, type_: PatchOperationType, path: Optional[PatchPath], value: Any) -> None:
        self._type = PatchOperationType(type_)
        if type_ == PatchOperationType.REMOVE:
            if path is None:
                raise ValueError("'path' must be specified for remove operation")
            value = None
        self._path = path
        self._value = value

    @property
    def type(self) -> PatchOperationType:
        return self._type

    @property
    def path(self) -> Optional[PatchPath]:
        return self._path

    @property
    def value(self) -> Any:
        return self._value

    @classmethod
    def validate(cls, data: Mapping) -> ValidationIssues:
        data = ScimData(data)
        issues = ValidationIssues()
        type_ = data.get("op")
        path = data.get("path")
        if path:
            issues.merge(PatchPath.validate(path), location=["path"])
        elif type_ == "remove":
            issues.add_error(
                issue=ValidationError.missing(),
                proceed=False,
                location=["path"],
            )
        elif type_ in ["add", "replace"] and data.get("value") is Missing:
            issues.add_error(
                issue=ValidationError.missing(),
                proceed=False,
                location=["value"],
            )
        return issues

    @classmethod
    def deserialize(cls, data: Mapping) -> Self:
        data = ScimData(data)
        type_ = data.get("op", "").lower()
        path_exp = data.get("path")
        path = PatchPath.deserialize(path_exp) if path_exp else None
        return cls(type_, path, data.get("value", None))

    def serialize(self) -> ScimData:
        data = {
            "op": self._type.value,
        }
        if self._path is not None:
            data["path"] = self._path.serialize()
        if self._value is not None and self._type != PatchOperationType.REMOVE:
            data["value"] = self._value
        return ScimData(data)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, PatchOperation):
            return False
        return self._type == other.type and self._path == other.path and self.value == other.value


class PatchOperations:
    def __init__(self, operations: Sequence[PatchOperation]) -> None:
        self._operations = list(operations)

    def __getitem__(self, index: int) -> PatchOperation:
        return self._operations[index]

    def __iter__(self) -> Iterator[PatchOperation]:
        return iter(self._operations)

    @classmethod
    def validate(cls, data: Iterable[Mapping]) -> ValidationIssues:
        issues = ValidationIssues()
        for i, operation in enumerate(data):
            issues.merge(
                PatchOperation.validate(operation),
                location=[i],
            )
        return issues

    @classmethod
    def deserialize(cls, data: Iterable[Mapping]) -> Self:
        return cls([PatchOperation.deserialize(operation) for operation in data])

    def serialize(self) -> list[ScimData]:
        return [operation.serialize() for operation in self._operations]

    def __eq__(self, other) -> bool:
        if not isinstance(other, PatchOperations):
            return False
        return self._operations == other._operations
