from typing import Dict, Optional, Tuple

from src.data.container import AttrRep
from src.data.operator import ComplexAttributeOperator
from src.error import ValidationError, ValidationIssues
from src.filter import Filter
from src.utils import PLACEHOLDER_REGEX, STRING_VALUES_REGEX, get_placeholder


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
    def parse(cls, path: str) -> Tuple[Optional["PatchPath"], ValidationIssues]:
        issues = ValidationIssues()

        string_values = {}
        for match in STRING_VALUES_REGEX.finditer(path):
            start, stop = match.span()
            string_value = match.string[start:stop]
            string_values[start] = string_value
            path = path.replace(string_value, get_placeholder(start), 1)

        if (
            path.count("[") > 1
            or path.count("]") > 1
            or ("[" in path and "]" not in path)
            or ("]" in path and "[" not in path)
            or ("[" in path and "]" in path and path.index("[") > path.index("]"))
        ):
            issues.add(issue=ValidationError.bad_operation_path(), proceed=False)
            return None, issues

        if "[" in path and "]" in path:
            return cls._parse_complex_multivalued_path(path, string_values)

        path = cls._encode_string_values(path, string_values)
        attr_rep = AttrRep.parse(path)
        if attr_rep is None:
            issues.add(issue=ValidationError.bad_attribute_name(path), proceed=False)
            return None, issues
        return (
            PatchPath(attr_rep=attr_rep, complex_filter=None, complex_filter_attr_rep=None),
            issues,
        )

    @classmethod
    def _parse_complex_multivalued_path(
        cls, path: str, string_values
    ) -> Tuple[Optional["PatchPath"], ValidationIssues]:
        filter_exp = path[: path.index("]") + 1]
        filter_, issues = Filter.parse(cls._encode_string_values(filter_exp, string_values))
        if issues.has_issues():
            return None, issues

        value_sub_attr_rep = None
        value_sub_attr_rep_exp = path[path.index("]") + 1 :]
        if value_sub_attr_rep_exp:
            if value_sub_attr_rep_exp.startswith("."):
                value_sub_attr_rep_exp = value_sub_attr_rep_exp[1:]
            value_sub_attr_rep = cls._get_sub_attr_rep(
                issues=issues,
                attr_rep=filter_.operator.attr_rep,
                sub_attr_rep_exp=cls._encode_string_values(value_sub_attr_rep_exp, string_values),
            )

        if issues.has_issues():
            return None, issues
        return (
            cls(
                attr_rep=filter_.operator.attr_rep,
                complex_filter=filter_,
                complex_filter_attr_rep=value_sub_attr_rep,
            ),
            issues,
        )

    @staticmethod
    def _get_sub_attr_rep(
        issues: ValidationIssues,
        attr_rep: Optional[AttrRep],
        sub_attr_rep_exp: str,
    ):
        sub_attr_rep = AttrRep.parse(sub_attr_rep_exp)
        if sub_attr_rep is None:
            issues.add(issue=ValidationError.bad_attribute_name(sub_attr_rep_exp), proceed=False)
        elif sub_attr_rep.sub_attr:
            if attr_rep is not None and not attr_rep.top_level_equals(sub_attr_rep):
                issues.add(
                    issue=ValidationError.complex_sub_attribute(attr_rep.attr, sub_attr_rep.attr),
                    proceed=False,
                )
        elif attr_rep is not None:
            sub_attr_rep = AttrRep(
                schema=attr_rep.schema,
                attr=attr_rep.attr,
                sub_attr=sub_attr_rep.attr,
            )
        return sub_attr_rep

    @staticmethod
    def _encode_string_values(exp: str, string_values: Dict[int, str]):
        encoded = exp
        for match in PLACEHOLDER_REGEX.finditer(exp):
            index = int(match.group(1))
            if index in (string_values or {}):
                encoded = encoded.replace(match.group(0), string_values[index])
        return encoded

    def __eq__(self, other) -> bool:
        if not isinstance(other, PatchPath):
            return False

        return bool(
            self.attr_rep == other.attr_rep
            and self.complex_filter == other.complex_filter
            and self.complex_filter_attr_rep == other.complex_filter_attr_rep
        )
