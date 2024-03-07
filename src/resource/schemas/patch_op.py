from typing import Any, List, Optional, Tuple, Union

from src.data import type as at
from src.data.attributes import Attribute, AttributeMutability, ComplexAttribute
from src.data.container import AttrRep, Invalid, Missing, SCIMDataContainer
from src.data.path import PatchPath
from src.error import ValidationError, ValidationIssues
from src.schemas import BaseSchema, ResourceSchema


def parse_operation_type(op: str) -> Tuple[Union[Invalid, str], ValidationIssues]:
    issues = ValidationIssues()
    allowed_ops = ["add", "remove", "replace"]
    if op not in allowed_ops:
        issues.add(
            issue=ValidationError.must_be_one_of(allowed_ops, op),
            proceed=False,
        )
        return Invalid, issues
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
    operations_data: List[SCIMDataContainer],
) -> Tuple[List[SCIMDataContainer], ValidationIssues]:
    issues = ValidationIssues()
    for i, operation_data in enumerate(operations_data):
        type_ = operation_data[_operations_op.rep]
        path: PatchPath = operation_data[_operations_path.rep]
        value = operation_data[_operations_value.rep]
        if type_ == "remove" and path in [None, Missing]:
            issues.add(
                issue=ValidationError.missing(),
                proceed=False,
                location=(i, _operations_path.rep.attr),
            )
            del operation_data[_operations_value.rep]
        elif type_ == "add":
            if value in [None, Missing]:
                issues.add(
                    issue=ValidationError.missing(),
                    proceed=False,
                    location=(i, _operations_value.rep.attr),
                )
            if path and path.complex_filter is not None and path.complex_filter_attr_rep is None:
                issues.add(
                    issue=ValidationError.complex_filter_without_sub_attr_for_add_op(),
                    proceed=False,
                    location=(i, _operations_path.rep.attr),
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


class PatchOp(BaseSchema):
    def __init__(self, resource_schema: ResourceSchema):
        super().__init__(
            schema="urn:ietf:params:scim:api:messages:2.0:PatchOp",
            attrs=[operations],
        )
        self._resource_schema = resource_schema

    def __repr__(self) -> str:
        return "PatchOp"

    def parse(self, data: Any) -> Tuple[Union[Invalid, SCIMDataContainer], ValidationIssues]:
        data, issues = super().parse(data)
        if not issues.can_proceed((self.attrs.operations.rep.attr,)):
            return data, issues

        parsed = []
        ops = data[self.attrs.operations__op.rep]
        paths = data[self.attrs.operations__path.rep]
        values = data[self.attrs.operations__value.rep]

        for i, (op, path, value) in enumerate(zip(ops, paths, values)):
            if issues.has_issues((operations.rep.attr, i)):
                parsed_op = SCIMDataContainer(
                    {
                        "op": op,
                        "path": path,
                        "value": value,
                    }
                )
                parsed.append(parsed_op)
                continue

            if op in ["add", "replace"]:
                parsed_op, issues_ = self._parse_add_or_replace_operation(op, path, value)
                issues.merge(issues_, location=(self.attrs.operations.rep.attr, i))
                parsed.append(parsed_op)
            else:
                parsed_op, issues_ = self._parse_remove_operation(path)
                issues.merge(issues_, location=(self.attrs.operations.rep.attr, i))
                parsed.append(parsed_op)

        data[operations.rep] = parsed
        return data, issues

    def _parse_remove_operation(
        self, path: PatchPath
    ) -> Tuple[Union[Invalid, SCIMDataContainer], ValidationIssues]:
        issues = validate_operation_path(self._resource_schema, path)
        if issues:
            return Invalid, issues

        attr = self._resource_schema.attrs.get(path.attr_rep)
        path_location = (self.attrs.operations__path.rep.sub_attr,)
        if path.complex_filter_attr_rep is None:
            if attr.mutability == AttributeMutability.READ_ONLY:
                issues.add(
                    issue=ValidationError.attribute_can_not_be_modified(),
                    proceed=True,
                    location=path_location,
                )
            if attr.required:
                if isinstance(attr, ComplexAttribute):
                    pass  # TODO: add warning here
                else:
                    issues.add(
                        issue=ValidationError.attribute_can_not_be_deleted(),
                        proceed=True,
                        location=path_location,
                    )
        else:
            sub_attr = self._resource_schema.attrs.get(path.complex_filter_attr_rep)
            if sub_attr.required:
                issues.add(
                    issue=ValidationError.attribute_can_not_be_deleted(),
                    proceed=True,
                    location=path_location,
                )
            if (
                attr.mutability == AttributeMutability.READ_ONLY
                or sub_attr.mutability == AttributeMutability.READ_ONLY
            ):
                issues.add(
                    issue=ValidationError.attribute_can_not_be_modified(),
                    proceed=True,
                    location=path_location,
                )

        return SCIMDataContainer({"op": "remove", "path": path}), issues

    def _parse_add_or_replace_operation(
        self, op: str, path: Union[PatchPath, None, Missing], value: Any
    ) -> Tuple[Union[Invalid, SCIMDataContainer], ValidationIssues]:
        issues = ValidationIssues()
        if path not in [None, Missing]:
            issues_ = validate_operation_path(self._resource_schema, path)
            if issues_:
                issues.merge(issues_, location=(self.attrs.operations__path.rep.sub_attr,))
                return Invalid, issues

        value, issues_ = self._parse_operation_value(path, value)
        issues.merge(
            issues_,
            location=(self.attrs.operations__value.rep.sub_attr,),
        )
        return SCIMDataContainer({"op": op, "path": path, "value": value}), issues

    def _parse_operation_value(
        self, path: Optional[PatchPath], value: Any
    ) -> Tuple[Any, ValidationIssues]:
        if path in [None, Missing]:
            value, issues = self._resource_schema.parse(value)
            issues.drop(("schemas",), code=27)
            issues.drop(("schemas",), code=28)
            issues.drop(("schemas",), code=29)
            for attr in self._resource_schema.attrs:
                if (
                    value[attr.rep] is not Missing
                    and attr.mutability == AttributeMutability.READ_ONLY
                ):
                    location = (attr.rep.attr,)
                    if attr.rep.sub_attr:
                        location = location + (attr.rep.sub_attr,)
                    if attr.rep.extension:
                        location = (attr.rep.schema,) + location
                    issues.add(
                        issue=ValidationError.attribute_can_not_be_modified(),
                        proceed=False,
                        location=location,
                    )
            return value, issues

        # sub-attribute of filtered multivalued complex attribute
        if (
            isinstance(self._resource_schema.attrs.get(path.attr_rep), ComplexAttribute)
            and path.complex_filter
            and path.complex_filter_attr_rep
        ):
            return self._parse_update_attr_value(path.complex_filter_attr_rep, value)
        return self._parse_update_attr_value(path.attr_rep, value)

    def _parse_update_attr_value(
        self, attr_rep: AttrRep, attr_value: Any
    ) -> Tuple[Any, ValidationIssues]:
        issues = ValidationIssues()

        attr = self._resource_schema.attrs.get(attr_rep)
        if attr is None:
            return Invalid, issues

        if attr.mutability == AttributeMutability.READ_ONLY:
            issues.add(
                issue=ValidationError.attribute_can_not_be_modified(),
                proceed=False,
            )
            return Invalid, issues

        parsed_attr_value, issues_ = attr.parse(attr_value)
        if issues_:
            issues.merge(issues_)

        elif isinstance(attr, ComplexAttribute) and not attr.multi_valued:
            for sub_attr in attr.attrs:
                if sub_attr.mutability != AttributeMutability.READ_ONLY:
                    # non-read-only attributes can be updated
                    continue
                v = parsed_attr_value[sub_attr.rep]
                if v is not Missing:
                    issues.add(
                        issue=ValidationError.attribute_can_not_be_modified(),
                        proceed=False,
                        location=(sub_attr.rep.sub_attr,),
                    )
        return parsed_attr_value, issues


def validate_operation_path(schema: ResourceSchema, path: PatchPath) -> ValidationIssues:
    issues = ValidationIssues()
    if schema.attrs.get(path.attr_rep) is None or (
        path.complex_filter_attr_rep is not None
        and schema.attrs.get(path.complex_filter_attr_rep) is None
    ):
        issues.add(
            issue=ValidationError.unknown_operation_target(),
            proceed=False,
        )
    return issues
