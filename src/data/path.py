from typing import Any, Dict, Optional

from src.data.container import AttrRep
from src.data.operator import ComplexAttributeOperator
from src.error import ValidationError, ValidationIssues
from src.filter import Filter
from src.utils import decode_placeholders, encode_strings


class PatchPath:
    def __init__(
        self,
        attr_rep: AttrRep,
        complex_filter: Optional[Filter],
        complex_filter_attr_rep: Optional[AttrRep],
    ):
        if attr_rep.sub_attr and (complex_filter or complex_filter_attr_rep):
            raise ValueError("sub-attribute can not be complex")
        if complex_filter_attr_rep:
            if not complex_filter_attr_rep.sub_attr:
                raise ValueError("sub-attribute name is required for 'complex_filter_attr_rep'")
            if not complex_filter_attr_rep.top_level_equals(attr_rep):
                raise ValueError(
                    "non-matching top-level attributes for 'attr_rep' "
                    "and 'complex_filter_attr_rep'"
                )
        if complex_filter is not None:
            if not isinstance(complex_filter.operator, ComplexAttributeOperator):
                raise ValueError("only ComplexAttributeOperator is supported as path filter")

            if complex_filter.operator.attr_rep != attr_rep:
                raise ValueError(
                    "non-matching top-level attributes for 'attr_rep' and 'complex_filter'"
                )

        self._attr_rep = attr_rep
        self._complex_filter = complex_filter
        self._complex_filter_attr_rep = complex_filter_attr_rep

    @property
    def attr_rep(self) -> AttrRep:
        return self._attr_rep

    @property
    def complex_filter(self) -> Optional[Filter]:
        return self._complex_filter

    @property
    def complex_filter_attr_rep(self) -> Optional[AttrRep]:
        return self._complex_filter_attr_rep

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
        issues.merge(AttrRep.validate(path))
        return issues

    @classmethod
    def _validate_complex_multivalued_path(
        cls, path: str, placeholders: Dict[str, Any]
    ) -> ValidationIssues:
        filter_exp = decode_placeholders(path[: path.index("]") + 1], placeholders)
        issues = Filter.validate(filter_exp)
        if issues.has_errors():
            return issues
        filter_ = Filter.deserialize(filter_exp)
        value_sub_attr_rep_exp = path[path.index("]") + 1 :]
        if value_sub_attr_rep_exp:
            if value_sub_attr_rep_exp.startswith("."):
                value_sub_attr_rep_exp = value_sub_attr_rep_exp[1:]
            issues.merge(
                cls._validate_sub_attr_rep(
                    attr_rep=filter_.operator.attr_rep,
                    sub_attr_rep_exp=decode_placeholders(value_sub_attr_rep_exp, placeholders),
                )
            )
        return issues

    @staticmethod
    def _validate_sub_attr_rep(attr_rep: AttrRep, sub_attr_rep_exp: str) -> ValidationIssues:
        issues = ValidationIssues()
        try:
            sub_attr_rep = AttrRep.deserialize(sub_attr_rep_exp)
            if sub_attr_rep.sub_attr and not attr_rep.top_level_equals(sub_attr_rep):
                issues.add_error(
                    issue=ValidationError.complex_sub_attribute(attr_rep.attr, sub_attr_rep.attr),
                    proceed=False,
                )
        except ValueError:
            issues.add_error(
                issue=ValidationError.bad_attribute_name(sub_attr_rep_exp), proceed=False
            )
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
            attr_rep=AttrRep.deserialize(decode_placeholders(path, placeholders)),
            complex_filter=None,
            complex_filter_attr_rep=None,
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
            val_attr_rep = AttrRep.deserialize(val_attr_exp)
            assert not val_attr_rep.sub_attr
            val_attr_rep = AttrRep(
                schema=filter_.operator.attr_rep.schema,
                attr=filter_.operator.attr_rep.attr,
                sub_attr=val_attr_rep.attr,
            )
        return cls(
            attr_rep=filter_.operator.attr_rep,
            complex_filter=filter_,
            complex_filter_attr_rep=val_attr_rep,
        )

    def __eq__(self, other) -> bool:
        if not isinstance(other, PatchPath):
            return False

        return bool(
            self.attr_rep == other.attr_rep
            and self.complex_filter == other.complex_filter
            and self.complex_filter_attr_rep == other.complex_filter_attr_rep
        )
