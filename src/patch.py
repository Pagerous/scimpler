from typing import Optional, Tuple

from src.attributes.attributes import AttributeName
from src.error import ValidationError, ValidationIssues
from src.filter.filter import OP_REGEX, parse_comparison_value
from src.filter.operator import Equal


class PatchPath:
    def __init__(
        self,
        attr_name: AttributeName,
        complex_filter: Optional[Equal],
        complex_filter_attr_name: Optional[AttributeName],
    ):
        if attr_name.sub_attr and (complex_filter or complex_filter_attr_name):
            raise ValueError("sub-attribute can not be complex")
        if complex_filter_attr_name:
            if not complex_filter_attr_name.sub_attr:
                raise ValueError("sub-attribute name is required for 'complex_filter_attr_name'")
            if not complex_filter_attr_name.top_level_equals(attr_name):
                raise ValueError(
                    "non-matching top-level attributes for 'attr_name' "
                    "and 'complex_filter_attr_name'"
                )
        if complex_filter:
            if not complex_filter.attr_name.sub_attr:
                raise ValueError("complex filter can operate on sub-attributes only")
            if not complex_filter.attr_name.top_level_equals(attr_name):
                raise ValueError(
                    "non-matching top-level attributes for 'attr_name' and 'complex_filter'"
                )

        self._attr_name = attr_name
        self._complex_filter = complex_filter
        self._complex_filter_attr_name = complex_filter_attr_name

    @property
    def attr_name(self) -> AttributeName:
        return self._attr_name

    @property
    def complex_filter(self) -> Optional[Equal]:
        return self._complex_filter

    @property
    def complex_filter_attr_name(self) -> Optional[AttributeName]:
        return self._complex_filter_attr_name

    @classmethod
    def parse(cls, path: str) -> Tuple[Optional["PatchPath"], ValidationIssues]:
        issues = ValidationIssues()
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
            return cls._parse_complex_multivalued_path(path)
        else:
            attr_name = AttributeName.parse(path)
            if attr_name is None:
                issues.add(issue=ValidationError.bad_attribute_name(path), proceed=False)
                return None, issues
            return (
                PatchPath(attr_name=attr_name, complex_filter=None, complex_filter_attr_name=None),
                issues,
            )

    @classmethod
    def _parse_complex_multivalued_path(
        cls, path: str
    ) -> Tuple[Optional["PatchPath"], ValidationIssues]:
        issues = ValidationIssues()

        attr_name_exp = path[: path.index("[")]
        attr_name = AttributeName.parse(attr_name_exp)
        if attr_name is None:
            issues.add(issue=ValidationError.bad_attribute_name(attr_name_exp), proceed=False)
        elif attr_name.sub_attr:
            issues.add(
                issue=ValidationError.complex_sub_attribute(attr_name.attr, attr_name.sub_attr),
                proceed=False,
            )

        multivalued_filter = None
        multivalued_filter_exp = path[path.index("[") + 1 : path.index("]")]
        components = OP_REGEX.split(multivalued_filter_exp)
        if len(components) != 3:
            issues.add(issue=ValidationError.bad_multivalued_attribute_filter(), proceed=False)
        else:
            if components[1].lower() != "eq":
                issues.add(issue=ValidationError.eq_operator_allowed_only(), proceed=False)
            sub_attr_name = cls._get_sub_attr_name(issues, attr_name, components[0])
            try:
                value = parse_comparison_value(components[2])
            except ValueError:
                value = None
                issues.add(issue=ValidationError.bad_comparison_value(components[2]), proceed=False)

            if issues.can_proceed():
                multivalued_filter = Equal(sub_attr_name, value)

        value_sub_attr_name = None
        value_sub_attr_name_exp = path[path.index("]") + 1 :]
        if value_sub_attr_name_exp:
            if value_sub_attr_name_exp.startswith("."):
                value_sub_attr_name_exp = value_sub_attr_name_exp[1:]
            value_sub_attr_name = cls._get_sub_attr_name(
                issues=issues,
                attr_name=attr_name,
                sub_attr_name_exp=value_sub_attr_name_exp,
            )

        if issues.has_issues():
            return None, issues
        return (
            cls(
                attr_name=attr_name,
                complex_filter=multivalued_filter,
                complex_filter_attr_name=value_sub_attr_name,
            ),
            issues,
        )

    @staticmethod
    def _get_sub_attr_name(
        issues: ValidationIssues,
        attr_name: Optional[AttributeName],
        sub_attr_name_exp: str,
    ):
        sub_attr_name = AttributeName.parse(sub_attr_name_exp)
        if sub_attr_name is None:
            issues.add(issue=ValidationError.bad_attribute_name(sub_attr_name_exp), proceed=False)
        elif sub_attr_name.sub_attr:
            if attr_name is not None and not attr_name.top_level_equals(sub_attr_name):
                issues.add(
                    issue=ValidationError.complex_sub_attribute(attr_name.attr, sub_attr_name.attr),
                    proceed=False,
                )
        elif attr_name is not None:
            sub_attr_name = AttributeName(
                schema=attr_name.schema,
                attr=attr_name.attr,
                sub_attr=sub_attr_name.attr,
            )
        return sub_attr_name
