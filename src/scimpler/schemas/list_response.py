from typing import Any, Iterable, Mapping, Optional, Union

from scimpler.data.attr_presence import AttrPresenceConfig
from scimpler.data.attrs import Attribute, Integer, Unknown
from scimpler.data.schemas import BaseResourceSchema, BaseSchema
from scimpler.data.scim_data import Invalid, Missing, ScimData
from scimpler.error import ValidationError, ValidationIssues


def _validate_resources_type(value) -> ValidationIssues:
    issues = ValidationIssues()
    for i, item in enumerate(value):
        if not isinstance(item, ScimData):
            issues.add_error(
                issue=ValidationError.bad_type("complex"),
                proceed=True,
                location=[i],
            )
            value[i] = Invalid
    return issues


class ListResponseSchema(BaseSchema):
    """
    ListResponse schema, identified by `urn:ietf:params:scim:api:messages:2.0:ListResponse` URI.

    Provides data validation and checks if:

    - `itemsPerPage` is consistent with number of `Resources`,
    - `Resources` contains known resources,
    - `Resources` contains valid resources that correspond to the known schemas.
    """

    schema = "urn:ietf:params:scim:api:messages:2.0:ListResponse"
    base_attrs: list[Attribute] = [
        Integer("totalResults", required=True),
        Integer("startIndex"),
        Integer("itemsPerPage"),
        Unknown(
            name="Resources",
            multi_valued=True,
            validators=[_validate_resources_type],
        ),
    ]

    def __init__(self, resource_schemas: Iterable[BaseResourceSchema]):
        """
        Args:
            resource_schemas: Resource schemas supported by the list response.

        Examples:
             >>> from scimpler.schemas import UserSchema, GroupSchema
             >>>
             >>> list_response = ListResponseSchema([UserSchema(), GroupSchema()])
        """
        super().__init__()
        self._contained_schemas = list(resource_schemas)

    @property
    def supported_schemas(self) -> list[BaseResourceSchema]:
        """
        Resource schemas supported by the list response.
        """
        return self._contained_schemas

    def _validate(self, data: ScimData, **kwargs) -> ValidationIssues:
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

        resource_schemas = self.get_schemas(resources)
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

    def _deserialize(self, data: ScimData) -> ScimData:
        resources = data.pop(self.attrs.resources)
        deserialized = self._process_resources(resources, "deserialize")
        if deserialized:
            data.set(self.attrs.resources, deserialized)
        return data

    def _serialize(self, data: ScimData) -> ScimData:
        resources = data.pop(self.attrs.resources)
        serialized = self._process_resources(resources, "serialize")
        if serialized:
            data.set(self.attrs.resources, serialized)
        return data

    def _process_resources(self, resources: list[Any], method: str) -> list[dict[str, Any]]:
        if not isinstance(resources, list):
            return []
        schemas = self.get_schemas(resources)
        serialized_resources: list[dict[str, Any]] = []
        for i, (resource, schema) in enumerate(zip(resources, schemas)):
            if schema is None:
                serialized_resources.append({})
            else:
                serialized_resources.append(getattr(schema, method)(resource))
        return serialized_resources

    def get_schemas(self, resources: list[Any]) -> list[Optional[BaseResourceSchema]]:
        """
        Returns schemas for corresponding items in the provided `resources`. Returns `None`
        for the particular item if its schema is not supported by the list response.

        Args:
            resources: Resources data to get the schemas for.

        Examples:
            >>> from scimpler.schemas import UserSchema
            >>>
            >>> user = UserSchema()
            >>> list_response = ListResponseSchema([user])
            >>> list_response.get_schemas(
            >>>     [
            >>>         {
            >>>             "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"]
            >>>             "id": "1",
            >>>             "userName": "Pagerous",
            >>>         },
            >>>         {
            >>>             "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"]
            >>>             "id": "2",
            >>>             "name": "GitHub Users",
            >>>         }
            >>>     ]
            >>> )
            [<scimpler.schemas.user.UserSchema at 0x7f1f6c193090>, None]
        """
        resource_schemas: list[Optional[BaseResourceSchema]] = []
        n_schemas = len(self._contained_schemas)
        for resource in resources:
            if isinstance(resource, Mapping):
                resource = ScimData(resource)
            if not isinstance(resource, ScimData):
                resource_schemas.append(None)
            elif n_schemas == 1:
                resource_schemas.append(self._contained_schemas[0])
            else:
                resource_schemas.append(self.get_schema(resource))
        return resource_schemas

    def get_schema(self, resource: Mapping) -> Optional[BaseResourceSchema]:
        """
        Returns a schema for the provided `resource`. Returns `None` if the schema
        in `resource` is not supported by the list response.

        Args:
            resource: Resource data to get the schema for.
        """
        resource = ScimData(resource)
        schemas_value = resource.get("schemas")
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
