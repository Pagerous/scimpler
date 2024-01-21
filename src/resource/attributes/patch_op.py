import typing as t

from src.attributes import type as at
from src.attributes.attributes import Attribute, ComplexAttribute, Missing, extract
from src.error import ValidationError, ValidationIssues
from src.patch import PatchPath


def parse_operation_type(op: str) -> t.Tuple[t.Optional[str], ValidationIssues]:
    issues = ValidationIssues()
    allowed_ops = ["add", "remove", "replace"]
    if op not in allowed_ops:
        issues.add(
            issue=ValidationError.must_be_one_of(allowed_ops, op),
            proceed=False,
        )
        return None, issues
    return op, issues


_operations_op = Attribute(
    name="op",
    type_=at.String,
    required=True,
    case_exact=True,
    parsers=[parse_operation_type],
)


_operations_path = Attribute(
    name="path",
    type_=at.String,
    required=False,
    case_exact=True,
    parsers=[PatchPath.parse],
)


_operations_value = Attribute(
    name="value",
    type_=at.Unknown,
)


def validate_operations(
    operations_data: t.List[t.Dict[str, t.Any]]
) -> t.Tuple[t.Optional[t.List[t.Dict[str, t.Any]]], ValidationIssues]:
    issues = ValidationIssues()
    for i, operation_data in enumerate(operations_data):
        type_ = extract("op", operation_data)
        path: PatchPath = extract("path", operation_data)
        value = extract("value", operation_data)
        if type_ == "remove" and path in [None, Missing]:
            issues.add(issue=ValidationError.missing(), proceed=False, location=(i, "path"))
        elif type_ == "add":
            if value in [None, Missing]:
                issues.add(issue=ValidationError.missing(), proceed=False, location=(i, "value"))
            if path and path.complex_filter is not None and path.complex_filter_attr_name is None:
                issues.add(
                    issue=ValidationError.complex_filter_without_sub_attr_for_add_op(),
                    proceed=False,
                    location=(i, "path"),
                )
    return operations_data, issues


operations = ComplexAttribute(
    sub_attributes=[
        _operations_op,
        _operations_path,
        _operations_value,
    ],
    name="Operations",
    required=True,
    multi_valued=True,
    complex_parsers=[validate_operations],
)
