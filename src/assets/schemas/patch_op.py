from typing import Any, Optional, Union

from src.container import Invalid, Missing, SCIMDataContainer
from src.data.attr_presence import validate_presence
from src.data.attrs import AttributeMutability, Complex, String, Unknown
from src.data.patch_path import PatchPath
from src.data.schemas import BaseSchema, ResourceSchema
from src.error import ValidationError, ValidationIssues


def _validate_operations(value: list[SCIMDataContainer]) -> ValidationIssues:
    issues = ValidationIssues()
    for i, item in enumerate(value):
        type_ = item.get("op")
        path = item.get("path")
        op_value = item.get("value")
        if type_ == "remove" and path in [None, Missing]:
            issues.add_error(
                issue=ValidationError.missing(),
                proceed=False,
                location=(i, "path"),
            )
        elif type_ == "add":
            if op_value in [None, Missing]:
                issues.add_error(
                    issue=ValidationError.missing(),
                    proceed=False,
                    location=(i, "value"),
                )
    return issues


class PatchOp(BaseSchema):
    def __init__(self, resource_schema: ResourceSchema):
        super().__init__(
            schema="urn:ietf:params:scim:api:messages:2.0:PatchOp",
            attrs=[
                Complex(
                    sub_attributes=[
                        String(
                            "op",
                            canonical_values=["add", "remove", "replace"],
                            restrict_canonical_values=True,
                            required=True,
                        ),
                        String(
                            "path",
                            validators=[PatchPath.validate],
                            deserializer=PatchPath.deserialize,
                        ),
                        Unknown("value"),
                    ],
                    name="Operations",
                    required=True,
                    multi_valued=True,
                    validators=[_validate_operations],
                )
            ],
        )
        self._resource_schema = resource_schema

    def _validate(self, data: SCIMDataContainer, **kwargs) -> ValidationIssues:
        issues = ValidationIssues()
        ops = data.get(self.attrs.operations__op)
        paths = data.get(self.attrs.operations__path)
        values = data.get(self.attrs.operations__value)

        if not all([ops, paths, values]):
            return issues

        for i, (op, path, value) in enumerate(zip(ops, paths, values)):
            if Invalid in (op, path, value):
                continue

            if path is not Missing:
                path = PatchPath.deserialize(path)
            if op in ["add", "replace"]:
                issues.merge(
                    issues=self._validate_add_or_replace_operation(path, value),
                    location=(self.attrs.operations.attr, i),
                )
            else:
                issues.merge(
                    issues=self._validate_remove_operation(path),
                    location=(self.attrs.operations.attr, i),
                )

        return issues

    def _validate_remove_operation(self, path: PatchPath) -> ValidationIssues:
        issues = ValidationIssues()
        if (issues_ := validate_operation_path(self._resource_schema, path)).has_errors():
            issues.merge(issues_, location=(self.attrs.operations__path.sub_attr,))
            return issues

        attr = self._resource_schema.attrs.get(path.attr_rep)
        path_location = (self.attrs.operations__path.sub_attr,)
        if path.sub_attr_name is None:
            if attr.mutability == AttributeMutability.READ_ONLY:
                issues.add_error(
                    issue=ValidationError.attribute_can_not_be_modified(),
                    proceed=True,
                    location=path_location,
                )
            if attr.required:
                issues.add_error(
                    issue=ValidationError.attribute_can_not_be_deleted(),
                    proceed=True,
                    location=path_location,
                )
        else:
            sub_attr = self._resource_schema.attrs.get_by_path(path)
            if sub_attr.required and not sub_attr.multi_valued:
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
                issues.merge(issues_, location=[self.attrs.operations__path.sub_attr])
                return issues

        issues.merge(
            issues=self._validate_operation_value(path, value),
            location=[self.attrs.operations__value.sub_attr],
        )
        return issues

    def _validate_operation_value(self, path: Optional[PatchPath], value: Any) -> ValidationIssues:
        if path in [None, Missing]:
            issues = self._resource_schema.validate(value)
            issues.pop_errors([27, 28, 29], ("schemas",))
            for attr_rep, attr in self._resource_schema.attrs:
                attr_value = value.get(attr_rep)
                if attr_value is Missing:
                    continue

                if attr.mutability == AttributeMutability.READ_ONLY:
                    issues.add_error(
                        issue=ValidationError.attribute_can_not_be_modified(),
                        proceed=False,
                        location=attr_rep.location,
                    )
                    continue

                if not isinstance(attr, Complex):
                    continue

                sub_attr_err = False
                attr_location = attr_rep.location
                for sub_attr_name, sub_attr in attr.attrs:
                    if (
                        sub_attr.mutability == AttributeMutability.READ_ONLY
                        and attr_value is not Invalid
                        and attr_value.get(sub_attr_name) is not Missing
                    ):
                        issues.add_error(
                            issue=ValidationError.attribute_can_not_be_modified(),
                            proceed=False,
                            location=(*attr_location, sub_attr_name),
                        )
                        sub_attr_err = True

                if not sub_attr_err:
                    issues.merge(
                        self._validate_complex_sub_attrs_presence(attr, attr_value),
                        location=attr_location,
                    )
            return issues
        return self._validate_update_attr_value(value, path)

    def _validate_update_attr_value(self, attr_value: Any, path: PatchPath) -> ValidationIssues:
        issues = ValidationIssues()
        attr = self._resource_schema.attrs.get_by_path(path)
        if attr.mutability == AttributeMutability.READ_ONLY:
            issues.add_error(
                issue=ValidationError.attribute_can_not_be_modified(),
                proceed=False,
            )
            return issues

        # e.g. emails[value ew '.com']
        updating_multivalued_items = (
            path.has_filter and not path.sub_attr_name and not isinstance(attr_value, list)
        )

        if updating_multivalued_items:
            issues_ = attr.validate([attr_value])
        else:
            issues_ = attr.validate(attr_value)
        issues.merge(issues_)

        if not issues_.can_proceed() or not isinstance(attr, Complex):
            return issues

        can_validate_presence = True
        if updating_multivalued_items or not attr.multi_valued:
            for sub_attr_name, sub_attr in attr.attrs:
                if sub_attr.mutability != AttributeMutability.READ_ONLY:
                    # non-read-only attributes can be updated
                    continue
                if attr_value.get(sub_attr_name) is not Missing:
                    issues.add_error(
                        issue=ValidationError.attribute_can_not_be_modified(),
                        proceed=False,
                        location=[sub_attr_name],
                    )
                    can_validate_presence = False

        if not updating_multivalued_items and can_validate_presence:
            issues.merge(
                PatchOp._validate_complex_sub_attrs_presence(attr, attr_value),
            )
        return issues

    @staticmethod
    def _validate_complex_sub_attrs_presence(attr: Complex, value: Any) -> ValidationIssues:
        issues = ValidationIssues()
        for sub_attr_name, sub_attr in attr.attrs:
            if attr.multi_valued:
                for i, item in enumerate(value):
                    issues.merge(
                        validate_presence(
                            attr=sub_attr,
                            value=item.get(sub_attr_name),
                            direction="REQUEST",
                            inclusivity="INCLUDE",
                        ),
                        location=(i, sub_attr_name),
                    )
                continue
            issues.merge(
                validate_presence(
                    attr=sub_attr,
                    value=value.get(sub_attr_name),
                    direction="REQUEST",
                    inclusivity="INCLUDE",
                ),
                location=[sub_attr_name],
            )
        return issues

    def deserialize(self, data: Any) -> SCIMDataContainer:
        data = super().deserialize(data)
        ops = data.get(self.attrs.operations__op)
        paths = data.get(self.attrs.operations__path)
        values = data.get(self.attrs.operations__value)
        deserialized = []
        for i, (op, path, value) in enumerate(zip(ops, paths, values)):
            if op in ["add", "replace"]:
                deserialized.append(
                    SCIMDataContainer(
                        {
                            "op": op,
                            "path": path,
                            "value": self._deserialize_operation_value(path, value),
                        }
                    )
                )
            else:
                deserialized.append(SCIMDataContainer({"op": "remove", "path": path}))
        data.set(self.attrs.operations, deserialized)
        return data

    def _deserialize_operation_value(self, path: Optional[PatchPath], value: Any) -> Any:
        if path in [None, Missing]:
            return self._resource_schema.deserialize(value)
        attr = self._resource_schema.attrs.get_by_path(path)
        if path.has_filter and not path.sub_attr_name and not isinstance(value, list):
            return attr.deserialize([value])[0]
        return attr.deserialize(value)


def validate_operation_path(schema: ResourceSchema, path: PatchPath) -> ValidationIssues:
    issues = ValidationIssues()
    if schema.attrs.get_by_path(path) is None:
        issues.add_error(
            issue=ValidationError.unknown_modification_target(),
            proceed=False,
        )
    return issues
