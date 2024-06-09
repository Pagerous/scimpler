from copy import copy
from typing import Any, Optional, TypeVar

from src.container import (
    AttrName,
    AttrRep,
    AttrRepFactory,
    BoundedAttrRep,
    SCIMDataContainer,
)
from src.data.attributes import Complex
from src.data.filter import Filter
from src.data.operator import ComplexAttributeOperator, LogicalOperator
from src.data.schemas import BaseSchema
from src.data.utils import decode_placeholders, encode_strings
from src.error import ValidationError, ValidationIssues

TAttrRep = TypeVar("TAttrRep", bound=AttrRep)


class PatchPath:
    def __init__(
        self,
        attr_rep: TAttrRep,
        sub_attr_name: Optional[str],
        filter_: Optional[Filter[ComplexAttributeOperator]] = None,
    ):
        if attr_rep.sub_attr:
            raise ValueError("'attr_rep' must not be a sub attribute")

        if filter_ is not None and filter_.operator.attr_rep != attr_rep:
            raise ValueError(
                f"provided filter is configured for {filter_.operator.attr_rep!r}, "
                f"but {attr_rep!r} is required"
            )

        self._attr_rep = attr_rep

        if sub_attr_name:
            sub_attr_name = AttrName(sub_attr_name)
        self._sub_attr_name = sub_attr_name
        self._filter = filter_

    @property
    def attr_rep(self) -> TAttrRep:
        return self._attr_rep

    @property
    def sub_attr_name(self) -> Optional[AttrName]:
        return self._sub_attr_name

    @property
    def has_filter(self) -> bool:
        return self._filter is not None

    @classmethod
    def validate(cls, path: str) -> ValidationIssues:
        issues = ValidationIssues()
        path, placeholders = encode_strings(path)
        if (
            path.count("[") > 1
            or path.count("]") > 1
            or ("[" in path and "]" not in path)
            or ("]" in path and "[" not in path)
            or ("[" in path and "]" in path and path.index("[") > path.index("]"))
        ):
            issues.add_error(issue=ValidationError.bad_value_syntax(), proceed=False)
            return issues

        if "[" in path and "]" in path:
            return cls._validate_complex_multivalued_path(path, placeholders)

        path = decode_placeholders(path, placeholders)
        issues.merge(AttrRepFactory.validate(path))
        return issues

    @classmethod
    def _validate_complex_multivalued_path(
        cls, path: str, placeholders: dict[str, Any]
    ) -> ValidationIssues:
        filter_exp = decode_placeholders(path[: path.index("]") + 1], placeholders)
        issues = Filter.validate(filter_exp)
        if issues.has_errors():
            return issues
        value_sub_attr_rep_exp = path[path.index("]") + 1 :]
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
    def deserialize(cls, path: str) -> "PatchPath":
        try:
            return cls._deserialize(path)
        except Exception as e:
            raise ValueError("invalid path expression", e)

    @classmethod
    def _deserialize(cls, path: str) -> "PatchPath":
        path, placeholders = encode_strings(path)
        if "[" in path and "]" in path:
            return cls._deserialize_complex_multivalued_path(path, placeholders)

        if "[" in path or "]" in path:
            raise ValueError("invalid path expression")

        attr_rep = AttrRepFactory.deserialize(decode_placeholders(path, placeholders))
        if attr_rep.sub_attr:
            sub_attr_name = attr_rep.sub_attr
            if isinstance(attr_rep, BoundedAttrRep):
                attr_rep = BoundedAttrRep(
                    schema=attr_rep.schema,
                    extension=attr_rep.extension,
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
        cls, path: str, placeholders: dict[str, Any]
    ) -> "PatchPath":
        filter_exp = decode_placeholders(path[: path.index("]") + 1], placeholders)
        filter_ = Filter.deserialize(filter_exp)
        sub_attr_name = None
        sub_attr_exp = path[path.index("]") + 1 :]
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

    def __repr__(self):
        if self._filter:
            repr_ = self._filter.serialize()
        elif isinstance(self._attr_rep, BoundedAttrRep):
            repr_ = str(
                BoundedAttrRep(
                    schema=self._attr_rep.schema,
                    extension=self._attr_rep.extension,
                    attr=self._attr_rep.attr,
                    sub_attr=self._sub_attr_name,
                )
            )
        else:
            repr_ = str(
                AttrRep(
                    attr=self._attr_rep.attr,
                    sub_attr=self._sub_attr_name,
                )
            )
        return f"PatchPath({repr_})"

    def __eq__(self, other) -> bool:
        if not isinstance(other, PatchPath):
            return False

        return bool(
            self.attr_rep == other.attr_rep
            and self._filter == other._filter
            and self._sub_attr_name == other._sub_attr_name
        )

    def __call__(self, value: Any, schema: BaseSchema) -> bool:
        attr = schema.attrs.get_by_path(self)
        if attr is None:
            raise ValueError(f"path does not indicate any attribute for {schema!r} schema")

        if not self._filter:
            return True

        if isinstance(value, dict):
            value = SCIMDataContainer(value)

        if attr.multi_valued:
            value = [value]

        if isinstance(attr, Complex):
            data = SCIMDataContainer()
            data.set(self._attr_rep, value)
            return self._filter(data, schema)

        operator = self._filter.operator.sub_operator
        if isinstance(operator, LogicalOperator):
            data = SCIMDataContainer()
            data.set("value", value)
        else:
            data = value

        value_attr = copy(attr)
        value_attr._name = AttrName("value")
        return self._filter.operator.sub_operator.match(
            value=data,
            schema_or_complex=Complex(
                name=self._attr_rep.attr,
                sub_attributes=[value_attr],
            ),
        )
