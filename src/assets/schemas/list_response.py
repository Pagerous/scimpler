from typing import Any, List, Optional, Sequence

from src.data.attributes import Integer, Unknown, get_scim_type
from src.data.container import Invalid, Missing, SCIMDataContainer
from src.data.schemas import BaseSchema, ResourceSchema
from src.error import ValidationError, ValidationIssues

total_results = Integer("totalResults", required=True)

start_index = Integer("startIndex")

items_per_page = Integer("itemsPerPage")


def validate_resources_type(value) -> ValidationIssues:
    issues = ValidationIssues()
    for i, item in enumerate(value):
        if not isinstance(item, SCIMDataContainer):
            issues.add_error(
                issue=ValidationError.bad_type(get_scim_type(dict), get_scim_type(type(value))),
                proceed=True,
                location=(i,),
            )
            value[0] = Invalid
    return issues


resources = Unknown(
    name="Resources",
    multi_valued=True,
    validators=[validate_resources_type],
)


class ListResponse(BaseSchema):
    def __init__(self, schemas: Sequence[BaseSchema]):
        super().__init__(
            schema="urn:ietf:params:scim:api:messages:2.0:ListResponse",
            attrs=[
                total_results,
                start_index,
                items_per_page,
                resources,
            ],
        )
        self._schemas = schemas

    @property
    def schemas(self) -> Sequence[BaseSchema]:
        return self._schemas

    def _validate(self, data: SCIMDataContainer) -> ValidationIssues:
        issues = ValidationIssues()
        resources_ = data.get(self.attrs.resources.rep)
        if resources_ is Missing:
            return issues

        if not isinstance(resources_, List):
            issues.add_error(
                issue=ValidationError.bad_type(
                    get_scim_type(list), get_scim_type(type(resources_))
                ),
                location=(self.attrs.resources.rep.attr,),
                proceed=False,
            )
            return issues

        if (items_per_page_ := data.get(self.attrs.itemsperpage.rep)) is not Invalid:
            issues.merge(
                validate_items_per_page_consistency(
                    resources_=resources_,
                    items_per_page_=items_per_page_,
                )
            )

        schemas_ = self.get_schemas_for_resources(resources_)
        for i, (resource, schema) in enumerate(zip(resources_, schemas_)):
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

    def serialize(self, data: Any) -> SCIMDataContainer:
        data = super().serialize(data)
        resources_ = data.get(self.attrs.resources.rep)
        if resources_ is Missing:
            return data
        schemas_ = self.get_schemas_for_resources(resources_)
        serialized_resources = []
        for i, (resource, schema) in enumerate(zip(resources_, schemas_)):
            serialized_resources.append(schema.serialize(resource))
        data.set(self.attrs.resources.rep, serialized_resources)
        return data

    def get_schemas_for_resources(self, resources_: List[Any]) -> List[Optional[ResourceSchema]]:
        schemas_ = []
        n_schemas = len(self._schemas)
        for resource in resources_:
            if n_schemas == 1:
                schemas_.append(self._schemas[0])
            else:
                schemas_.append(self._infer_schema_from_data(resource))
        return schemas_

    def _infer_schema_from_data(self, data: Any) -> Optional[BaseSchema]:
        if not isinstance(data, SCIMDataContainer):
            return None

        schemas_value = data.get(self.attrs.schemas.rep)
        if isinstance(schemas_value, List) and len(schemas_value) > 0:
            schemas_value = {
                item.lower() if isinstance(item, str) else item for item in schemas_value
            }
            for schema in self._schemas:
                if not schemas_value.difference({s.lower() for s in schema.schemas}):
                    return schema
        return None


def validate_items_per_page_consistency(
    resources_: List[Any], items_per_page_: Any
) -> ValidationIssues:
    issues = ValidationIssues()
    if not isinstance(items_per_page_, int):
        return issues

    n_resources = len(resources_)
    if items_per_page_ != n_resources:
        issues.add_error(
            issue=ValidationError.must_be_equal_to(value="number of resources"),
            location=(items_per_page.rep.attr,),
            proceed=True,
        )
        issues.add_error(
            issue=ValidationError.must_be_equal_to(items_per_page.rep.attr),
            location=(resources.rep.attr,),
            proceed=True,
        )
    return issues
