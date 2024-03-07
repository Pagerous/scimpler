from typing import Any, List, Optional, Sequence, Tuple, Union

from src.data import type as type_
from src.data.attributes import Attribute
from src.data.container import Invalid, Missing, SCIMDataContainer
from src.data.type import get_scim_type
from src.error import ValidationError, ValidationIssues
from src.schemas import BaseSchema, ResourceSchema

total_results = Attribute(
    name="totalResults",
    type_=type_.Integer,
    required=True,
)

start_index = Attribute(
    name="startIndex",
    type_=type_.Integer,
)

items_per_page = Attribute(
    name="itemsPerPage",
    type_=type_.Integer,
)

resources = Attribute(
    name="Resources",
    type_=type_.Unknown,
)


class ListResponse(BaseSchema):
    def __init__(self, resource_schemas: Sequence[ResourceSchema]):
        super().__init__(
            schema="urn:ietf:params:scim:api:messages:2.0:ListResponse",
            attrs=[
                total_results,
                start_index,
                items_per_page,
                resources,
            ],
        )
        self._resource_schemas = resource_schemas

    def __repr__(self) -> str:
        return "ListResponse"

    def dump(self, data: Any) -> Tuple[Union[Invalid, SCIMDataContainer], ValidationIssues]:
        data, issues = super().dump(data)
        if not issues.can_proceed():
            return data, issues

        resources_ = data[self.attrs.resources.rep]
        if resources_ is Missing:
            return data, issues

        if not (resources_ is Missing or isinstance(resources_, List)):
            issues.add(
                issue=ValidationError.bad_type(
                    get_scim_type(list), get_scim_type(type(resources_))
                ),
                location=(self.attrs.resources.rep.attr,),
                proceed=False,
            )
            return data, issues

        if issues.can_proceed((self.attrs.itemsperpage.rep.attr,)):
            items_per_page_ = data[self.attrs.itemsperpage.rep]
            issues.merge(
                validate_items_per_page_consistency(
                    resources_=resources_,
                    items_per_page_=items_per_page_,
                )
            )

        schemas_ = self.get_schemas_for_resources(resources_)

        dumped_resources = []
        for i, (resource, schema) in enumerate(zip(resources_, schemas_)):
            if schema is None:
                issues.add(
                    issue=ValidationError.unknown_schema(),
                    proceed=False,
                    location=(self.attrs.resources.rep.attr, i),
                )
                resource = Invalid
            else:
                resource, issues_ = schema.dump(resource)
                issues.merge(issues_, location=(self.attrs.resources.rep.attr, i))
            dumped_resources.append(resource)
        data[self.attrs.resources.rep] = dumped_resources

        return data, issues

    def get_schemas_for_resources(self, resources_: List[Any]) -> List[Optional[ResourceSchema]]:
        schemas_ = []
        n_schemas = len(self._resource_schemas)
        for resource in resources_:
            if n_schemas == 1:
                schemas_.append(self._resource_schemas[0])
            else:
                schemas_.append(self._infer_schema_from_data(resource))
        return schemas_

    def _infer_schema_from_data(self, data: Any) -> Optional[BaseSchema]:
        if not isinstance(data, SCIMDataContainer):
            return None

        schemas_value = data[self.attrs.schemas.rep]
        if isinstance(schemas_value, List) and len(schemas_value) > 0:
            schemas_value = {
                item.lower() if isinstance(item, str) else item for item in schemas_value
            }
            for schema in self._resource_schemas:
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
        issues.add(
            issue=ValidationError.must_be_equal_to(value="number of resources"),
            location=(items_per_page.rep.attr,),
            proceed=True,
        )
        issues.add(
            issue=ValidationError.must_be_equal_to(items_per_page.rep.attr),
            location=(resources.rep.attr,),
            proceed=True,
        )
    return issues
