import abc
from collections.abc import Sequence
from copy import copy, deepcopy
from functools import partial
from typing import Any, Callable, Iterable, Iterator, Mapping, Optional, cast

from typing_extensions import Self

from scimpler.data import Attribute
from scimpler.data.attrs import AttributeMutability, Complex
from scimpler.data.filter import Filter
from scimpler.data.identifiers import AttrName, AttrRep, AttrRepFactory, BoundedAttrRep
from scimpler.data.operator import ComplexAttributeOperator
from scimpler.data.schemas import BaseSchema
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
            filter_: Value selection filter, used for multivalued attributes. The only supported
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
        self._sub_attr_rep: Optional[AttrRep]
        if sub_attr_name is not None:
            self._sub_attr_rep = self._attr_rep.create_sub_attr_rep(sub_attr_name)
        else:
            self._sub_attr_rep = None
        self._filter = filter_

    @property
    def attr_rep(self) -> AttrRep:
        """
        The representation of the attribute being targeted.
        """
        return self._attr_rep

    @property
    def sub_attr_rep(self) -> Optional[AttrRep]:
        """
        The sub-attribute being targeted, if any.
        """
        return self._sub_attr_rep

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
            raise ValueError("invalid path expression") from None

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
        Serializes `PatchPath` to a string expression.
        """
        if self._filter:
            serialized = self._filter.serialize()
            if self.sub_attr_rep:
                serialized += f".{self.sub_attr_rep.sub_attr}"
            return serialized

        if self._sub_attr_rep is not None:
            return str(self._sub_attr_rep)

        return str(self._attr_rep)

    def __repr__(self):
        return f"PatchPath({self.serialize()})"

    def __eq__(self, other) -> bool:
        if not isinstance(other, PatchPath):
            return False

        return bool(
            self.attr_rep == other.attr_rep
            and self._filter == other._filter
            and self._sub_attr_rep == other._sub_attr_rep
        )

    def __call__(self, value: Any, schema: BaseSchema) -> bool:
        """
        Returns the flag indicating whether the provided value matches the value selection filter.

        Args:
            value: The value to test against the value selection filter.
            schema: Schema that describes the provided value.

        Raises:
            ValueError: When provided `schema` does not define the attribute targeted by the path.
            AttributeError: When the path does not have the value selection filter.

        Returns:
            Flag indicating whether the provided value matches the value selection filter.

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


class PatchException(Exception):
    pass


class MutabilityException(PatchException):
    pass


class NoTargetException(PatchException):
    pass


class PatchOperation(abc.ABC):
    type: str

    def __init__(self, path: Optional[PatchPath] = None):
        self._path = path

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, PatchOperation):
            return False
        return self._path == other._path

    @property
    def path(self) -> Optional[PatchPath]:
        """
        Target path of the operation. If `None`, a whole resource is the target.
        """
        return self._path

    def apply(self, data: Mapping, schema: BaseSchema, check_mutability: bool = True) -> ScimData:
        """
        Applies the operation on the provided `data` and returns the result.
        If the `data` is `ScimData`, the changes are also applied in place.

        Args:
            data: The data to apply the operation on. Should contain the current attributes state
                of the resource being updated.
            schema: The schema that describes the data.
            check_mutability: If `True`, the operation result is validated against attribute
                mutability rules.

        Raises:
            MutabilityException: If the operation violates attribute mutability rules.

        Returns:
            Updated data.
        """
        data = ScimData(data)
        old_data = cast(ScimData, deepcopy(ScimData(data))) if check_mutability else ScimData()

        self._apply(data, schema)

        if check_mutability:
            for attr_rep, attr in schema.attrs:
                _check_attr_mutability_violation(
                    attr=attr,
                    attr_rep=attr_rep,
                    old_value=old_data.get(attr_rep),
                    new_value=data.get(attr_rep),
                )
        return data

    @abc.abstractmethod
    def _apply(self, data: ScimData, schema: BaseSchema) -> None: ...

    def _get_attrs(self, schema: BaseSchema) -> tuple[Attribute, Optional[Attribute]]:
        if self._path is None:
            raise ValueError("operation has no 'path' specified")

        if self._path.sub_attr_rep:
            sub_attr = schema.attrs.get(self._path.sub_attr_rep)
            if sub_attr is None:
                raise NoTargetException(
                    f"unknown modification target {str(self._path.sub_attr_rep)!r} "
                    f"for {schema.__class__.__name__!r} schema"
                )
        else:
            sub_attr = None

        attr = schema.attrs.get(self._path.attr_rep)
        if attr is None:
            raise NoTargetException(
                f"unknown modification target {str(self._path.attr_rep)!r} "
                f"for {schema.__class__.__name__!r} schema"
            )

        return attr, sub_attr


class UpdateOperation(PatchOperation, abc.ABC):
    def __init__(self, path: Optional[PatchPath], value: Any) -> None:
        super().__init__(path)
        self._value = value

    @property
    def value(self) -> Any:
        """
        A value associated with the operation.
        """
        return self._value

    def _apply(self, data: ScimData, schema: BaseSchema) -> None:
        attr: Optional[Attribute]
        if self._path is None:
            value = ScimData(self._value)
            for attr_rep, attr in schema.attrs:
                attr_value = value.get(attr_rep)
                if attr_value is Missing:
                    continue

                self._apply_on_attr(
                    path=None,
                    value=attr_value,
                    attr_rep=attr_rep,
                    attr=attr,
                    sub_attr=None,
                    data=data,
                    schema=schema,
                )
            return

        attr, sub_attr = self._get_attrs(schema)
        self._apply_on_attr(
            path=self._path,
            value=self._value,
            attr_rep=self._path.attr_rep,
            attr=attr,
            sub_attr=sub_attr,
            data=data,
            schema=schema,
        )

    @classmethod
    def _apply_on_attr(
        cls,
        path: Optional[PatchPath],
        value: Any,
        attr_rep: AttrRep,
        attr: Attribute,
        sub_attr: Optional[Attribute],
        data: ScimData,
        schema: BaseSchema,
    ) -> None:
        matches_path = partial(path, schema=schema) if path and path.has_filter else None
        if sub_attr is None:
            if attr.multi_valued:
                cls._apply_on_multivalued_attr(
                    value=value,
                    data=data,
                    attr_rep=attr_rep,
                    attr=attr,
                    matches_path=matches_path,
                )
            else:
                cls._apply_on_singular_attr(
                    value=value,
                    data=data,
                    attr_rep=attr_rep,
                    attr=attr,
                )
            return

        if attr.multi_valued:
            cls._apply_on_multivalued_attr_with_sub_attr(
                value=value,
                data=data,
                attr_rep=attr_rep,
                sub_attr=sub_attr,
                matches_path=matches_path,
            )
        else:
            cls._apply_on_singular_attr_with_sub_attr(
                value=value,
                data=data,
                attr_rep=attr_rep,
                sub_attr=sub_attr,
            )

    @classmethod
    def _apply_on_singular_attr(
        cls,
        value: Any,
        data: ScimData,
        attr_rep: AttrRep,
        attr: Attribute,
    ) -> None:
        # e.g. User:name
        if isinstance(attr, Complex):
            attr_value = data.get(attr_rep) or ScimData()
            cls._apply_on_sub_attrs(
                value=ScimData(value),
                data=attr_value,
                attr=attr,
            )
        else:
            # e.g. User:nickName
            attr_value = value

        data.set(
            key=attr_rep,
            value=attr_value,
        )

    @classmethod
    def _apply_on_multivalued_attr(
        cls,
        value: Any,
        data: ScimData,
        attr_rep: AttrRep,
        attr: Attribute,
        matches_path: Optional[Callable],
    ) -> None:
        current_value = data.get(attr_rep) or []
        if not matches_path:
            # e.g. emails
            cls._apply_on_multivalued_attr_without_filter(
                value=value,
                data=data,
                attr_rep=attr_rep,
            )
            return

        if not isinstance(attr, Complex):
            # e.g. strings[value eq "abc"]
            has_matches = False
            updated_value = []
            for element in current_value:
                if matches_path(element):
                    updated_value.append(value)
                    has_matches = True
                else:
                    updated_value.append(element)

            if not has_matches:
                raise NoTargetException(
                    f"no {str(attr_rep)!r} elements matched supplied value selection filter"
                )

            data.set(key=attr_rep, value=updated_value)
            return

        # e.g. User:emails[type eq "work"]
        value = ScimData(value)
        has_matches = False
        updated_value = []
        for element in current_value:
            if matches_path(element):
                has_matches = True
                cls._apply_on_sub_attrs(
                    value=value,
                    data=element,
                    attr=attr,
                )
            updated_value.append(element)

        if not has_matches:
            raise NoTargetException(
                f"no {str(attr_rep)!r} elements matched supplied value selection filter"
            )

        data.set(key=attr_rep, value=updated_value)

    @classmethod
    def _apply_on_sub_attrs(
        cls,
        value: ScimData,
        data: ScimData,
        attr: Complex,
    ) -> None:
        for sub_attr_name, sub_attr in attr.attrs:
            sub_attr_value = value.get(sub_attr_name)
            if sub_attr_value is Missing:
                continue
            if sub_attr.multi_valued:
                cls._apply_on_multivalued_attr(
                    value=sub_attr_value,
                    data=data,
                    attr_rep=AttrRep(sub_attr_name),
                    attr=sub_attr,
                    matches_path=None,
                )
            else:
                cls._apply_on_singular_attr(
                    value=sub_attr_value,
                    data=data,
                    attr_rep=AttrRep(sub_attr_name),
                    attr=sub_attr,
                )

    @classmethod
    @abc.abstractmethod
    def _apply_on_multivalued_attr_without_filter(
        cls, value: Any, data: ScimData, attr_rep: AttrRep
    ) -> None: ...

    @classmethod
    def _apply_on_singular_attr_with_sub_attr(
        cls,
        value: Any,
        data: ScimData,
        attr_rep: AttrRep,
        sub_attr: Attribute,
    ) -> None:
        attr_value = data.get(attr_rep) or ScimData()
        if sub_attr.multi_valued:
            # assuming complex attribute that has multivalued sub-attribute
            cls._apply_on_multivalued_attr(
                value=value,
                data=attr_value,
                attr_rep=AttrRep(sub_attr.name),
                attr=sub_attr,
                matches_path=None,
            )
        else:
            # all the other cases, like User:name.formatted
            cls._apply_on_singular_attr(
                value=value,
                data=attr_value,
                attr_rep=AttrRep(sub_attr.name),
                attr=sub_attr,
            )
        data.set(key=attr_rep, value=attr_value)

    @classmethod
    def _apply_on_multivalued_attr_with_sub_attr(
        cls,
        value: Any,
        data: ScimData,
        attr_rep: AttrRep,
        sub_attr: Attribute,
        matches_path: Optional[Callable],
    ) -> None:
        if matches_path:
            cls._apply_on_multivalued_attr_with_sub_attr_and_filter(
                value=value,
                data=data,
                attr_rep=attr_rep,
                sub_attr=sub_attr,
                matches_path=matches_path,
            )
            return
        cls._apply_on_multivalued_attr_with_sub_attr_and_no_filter(
            value=value,
            data=data,
            attr_rep=attr_rep,
            sub_attr=sub_attr,
        )

    @classmethod
    def _apply_on_multivalued_attr_with_sub_attr_and_filter(
        cls,
        value: Any,
        data: ScimData,
        attr_rep: AttrRep,
        sub_attr: Attribute,
        matches_path: Callable,
    ):
        current_value = data.get(attr_rep) or []
        if not current_value:
            return

        updated_value = []
        has_matches = False
        for element in current_value:
            if not matches_path(element):
                updated_value.append(element)
                continue

            has_matches = True
            if sub_attr.multi_valued:
                # assuming complex attribute that has multivalued sub-attribute
                cls._apply_on_multivalued_attr(
                    value=value,
                    data=element,
                    attr_rep=AttrRep(sub_attr.name),
                    attr=sub_attr,
                    matches_path=None,
                )
            else:
                # all other cases, like User:emails[type eq "work"].value
                cls._apply_on_singular_attr(
                    value=value,
                    data=element,
                    attr_rep=AttrRep(sub_attr.name),
                    attr=sub_attr,
                )
            updated_value.append(element)

        if not has_matches:
            raise NoTargetException(
                f"no {str(attr_rep)!r} elements matched supplied value selection filter"
            )

    @classmethod
    def _apply_on_multivalued_attr_with_sub_attr_and_no_filter(
        cls, value: Any, data: ScimData, attr_rep: AttrRep, sub_attr: Attribute
    ) -> None:
        current_value = data.get(attr_rep) or []
        if not current_value:
            return

        updated_value = []
        for element in current_value:
            if sub_attr.multi_valued:
                # assuming complex attribute that has multivalued sub-attribute
                cls._apply_on_multivalued_attr(
                    value=value,
                    data=element,
                    attr_rep=AttrRep(sub_attr.name),
                    attr=sub_attr,
                    matches_path=None,
                )
            else:
                # all the other cases, like User:emails.type
                cls._apply_on_singular_attr(
                    value=value,
                    data=element,
                    attr_rep=AttrRep(sub_attr.name),
                    attr=sub_attr,
                )
            updated_value.append(element)

        data.set(
            key=attr_rep,
            value=updated_value,
        )


class Add(UpdateOperation):
    """
    The **add** operation, as specified in [RFC-7644, section 3.5.2.1.](https://www.rfc-editor.org/rfc/rfc7644#section-3.5.2.1)
    """

    type = "add"

    @classmethod
    def _apply_on_multivalued_attr_without_filter(
        cls, value: Any, data: ScimData, attr_rep: AttrRep
    ) -> None:
        current_value = data.get(attr_rep) or []
        if not isinstance(value, list):
            value = [value]
        updated_value = current_value
        updated_value.extend(value)
        data.set(key=attr_rep, value=updated_value)


class Replace(UpdateOperation):
    """
    The **replace** operation, as specified in [RFC-7644, section 3.5.2.3.](https://www.rfc-editor.org/rfc/rfc7644#section-3.5.2.3)
    """

    type = "replace"

    @classmethod
    def _apply_on_multivalued_attr_without_filter(
        cls, value: Any, data: ScimData, attr_rep: AttrRep
    ) -> None:
        if not isinstance(value, list):
            value = [value]
        data.set(key=attr_rep, value=value)


class Remove(PatchOperation):
    """
    The **remove** operation, as specified in [RFC-7644, section 3.5.2.2.](https://www.rfc-editor.org/rfc/rfc7644#section-3.5.2.2)
    """

    type = "remove"

    def __init__(self, path: PatchPath) -> None:
        super().__init__(path)

    @property
    def path(self) -> PatchPath:
        """
        Target path of the operation.
        """
        return cast(PatchPath, self._path)

    def _apply(self, data: ScimData, schema: BaseSchema) -> None:
        attr, sub_attr = self._get_attrs(schema)
        self._apply_on_attr(
            path=self.path,
            attr_rep=self.path.attr_rep,
            attr=attr,
            sub_attr=sub_attr,
            data=data,
            schema=schema,
        )

    @classmethod
    def _apply_on_attr(
        cls,
        path: PatchPath,
        attr_rep: AttrRep,
        attr: Attribute,
        sub_attr: Optional[Attribute],
        data: ScimData,
        schema: BaseSchema,
    ) -> None:
        matches_path = partial(path, schema=schema) if path.has_filter else None
        if sub_attr is None:
            if attr.multi_valued:
                cls._apply_on_multivalued_attr(
                    data=data,
                    attr_rep=attr_rep,
                    matches_path=matches_path,
                )
            else:
                cls._apply_on_singular_attr(
                    data=data,
                    attr_rep=attr_rep,
                )
            return

        if attr.multi_valued:
            cls._apply_on_multivalued_attr_with_sub_attr(
                data=data,
                attr_rep=attr_rep,
                sub_attr=sub_attr,
                matches_path=matches_path,
            )
        else:
            cls._apply_on_singular_attr_with_sub_attr(
                data=data,
                attr_rep=attr_rep,
                sub_attr=sub_attr,
            )

    @classmethod
    def _apply_on_singular_attr(
        cls,
        data: ScimData,
        attr_rep: AttrRep,
    ) -> None:
        if data.get(attr_rep):
            data.set(key=attr_rep, value=None)

    @classmethod
    def _apply_on_multivalued_attr(
        cls,
        data: ScimData,
        attr_rep: AttrRep,
        matches_path: Optional[Callable],
    ) -> None:
        current_value = data.get(attr_rep)
        if not current_value:
            return

        if not matches_path:
            # e.g. emails
            data.set(key=attr_rep, value=[])
            return

        # e.g. strings[value eq "abc"] or User:emails[type eq "work"]
        updated_value = []
        for element in current_value:
            if not matches_path(element):
                updated_value.append(element)
        data.set(key=attr_rep, value=updated_value)

    @classmethod
    def _apply_on_singular_attr_with_sub_attr(
        cls,
        data: ScimData,
        attr_rep: AttrRep,
        sub_attr: Attribute,
    ) -> None:
        attr_value = data.get(attr_rep)
        if not attr_value:
            return

        if sub_attr.multi_valued:
            cls._apply_on_multivalued_attr(
                data=attr_value,
                attr_rep=AttrRep(sub_attr.name),
                matches_path=None,
            )
        else:
            cls._apply_on_singular_attr(
                data=attr_value,
                attr_rep=AttrRep(sub_attr.name),
            )

    @classmethod
    def _apply_on_multivalued_attr_with_sub_attr(
        cls,
        data: ScimData,
        attr_rep: AttrRep,
        sub_attr: Attribute,
        matches_path: Optional[Callable],
    ) -> None:
        if matches_path:
            cls._apply_on_multivalued_attr_with_sub_attr_and_filter(
                data=data,
                attr_rep=attr_rep,
                sub_attr=sub_attr,
                matches_path=matches_path,
            )
            return
        cls._apply_on_multivalued_attr_with_sub_attr_and_no_filter(
            data=data,
            attr_rep=attr_rep,
            sub_attr=sub_attr,
        )

    @classmethod
    def _apply_on_multivalued_attr_with_sub_attr_and_filter(
        cls, data: ScimData, attr_rep: AttrRep, sub_attr: Attribute, matches_path: Callable
    ):
        current_value = data.get(attr_rep)
        if not current_value:
            return

        updated_value = []
        for element in current_value:
            if not matches_path(element):
                updated_value.append(element)
                continue

            if sub_attr.multi_valued:
                # assuming complex attribute that has multivalued sub-attribute
                cls._apply_on_multivalued_attr(
                    data=element,
                    attr_rep=AttrRep(sub_attr.name),
                    matches_path=None,
                )
            else:
                # all the other cases, like User:emails[type eq "work"].value
                cls._apply_on_singular_attr(
                    data=element,
                    attr_rep=AttrRep(sub_attr.name),
                )
            updated_value.append(element)

        data.set(
            key=attr_rep,
            value=updated_value,
        )

    @classmethod
    def _apply_on_multivalued_attr_with_sub_attr_and_no_filter(
        cls, data: ScimData, attr_rep: AttrRep, sub_attr: Attribute
    ) -> None:
        current_value = data.get(attr_rep) or []
        if not current_value:
            return

        updated_value = []
        for element in current_value:
            if sub_attr.multi_valued:
                # assuming complex attribute that has multivalued sub-attribute
                cls._apply_on_multivalued_attr(
                    data=element,
                    attr_rep=AttrRep(sub_attr.name),
                    matches_path=None,
                )
            else:
                # all the other cases, like User:emails.type
                cls._apply_on_singular_attr(
                    data=element,
                    attr_rep=AttrRep(sub_attr.name),
                )
            updated_value.append(element)

        data.set(
            key=attr_rep,
            value=updated_value,
        )


class PatchOperations:
    def __init__(self, operations: Sequence[PatchOperation]) -> None:
        self._operations = list(operations)

    def __getitem__(self, index: int) -> PatchOperation:
        return self._operations[index]

    def __iter__(self) -> Iterator[PatchOperation]:
        return iter(self._operations)

    def __eq__(self, other) -> bool:
        if not isinstance(other, PatchOperations):
            return False
        return self._operations == other._operations

    @classmethod
    def validate(cls, data: Iterable[Mapping]) -> ValidationIssues:
        """
        Validates the provided data against the requirements for the patch operations,
        as specified in RFC-7644.

        Args:
            data: Patch operations data to validate.

        Returns:
            Validation issues.
        """
        issues = ValidationIssues()
        for i, operation in enumerate(data):
            issues.merge(
                cls._validate_single(operation),
                location=[i],
            )
        return issues

    @classmethod
    def deserialize(cls, data: Iterable[Mapping]) -> Self:
        """
        Deserializes the provided data into `PatchOperations`. The exact types of
        inner operations depend on the values of 'op'.
        """
        return cls([cls._deserialize_single(operation) for operation in data])

    def serialize(self) -> list[ScimData]:
        """
        Serializes `PatchOperations` into a list of operations as mappings.
        """
        return [self._serialize_single(operation) for operation in self._operations]

    @classmethod
    def _validate_single(cls, data: Mapping) -> ValidationIssues:
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
    def _deserialize_single(cls, data: Mapping) -> "PatchOperation":
        data = ScimData(data)
        type_ = data.get("op", "").lower()
        path_exp = data.get("path")
        path = PatchPath.deserialize(path_exp) if path_exp else None
        if type_ == "add":
            return Add(path, data.get("value", None))
        if type_ == "replace":
            return Replace(path, data.get("value", None))
        if type_ == "remove":
            if path is None:
                raise ValueError("'path' must be specified for 'remove' operation")
            return Remove(path)
        raise ValueError(f"invalid patch operation type: {type_}")

    @classmethod
    def _serialize_single(cls, op: "PatchOperation") -> ScimData:
        data = {"op": op.type}
        if op.path is not None:
            data["path"] = op.path.serialize()
        if hasattr(op, "value"):
            data["value"] = getattr(op, "value")
        return ScimData(data)

    def apply(self, data: Mapping, schema: BaseSchema) -> ScimData:
        """
        Applies the operations on the provided `data` and returns the result.
        If the `data` is `ScimData`, the changes are also applied in place.

        After the operations are applied, the attribute mutability rules are checked
        against their violation. For example, modifying read-only attributes or
        removing required attributes violates these rules (see RFC-7644). Since this
        check is performed at the end, it means that if a first operation changes the
        attribute state, and a second brings its value back, nothing happens.

        Args:
            data: The data to apply the operation on. Should contain the current attributes state
                of the resource being updated.
            schema: The schema that describes the data.

        Raises:
            MutabilityException: If any of the operations violates attribute mutability rules.

        Returns:
            Updated data.
        """
        data = ScimData(data)
        old_data = cast(ScimData, deepcopy(ScimData(data)))

        for operation in self._operations:
            operation.apply(data, schema, check_mutability=False)

        for attr_rep, attr in schema.attrs:
            _check_attr_mutability_violation(
                attr=attr,
                attr_rep=attr_rep,
                old_value=old_data.get(attr_rep),
                new_value=data.get(attr_rep),
            )
        return data


def _check_attr_mutability_violation(
    attr: Attribute,
    attr_rep: AttrRep,
    old_value: Any,
    new_value: Any,
) -> None:
    _check_attr_read_only_violation(
        attr=attr,
        attr_rep=attr_rep,
        new_value=new_value,
        old_value=old_value,
    )
    _check_attr_immutable_violation(
        attr=attr,
        attr_rep=attr_rep,
        new_value=new_value,
        old_value=old_value,
    )
    _check_attr_required_violation(
        attr=attr,
        attr_rep=attr_rep,
        new_value=new_value,
        old_value=old_value,
    )

    if not isinstance(attr, Complex):
        return

    _check_sub_attrs_mutability_violation(
        attr=attr,
        attr_rep=attr_rep,
        old_value=old_value,
        new_value=new_value,
    )


def _check_attr_read_only_violation(
    attr: Attribute, attr_rep: AttrRep, new_value: Any, old_value: Any
):
    if (
        attr.mutability is AttributeMutability.READ_ONLY
        and new_value is not Missing
        and new_value != old_value
    ):
        raise MutabilityException(f"attribute {str(attr_rep)!r} is read-only")


def _check_attr_immutable_violation(
    attr: Attribute, attr_rep: AttrRep, new_value: Any, old_value: Any
):
    if attr.mutability is AttributeMutability.IMMUTABLE and old_value and old_value != new_value:
        raise MutabilityException(
            f"attribute {str(attr_rep)!r} is immutable and has value assigned already"
        )


def _check_attr_required_violation(
    attr: Attribute, attr_rep: AttrRep, new_value: Any, old_value: Any
):
    if old_value and not new_value and attr.required:
        raise MutabilityException(f"attribute {str(attr_rep)!r} is required")


def _check_sub_attrs_mutability_violation(
    attr: Complex, attr_rep: AttrRep, old_value: Any, new_value: Any
):
    if attr.multi_valued:
        new_value = new_value or []
        old_value = old_value or []
    else:
        new_value = [new_value]
        old_value = [old_value]

    new_value = [ScimData(element) for element in new_value]
    for sub_attr_name, sub_attr in attr.attrs:
        _check_sub_attr_mutability_violation(
            attr=attr,
            attr_rep=attr_rep,
            attr_old_value=old_value,
            attr_new_value=new_value,
            sub_attr=sub_attr,
            sub_attr_name=sub_attr_name,
        )


def _check_sub_attr_mutability_violation(
    attr: Attribute,
    attr_rep: AttrRep,
    attr_old_value: list,
    attr_new_value: list,
    sub_attr: Attribute,
    sub_attr_name: AttrName,
):
    n_items = max(len(attr_new_value), len(attr_old_value))
    for i in range(n_items):
        try:
            old_element = attr_old_value[i]
        except IndexError:
            old_element = None

        try:
            new_element = attr_new_value[i]
        except IndexError:
            new_element = None

        if (old_element is None or new_element is None) and attr.multi_valued:
            continue

        old_element = old_element or ScimData()
        new_element = new_element or ScimData()
        sub_attr_old_value = old_element.get(sub_attr_name)
        sub_attr_new_value = new_element.get(sub_attr_name)
        _check_attr_mutability_violation(
            attr=sub_attr,
            attr_rep=attr_rep.create_sub_attr_rep(sub_attr_name),
            old_value=sub_attr_old_value,
            new_value=sub_attr_new_value,
        )
