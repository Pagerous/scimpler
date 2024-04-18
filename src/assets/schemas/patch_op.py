from typing import Any, List, Optional, Union

from src.data.attributes import AttributeMutability, Complex, String, Unknown
from src.data.container import AttrRep, Invalid, Missing, SCIMDataContainer
from src.data.path import PatchPath
from src.data.schemas import BaseSchema, ResourceSchema
from src.error import ValidationError, ValidationIssues

_operations_op = String(
    "op",
    canonical_values=["add", "remove", "replace"],
    restrict_canonical_values=True,
    required=True,
)


_operations_path = String(
    "path",
    validators=[PatchPath.validate],
    parser=PatchPath.parse,
)


_operations_value = Unknown("value")


def validate_operations(value: List[SCIMDataContainer]) -> ValidationIssues:
    issues = ValidationIssues()
    for i, item in enumerate(value):
        type_ = item.get(_operations_op.rep)
        path = item.get(_operations_path.rep)
        op_value = item.get(_operations_value.rep)
        if type_ == "remove" and path in [None, Missing]:
            issues.add_error(
                issue=ValidationError.missing(),
                proceed=False,
                location=(i, _operations_path.rep.attr),
            )
        elif type_ == "add":
            if op_value in [None, Missing]:
                issues.add_error(
                    issue=ValidationError.missing(),
                    proceed=False,
                    location=(i, _operations_value.rep.attr),
                )
            if (
                path
                and (path := PatchPath.parse(path)).complex_filter is not None
                and path.complex_filter_attr_rep is None
            ):
                issues.add_error(
                    issue=ValidationError.complex_filter_without_sub_attr_for_add_op(),
                    proceed=False,
                    location=(i, _operations_path.rep.attr),
                )
    return issues


def parse_operations(value: List[SCIMDataContainer]) -> List[SCIMDataContainer]:
    for i, item in enumerate(value):
        if item == "remove":
            item.pop(_operations_value.rep)
    return value


operations = Complex(
    sub_attributes=[
        _operations_op,
        _operations_path,
        _operations_value,
    ],
    name="Operations",
    required=True,
    multi_valued=True,
    validators=[validate_operations],
    parser=parse_operations,
)


class PatchOp(BaseSchema):
    def __init__(self, resource_schema: ResourceSchema):
        super().__init__(
            schema="urn:ietf:params:scim:api:messages:2.0:PatchOp",
            attrs=[operations],
        )
        self._resource_schema = resource_schema

    def _validate(self, data: SCIMDataContainer) -> ValidationIssues:
        issues = ValidationIssues()
        ops = data.get(self.attrs.operations__op.rep)
        paths = data.get(self.attrs.operations__path.rep)
        values = data.get(self.attrs.operations__value.rep)

        for i, (op, path, value) in enumerate(zip(ops, paths, values)):
            if Invalid in (op, path, value):
                continue

            if path is not Missing:
                path = PatchPath.parse(path)
            if op in ["add", "replace"]:
                issues.merge(
                    issues=self._validate_add_or_replace_operation(path, value),
                    location=(self.attrs.operations.rep.attr, i),
                )
            else:
                issues.merge(
                    issues=self._validate_remove_operation(path),
                    location=(self.attrs.operations.rep.attr, i),
                )

        return issues

    def _validate_remove_operation(self, path: PatchPath) -> ValidationIssues:
        issues = validate_operation_path(self._resource_schema, path)
        if issues.has_errors():
            return issues

        attr = self._resource_schema.attrs.get(path.attr_rep)
        path_location = (self.attrs.operations__path.rep.sub_attr,)
        if path.complex_filter_attr_rep is None:
            if attr.mutability == AttributeMutability.READ_ONLY:
                issues.add_error(
                    issue=ValidationError.attribute_can_not_be_modified(),
                    proceed=True,
                    location=path_location,
                )
            if attr.required:
                if isinstance(attr, Complex):
                    pass  # TODO: add warning here
                else:
                    issues.add_error(
                        issue=ValidationError.attribute_can_not_be_deleted(),
                        proceed=True,
                        location=path_location,
                    )
        else:
            sub_attr = self._resource_schema.attrs.get(path.complex_filter_attr_rep)
            if sub_attr.required:
                issues.add_error(
                    issue=ValidationError.attribute_can_not_be_deleted(),
                    proceed=True,
                    location=path_location,
                )
            if (
                attr.mutability == AttributeMutability.READ_ONLY
                or sub_attr.mutability == AttributeMutability.READ_ONLY
            ):
                issues.add_error(
                    issue=ValidationError.attribute_can_not_be_modified(),
                    proceed=True,
                    location=path_location,
                )

        return issues

    def _validate_add_or_replace_operation(
        self, path: Union[PatchPath, None, Missing], value: Any
    ) -> ValidationIssues:
        issues = ValidationIssues()
        if path not in [None, Missing]:
            issues_ = validate_operation_path(self._resource_schema, path)
            if issues_.has_errors():
                issues.merge(issues_, location=(self.attrs.operations__path.rep.sub_attr,))
                return issues

        issues.merge(
            issues=self._validate_operation_value(path, value),
            location=(self.attrs.operations__value.rep.sub_attr,),
        )
        return issues

    def _validate_operation_value(self, path: Optional[PatchPath], value: Any) -> ValidationIssues:
        if path in [None, Missing]:
            issues = self._resource_schema.validate(value)
            issues.pop_error(("schemas",), code=27)
            issues.pop_error(("schemas",), code=28)
            issues.pop_error(("schemas",), code=29)
            for attr in self._resource_schema.attrs:
                if (
                    value.get(attr.rep) is not Missing
                    and attr.mutability == AttributeMutability.READ_ONLY
                ):
                    location = (attr.rep.attr,)
                    if attr.rep.sub_attr:
                        location = location + (attr.rep.sub_attr,)
                    if attr.rep.extension:
                        location = (attr.rep.schema,) + location
                    issues.add_error(
                        issue=ValidationError.attribute_can_not_be_modified(),
                        proceed=False,
                        location=location,
                    )
            return issues

        # sub-attribute of filtered multivalued complex attribute
        if (
            isinstance(self._resource_schema.attrs.get(path.attr_rep), Complex)
            and path.complex_filter
            and path.complex_filter_attr_rep
        ):
            attr_rep = path.complex_filter_attr_rep
        else:
            attr_rep = path.attr_rep
        return self._validate_update_attr_value(attr_rep, value)

    def _validate_update_attr_value(self, attr_rep: AttrRep, attr_value: Any) -> ValidationIssues:
        issues = ValidationIssues()

        attr = self._resource_schema.attrs.get(attr_rep)
        if attr is None:
            return issues

        if attr.mutability == AttributeMutability.READ_ONLY:
            issues.add_error(
                issue=ValidationError.attribute_can_not_be_modified(),
                proceed=False,
            )
            return issues

        issues_ = attr.validate(attr_value)
        issues.merge(issues_)
        if not issues_.can_proceed():
            return issues

        elif isinstance(attr, Complex) and not attr.multi_valued:
            for sub_attr in attr.attrs:
                if sub_attr.mutability != AttributeMutability.READ_ONLY:
                    # non-read-only attributes can be updated
                    continue
                if attr_value[sub_attr.rep] is not Missing:
                    issues.add_error(
                        issue=ValidationError.attribute_can_not_be_modified(),
                        proceed=False,
                        location=(sub_attr.rep.sub_attr,),
                    )
        return issues

    def parse(self, data: Any) -> SCIMDataContainer:
        data = super().parse(data)
        ops = data.get(self.attrs.operations__op.rep)
        paths = data.get(self.attrs.operations__path.rep)
        values = data.get(self.attrs.operations__value.rep)
        parsed = []
        for i, (op, path, value) in enumerate(zip(ops, paths, values)):
            if op in ["add", "replace"]:
                parsed.append(
                    SCIMDataContainer(
                        {"op": op, "path": path, "value": self._parse_operation_value(path, value)}
                    )
                )
            else:
                parsed.append(SCIMDataContainer({"op": "remove", "path": path}))
        data.set(operations.rep, parsed)
        return data

    def _parse_operation_value(self, path: Optional[PatchPath], value: Any) -> Any:
        if path in [None, Missing]:
            return self._resource_schema.parse(value)

        # sub-attribute of filtered multivalued complex attribute
        if (
            isinstance(self._resource_schema.attrs.get(path.attr_rep), Complex)
            and path.complex_filter
            and path.complex_filter_attr_rep
        ):
            attr_rep = path.complex_filter_attr_rep
        else:
            attr_rep = path.attr_rep
        return self._resource_schema.attrs.get(attr_rep).parse(value)


def validate_operation_path(schema: ResourceSchema, path: PatchPath) -> ValidationIssues:
    issues = ValidationIssues()
    if schema.attrs.get(path.attr_rep) is None or (
        path.complex_filter_attr_rep is not None
        and schema.attrs.get(path.complex_filter_attr_rep) is None
    ):
        issues.add_error(
            issue=ValidationError.unknown_operation_target(),
            proceed=False,
        )
    return issues
