from typing import Any, List, Optional, Union

from src.attributes import Attribute, AttributeMutability, Complex, String, Unknown
from src.container import BoundedAttrRep, Invalid, Missing, SCIMDataContainer
from src.error import ValidationError, ValidationIssues
from src.path import PatchPath
from src.schemas import BaseSchema, ResourceSchema


def validate_operations(value: List[SCIMDataContainer]) -> ValidationIssues:
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


def deserialize_operations(value: List[SCIMDataContainer]) -> List[SCIMDataContainer]:
    for i, item in enumerate(value):
        if item == "remove":
            item.pop("value")
    return value


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
                    validators=[validate_operations],
                    deserializer=deserialize_operations,
                )
            ],
        )
        self._resource_schema = resource_schema

    def _validate(self, data: SCIMDataContainer) -> ValidationIssues:
        issues = ValidationIssues()
        ops = data.get(self.attrs.operations__op.rep)
        paths = data.get(self.attrs.operations__path.rep)
        values = data.get(self.attrs.operations__value.rep)

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
        if path.sub_attr_rep is None:
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
            sub_attr = self._resource_schema.attrs.get(
                BoundedAttrRep(
                    schema=path.attr_rep.schema,
                    attr=path.attr_rep.attr,
                    sub_attr=path.sub_attr_rep.attr,
                )
            )
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
                location = (attr.rep.attr,)
                attr_value = value.get(attr.rep)
                if attr_value is Missing:
                    continue

                if attr.mutability == AttributeMutability.READ_ONLY:
                    if attr.rep.extension:
                        location = (attr.rep.schema,) + location
                    issues.add_error(
                        issue=ValidationError.attribute_can_not_be_modified(),
                        proceed=False,
                        location=location,
                    )

                elif not isinstance(attr, Complex):
                    continue

                for sub_attr in attr.attrs:
                    if (
                        sub_attr.mutability == AttributeMutability.READ_ONLY
                        and attr_value.get(sub_attr.rep) is not Missing
                    ):
                        location = location + (sub_attr.rep.attr,)
                        if attr.rep.extension:
                            location = (attr.rep.schema,) + location
                        issues.add_error(
                            issue=ValidationError.attribute_can_not_be_modified(),
                            proceed=False,
                            location=location,
                        )
            return issues

        attr = self._resource_schema.attrs.get_by_path(path)
        if attr is None:
            return ValidationIssues()
        return self._validate_update_attr_value(attr, value, path)

    @staticmethod
    def _validate_update_attr_value(
        attr: Attribute, attr_value: Any, path: PatchPath
    ) -> ValidationIssues:
        issues = ValidationIssues()
        if attr.mutability == AttributeMutability.READ_ONLY:
            issues.add_error(
                issue=ValidationError.attribute_can_not_be_modified(),
                proceed=False,
            )
            return issues

        # e.g. emails[value ew '.com']
        updating_multivalued_items = (
            path.has_filter and not path.sub_attr_rep and not isinstance(attr_value, List)
        )

        if updating_multivalued_items:
            issues_ = attr.validate([attr_value])
        else:
            issues_ = attr.validate(attr_value)
        issues.merge(issues_)
        if not issues_.can_proceed():
            return issues

        if isinstance(attr, Complex) and (updating_multivalued_items or not attr.multi_valued):
            for sub_attr in attr.attrs:
                if sub_attr.mutability != AttributeMutability.READ_ONLY:
                    # non-read-only attributes can be updated
                    continue
                if attr_value[sub_attr.rep] is not Missing:
                    issues.add_error(
                        issue=ValidationError.attribute_can_not_be_modified(),
                        proceed=False,
                        location=(sub_attr.rep.attr,),
                    )
        return issues

    def deserialize(self, data: Any) -> SCIMDataContainer:
        data = super().deserialize(data)
        ops = data.get(self.attrs.operations__op.rep)
        paths = data.get(self.attrs.operations__path.rep)
        values = data.get(self.attrs.operations__value.rep)
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
        data.set(self.attrs.operations.rep, deserialized)
        return data

    def _deserialize_operation_value(self, path: Optional[PatchPath], value: Any) -> Any:
        if path in [None, Missing]:
            return self._resource_schema.deserialize(value)

        attr = self._resource_schema.attrs.get(path.attr_rep)

        if isinstance(attr, Complex) and path.sub_attr_rep:
            return attr.attrs.get(path.sub_attr_rep).deserialize(value)

        if path.has_filter and not path.sub_attr_rep and not isinstance(value, List):
            return attr.deserialize([value])[0]

        return attr.deserialize(value)


def validate_operation_path(schema: ResourceSchema, path: PatchPath) -> ValidationIssues:
    issues = ValidationIssues()
    if schema.attrs.get_by_path(path) is None:
        issues.add_error(
            issue=ValidationError.unknown_operation_target(),
            proceed=False,
        )
    return issues
