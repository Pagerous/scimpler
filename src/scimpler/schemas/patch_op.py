from copy import copy
from typing import Any, Optional, Union, cast

from scimpler.data.attr_presence import validate_presence
from scimpler.data.attrs import Attribute, AttributeMutability, Complex, String, Unknown
from scimpler.data.patch_path import PatchPath
from scimpler.data.schemas import BaseSchema, ResourceSchema
from scimpler.data.scim_data import Invalid, Missing, MissingType, SCIMData
from scimpler.error import ValidationError, ValidationIssues


def _validate_operations(value: list[SCIMData]) -> ValidationIssues:
    issues = ValidationIssues()
    for i, item in enumerate(value):
        type_ = item.get("op")
        path = item.get("path")
        op_value = item.get("value")
        if type_ == "remove" and path in [None, Missing]:
            issues.add_error(
                issue=ValidationError.missing(),
                proceed=False,
                location=[i, "path"],
            )
        elif type_ == "add":
            if op_value in [None, Missing]:
                issues.add_error(
                    issue=ValidationError.missing(),
                    proceed=False,
                    location=[i, "value"],
                )
    return issues


class PatchOpSchema(BaseSchema):
    schema = "urn:ietf:params:scim:api:messages:2.0:PatchOp"
    base_attrs: list[Attribute] = [
        Complex(
            name="Operations",
            required=True,
            multi_valued=True,
            validators=[_validate_operations],
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
                    serializer=lambda path: path.serialize(),
                ),
                Unknown("value"),
            ],
        )
    ]

    def __init__(self, resource_schema: ResourceSchema):
        super().__init__()
        self._resource_schema = resource_schema

    @property
    def resource_schema(self) -> ResourceSchema:
        return self._resource_schema

    def _validate(self, data: SCIMData, **kwargs) -> ValidationIssues:
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
        attr = self._resource_schema.attrs.get_by_path(path)
        if attr is None:
            issues.add_error(
                issue=ValidationError.unknown_modification_target(),
                proceed=False,
                location=[self.attrs.operations__path.sub_attr],
            )
            return issues

        path_location = [self.attrs.operations__path.sub_attr]
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
            parent_attr = cast(Attribute, self._resource_schema.attrs.get(path.attr_rep))
            if attr.required and not attr.multi_valued:
                issues.add_error(
                    issue=ValidationError.attribute_can_not_be_deleted(),
                    proceed=True,
                    location=path_location,
                )
            if (
                parent_attr.mutability == AttributeMutability.READ_ONLY
                or attr.mutability == AttributeMutability.READ_ONLY
            ):
                issues.add_error(
                    issue=ValidationError.attribute_can_not_be_modified(),
                    proceed=True,
                    location=path_location,
                )

        return issues

    def _validate_add_or_replace_operation(
        self, path: Union[PatchPath, None, MissingType], value: Any
    ) -> ValidationIssues:
        issues = ValidationIssues()
        attr = None

        if isinstance(path, PatchPath):
            attr = self._resource_schema.attrs.get_by_path(path)
            if attr is None:
                issues.add_error(
                    issue=ValidationError.unknown_modification_target(),
                    proceed=False,
                    location=[self.attrs.operations__path.sub_attr],
                )
                return issues

        issues.merge(
            issues=self._validate_operation_value(attr, path, value),
            location=[self.attrs.operations__value.sub_attr],
        )
        return issues

    def _validate_operation_value(
        self, attr: Optional[Attribute], path: Union[PatchPath, None, MissingType], value: Any
    ) -> ValidationIssues:
        if not isinstance(path, PatchPath):
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
        return self._validate_update_attr_value(cast(Attribute, attr), value, path)

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
                PatchOpSchema._validate_complex_sub_attrs_presence(attr, attr_value),
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

    def _serialize(self, data: SCIMData) -> SCIMData:
        processed = []
        for operation in data.get(self.attrs.operations):
            op = operation.get("op")
            path = operation.get("path")
            value = operation.get("value")
            processed_operation = {"op": op}
            if op in ["add", "replace"] and value not in [None, Missing]:
                processed_operation["value"] = self._process_operation_value(
                    path=path,
                    value=value,
                    method="serialize",
                )
            if path:
                processed_operation["path"] = path

            processed.append(SCIMData(processed_operation))
        data.set(self.attrs.operations, processed)
        return data

    def _deserialize(self, data: SCIMData) -> SCIMData:
        ops = data.get(self.attrs.operations__op)
        paths = data.get(self.attrs.operations__path)
        values = data.get(self.attrs.operations__value)
        processed = []
        for op, path, value in zip(ops, paths, values):
            processed_operation = {"op": op}
            if op in ["add", "replace"]:
                if value in [None, Missing]:
                    processed_operation["value"] = None
                else:
                    processed_operation["value"] = self._process_operation_value(
                        path=path,
                        value=value,
                        method="deserialize",
                    )
            if path:
                processed_operation["path"] = path
            processed.append(SCIMData(processed_operation))
        data.set(self.attrs.operations, processed)
        return data

    def get_value_schema(
        self,
        path: Union[str, PatchPath, None, MissingType],
        value: Any,
    ) -> Union[BaseSchema, Attribute]:
        if not isinstance(path, (str, PatchPath)):
            return self._resource_schema

        if isinstance(path, str):
            path_normalized = PatchPath.deserialize(path)
        else:
            path_normalized = path

        attr = self._resource_schema.attrs.get_by_path(path_normalized)
        if attr is None:
            raise ValueError(f"target indicated by path {path!r} does not exist")

        if (
            path_normalized.has_filter
            and not path_normalized.sub_attr_name
            and not isinstance(value, list)
        ):
            attr = cast(Attribute, copy(attr))
            attr._multi_valued = False
            return attr
        return attr

    def _process_operation_value(
        self,
        path: Union[PatchPath, None, MissingType],
        value: Any,
        method: str,
    ) -> Any:
        return getattr(self.get_value_schema(path, value), method)(value)
