from typing import Any, Optional, Sequence

from src.container import Invalid, Missing, SCIMDataContainer
from src.data.attributes import Integer, Unknown
from src.error import ValidationError, ValidationIssues
from src.schemas import BaseSchema, ResourceSchema


def _validate_resources_type(value) -> ValidationIssues:
    issues = ValidationIssues()
    for i, item in enumerate(value):
        if not isinstance(item, SCIMDataContainer):
            issues.add_error(
                issue=ValidationError.bad_type("complex"),
                proceed=True,
                location=(i,),
            )
            value[0] = Invalid
    return issues


class ListResponse(BaseSchema):
    def __init__(self, schemas: Sequence[BaseSchema]):
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
        self._contained_schemas = list(schemas)

    @property
    def contained_schemas(self) -> list[BaseSchema]:
        return self._contained_schemas

    def _validate(self, data: SCIMDataContainer) -> ValidationIssues:
        issues = ValidationIssues()

        resources = data.get(self.attrs.resources.rep)
        if resources in [Missing, Invalid]:
            return issues

        if (items_per_page_ := data.get(self.attrs.itemsperpage.rep)) is not Invalid:
            issues.merge(
                validate_items_per_page_consistency(
                    resources_=resources,
                    items_per_page_=items_per_page_,
                )
            )

        schemas = self.get_schemas_for_resources(resources)
        for i, (resource, schema) in enumerate(zip(resources, schemas)):
            if schema is None:
                issues.add_error(
                    issue=ValidationError.unknown_schema(),
                    proceed=False,
                    location=(self.attrs.resources.rep.attr, i),
                )
            elif resource is not Invalid:
                issues.merge(
                    issues=schema.validate(resource),
                    location=(self.attrs.resources.rep.attr, i),
                )
        return issues

    def _serialize(self, data: SCIMDataContainer) -> SCIMDataContainer:
        resources = data.get(self.attrs.resources.rep)
        if resources is Missing or not isinstance(resources, list):
            return data

        schemas = self.get_schemas_for_resources(resources)
        serialized_resources = []
        for i, (resource, schema) in enumerate(zip(resources, schemas)):
            if schema is None:
                serialized_resources.append({})
            else:
                serialized_resources.append(schema.serialize(resource))
        data.set(self.attrs.resources.rep, serialized_resources)
        return data

    def get_schemas_for_resources(
        self,
        resources: list[Any],
    ) -> list[Optional[ResourceSchema]]:
        schemas = []
        n_schemas = len(self._contained_schemas)
        for resource in resources:
            if not isinstance(resource, SCIMDataContainer):
                schemas.append(None)
            elif n_schemas == 1:
                schemas.append(self._contained_schemas[0])
            else:
                schemas.append(self._infer_schema_from_data(resource))
        return schemas

    def _infer_schema_from_data(self, data: SCIMDataContainer) -> Optional[BaseSchema]:
        schemas_value = data.get(self.attrs.schemas.rep)
        if isinstance(schemas_value, list) and len(schemas_value) > 0:
            schemas_value = {
                item.lower() if isinstance(item, str) else item for item in schemas_value
            }
            for schema in self._contained_schemas:
                if not schemas_value.difference({s.lower() for s in schema.schemas}):
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
            location=("itemsPerPage",),
            proceed=True,
        )
        issues.add_error(
            issue=ValidationError.must_be_equal_to("itemsPerPage"),
            location=("Resources",),
            proceed=True,
        )
    return issues
