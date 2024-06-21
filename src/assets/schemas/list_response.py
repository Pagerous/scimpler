from typing import Any, Optional, Sequence, Union

from src.container import Invalid, Missing, SCIMDataContainer
from src.data.attr_presence import AttrPresenceConfig
from src.data.attrs import Integer, Unknown
from src.data.schemas import BaseResourceSchema, BaseSchema
from src.error import ValidationError, ValidationIssues


def _validate_resources_type(value) -> ValidationIssues:
    issues = ValidationIssues()
    for i, item in enumerate(value):
        if not isinstance(item, SCIMDataContainer):
            issues.add_error(
                issue=ValidationError.bad_type("complex"),
                proceed=True,
                location=[i],
            )
            value[i] = Invalid
    return issues


class ListResponse(BaseSchema):
    def __init__(self, resource_schemas: Sequence[BaseResourceSchema]):
        super().__init__(
            schema="urn:ietf:params:scim:api:messages:2.0:ListResponse",
            attrs=[
                Integer("totalResults", required=True),
                Integer("startIndex"),
                Integer("itemsPerPage"),
                Unknown(
                    name="Resources",
                    multi_valued=True,
                    validators=[_validate_resources_type],
                ),
            ],
        )
        self._contained_schemas = list(resource_schemas)

    @property
    def contained_schemas(self) -> list[BaseResourceSchema]:
        return self._contained_schemas

    def _validate(self, data: SCIMDataContainer, **kwargs) -> ValidationIssues:
        issues = ValidationIssues()

        resources_rep = self.attrs.resources
        resources = data.get(resources_rep)
        if resources in [Missing, Invalid]:
            return issues

        if (items_per_page_ := data.get(self.attrs.itemsperpage)) is not Invalid:
            issues.merge(
                validate_items_per_page_consistency(
                    resources_=resources,
                    items_per_page_=items_per_page_,
                )
            )

        resource_presence_config = kwargs.get("resource_presence_config")
        if resource_presence_config is None:
            resource_presence_config = AttrPresenceConfig("RESPONSE")

        resource_schemas = self.get_schemas_for_resources(resources)
        for i, (resource, schema) in enumerate(zip(resources, resource_schemas)):
            if resource is Invalid:
                continue

            resource_location: tuple[Union[str, int], ...] = (*resources_rep.location, i)
            if schema is None:
                issues.add_error(
                    issue=ValidationError.unknown_schema(),
                    proceed=False,
                    location=resource_location,
                )
                continue

            issues.merge(
                issues=schema.validate(resource, resource_presence_config),
                location=resource_location,
            )
        return issues

    def _deserialize(self, data: SCIMDataContainer) -> SCIMDataContainer:
        resources = data.pop(self.attrs.resources)
        deserialized = self._process_resources(resources, "deserialize")
        if deserialized:
            data.set(self.attrs.resources, deserialized)
        return data

    def _serialize(self, data: SCIMDataContainer) -> SCIMDataContainer:
        resources = data.pop(self.attrs.resources)
        serialized = self._process_resources(resources, "serialize")
        if serialized:
            data.set(self.attrs.resources, serialized)
        return data

    def _process_resources(self, resources: list[Any], method: str) -> list[dict[str, Any]]:
        if not isinstance(resources, list):
            return []
        schemas = self.get_schemas_for_resources(resources)
        serialized_resources: list[dict[str, Any]] = []
        for i, (resource, schema) in enumerate(zip(resources, schemas)):
            if schema is None:
                serialized_resources.append({})
            else:
                serialized_resources.append(getattr(schema, method)(resource))
        return serialized_resources

    def get_schemas_for_resources(
        self,
        resources: list[Any],
    ) -> list[Optional[BaseResourceSchema]]:
        resource_schemas: list[Optional[BaseResourceSchema]] = []
        n_schemas = len(self._contained_schemas)
        for resource in resources:
            if isinstance(resource, dict):
                resource = SCIMDataContainer(resource)
            if not isinstance(resource, SCIMDataContainer):
                resource_schemas.append(None)
            elif n_schemas == 1:
                resource_schemas.append(self._contained_schemas[0])
            else:
                resource_schemas.append(self._infer_schema_from_data(resource))
        return resource_schemas

    def _infer_schema_from_data(self, data: SCIMDataContainer) -> Optional[BaseResourceSchema]:
        schemas_value = data.get("schemas")
        if isinstance(schemas_value, list) and len(schemas_value) > 0:
            schemas_value = {
                item.lower() if isinstance(item, str) else item for item in schemas_value
            }
            for schema in self._contained_schemas:
                if schema.schema in schemas_value:
                    return schema
        return None


def validate_items_per_page_consistency(
    resources_: list[Any], items_per_page_: Any
) -> ValidationIssues:
    issues = ValidationIssues()
    if not isinstance(items_per_page_, int):
        return issues

    n_resources = len(resources_)
    if items_per_page_ != n_resources:
        issues.add_error(
            issue=ValidationError.must_be_equal_to(value="number of resources"),
            location=["itemsPerPage"],
            proceed=True,
        )
        issues.add_error(
            issue=ValidationError.must_be_equal_to("itemsPerPage"),
            location=["Resources"],
            proceed=True,
        )
    return issues
