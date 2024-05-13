from typing import Any, Dict, Optional

from src.container import AttrRep, BoundedAttrRep
from src.error import ValidationError, ValidationIssues
from src.filter import Filter
from src.operator import ComplexAttributeOperator
from src.utils import decode_placeholders, encode_strings


class PatchPath:
    def __init__(
        self,
        attr_rep: BoundedAttrRep,
        filter: Optional[Filter],  # noqa
        filter_sub_attr_rep: Optional[AttrRep],
    ):
        if attr_rep.sub_attr and (filter or filter_sub_attr_rep):
            raise ValueError("sub-attribute can not be complex")

        if filter is not None:
            if not isinstance(filter.operator, ComplexAttributeOperator):
                raise ValueError("only ComplexAttributeOperator is supported as path filter")

            if filter.operator.attr_rep != attr_rep:
                raise ValueError("non-matching top-level attributes for 'attr_rep' and 'filter'")

        self._attr_rep = attr_rep
        self._filter = filter
        self._filter_sub_attr_rep = filter_sub_attr_rep

    @property
    def attr_rep(self) -> BoundedAttrRep:
        return self._attr_rep

    @property
    def filter(self) -> Optional[Filter]:
        return self._filter

    @property
    def filter_sub_attr_rep(self) -> Optional[AttrRep]:
        return self._filter_sub_attr_rep

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
            issues.add_error(issue=ValidationError.bad_operation_path(), proceed=False)
            return issues

        if "[" in path and "]" in path:
            return cls._validate_complex_multivalued_path(path, placeholders)

        path = decode_placeholders(path, placeholders)
        issues.merge(BoundedAttrRep.validate(path))
        return issues

    @classmethod
    def _validate_complex_multivalued_path(
        cls, path: str, placeholders: Dict[str, Any]
    ) -> ValidationIssues:
        filter_exp = decode_placeholders(path[: path.index("]") + 1], placeholders)
        issues = Filter.validate(filter_exp)
        if issues.has_errors():
            return issues
        value_sub_attr_rep_exp = path[path.index("]") + 1 :]
        if value_sub_attr_rep_exp:
            if value_sub_attr_rep_exp.startswith("."):
                value_sub_attr_rep_exp = value_sub_attr_rep_exp[1:]
            issues.merge(AttrRep.validate(value_sub_attr_rep_exp))
        return issues

    @classmethod
    def deserialize(cls, path: str) -> "PatchPath":
        try:
            return cls._deserialize(path)
        except Exception:
            raise ValueError("invalid path expression")

    @classmethod
    def _deserialize(cls, path: str) -> "PatchPath":
        path, placeholders = encode_strings(path)
        if "[" in path and "]" in path:
            return cls._deserialize_complex_multivalued_path(path, placeholders)

        assert "[" not in path and "]" not in path
        return PatchPath(
            attr_rep=BoundedAttrRep.deserialize(decode_placeholders(path, placeholders)),
            filter=None,
            filter_sub_attr_rep=None,
        )

    @classmethod
    def _deserialize_complex_multivalued_path(
        cls, path: str, placeholders: Dict[str, Any]
    ) -> "PatchPath":
        filter_exp = decode_placeholders(path[: path.index("]") + 1], placeholders)
        filter_ = Filter.deserialize(filter_exp)
        val_attr_rep = None
        val_attr_exp = path[path.index("]") + 1 :]
        if val_attr_exp:
            if val_attr_exp.startswith("."):
                val_attr_exp = val_attr_exp[1:]
            val_attr_exp = decode_placeholders(val_attr_exp, placeholders)
            val_attr_rep = AttrRep(val_attr_exp)

        return cls(
            attr_rep=filter_.operator.attr_rep,
            filter=filter_,
            filter_sub_attr_rep=val_attr_rep,
        )

    def __eq__(self, other) -> bool:
        if not isinstance(other, PatchPath):
            return False

        return bool(
            self.attr_rep == other.attr_rep
            and self.filter == other.filter
            and self.filter_sub_attr_rep == other.filter_sub_attr_rep
        )