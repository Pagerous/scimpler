import abc
from copy import deepcopy
from typing import Dict, Iterable, List, Optional, Union

from src.parser.attributes import common as common_attrs
from src.parser.attributes import error as error_attrs
from src.parser.attributes import list_result as query_result_attrs
from src.parser.attributes import user as user_attrs
from src.parser.attributes import user_enterprise_extension as enterprise_attrs
from src.parser.attributes.attributes import Attribute, AttributeName, ComplexAttribute


class Schema(abc.ABC):
    def __init__(self, schema: str, repr_: str, attrs: Iterable[Attribute]):
        self._top_level_attr_names: List[AttributeName] = []
        self._attr_names: List[AttributeName] = []
        self._attrs = {}
        for attr in attrs:
            attr_name = AttributeName(schema, attr.name)
            self._top_level_attr_names.append(attr_name)
            self._attr_names.append(attr_name)
            if isinstance(attr, ComplexAttribute):
                self._attr_names.extend(
                    [AttributeName(schema, attr.name, sub_attr) for sub_attr in attr.sub_attributes]
                )
            self._attrs[attr.name] = attr

        self._repr = repr_
        self._schema = schema

    @property
    def top_level_attr_names(self) -> List[AttributeName]:
        return self._top_level_attr_names

    @property
    def attr_names(self) -> List[AttributeName]:
        return self._attr_names

    @property
    def schemas(self) -> List[str]:
        return [self._schema]

    def __repr__(self) -> str:
        return self._repr

    def get_attr(
        self,
        attr_name: AttributeName,
    ) -> Optional[Union[Attribute, ComplexAttribute]]:
        if attr_name.schema and attr_name.schema not in map(str.lower, self.schemas):
            return None
        if attr_name not in self._attr_names:
            return None
        attr = self._attrs[attr_name.attr]
        if isinstance(attr, ComplexAttribute) and attr_name.sub_attr:
            return attr.sub_attributes[attr_name.sub_attr]
        return attr


class ResourceSchema(Schema, abc.ABC):
    def __init__(self, schema: str, repr_: str, attrs: Iterable[Attribute]):
        super().__init__(
            schema=schema,
            repr_=repr_,
            attrs=[
                common_attrs.schemas,
                common_attrs.id_,
                common_attrs.external_id,
                common_attrs.meta,
                *attrs,
            ],
        )
        self._schema_extensions: Dict[str, bool] = {}

    @property
    def schemas(self) -> List[str]:
        return ["urn:ietf:params:scim:schemas:core:2.0:user"] + list(self._schema_extensions)

    def with_extension(
        self, extension: "SchemaExtension", required: bool = False
    ) -> "ResourceSchema":
        if extension.schema in self._schema_extensions:
            raise ValueError(f"extension {extension!r} already in {self!r} schema")

        copy = deepcopy(self)
        copy._schema_extensions[extension.schema] = required
        for attr in extension.attrs:
            attr_name = AttributeName(extension.schema, attr.name)
            copy._top_level_attr_names.append(attr_name)
            to_extend = [attr_name]
            if isinstance(attr, ComplexAttribute):
                to_extend += [
                    AttributeName(extension.schema, attr.name, sub_attr)
                    for sub_attr in attr.sub_attributes
                ]
            copy._attr_names.extend(to_extend)
        copy._attrs.update({attr.name: attr for attr in extension.attrs})
        return copy


class SchemaExtension:
    def __init__(self, schema: str, attrs: Iterable[Attribute]):
        self._schema = schema
        self._attrs = list(attrs)

    @property
    def schema(self) -> str:
        return self._schema

    @property
    def attrs(self) -> List[Attribute]:
        return self._attrs


LIST_RESPONSE = Schema(
    schema="urn:ietf:params:scim:api:messages:2.0:listresponse",
    repr_="ListResponse",
    attrs=[
        common_attrs.schemas,
        query_result_attrs.total_results,
        query_result_attrs.start_index,
        query_result_attrs.items_per_page,
    ],
)

ERROR = Schema(
    schema="urn:ietf:params:scim:api:messages:2.0:error",
    repr_="Error",
    attrs=[
        common_attrs.schemas,
        error_attrs.status,
        error_attrs.scim_type,
        error_attrs.detail,
    ],
)

USER_ENTERPRISE_EXTENSION = SchemaExtension(
    schema="urn:ietf:params:scim:schemas:extension:enterprise:2.0:user",
    attrs=[
        enterprise_attrs.employee_number,
        enterprise_attrs.cost_center,
        enterprise_attrs.division,
        enterprise_attrs.department,
        enterprise_attrs.organization,
        enterprise_attrs.manager,
    ],
)

USER = ResourceSchema(
    schema="urn:ietf:params:scim:schemas:core:2.0:user",
    repr_="User",
    attrs=[
        user_attrs.user_name,
        user_attrs.name,
        user_attrs.display_name,
        user_attrs.nick_name,
        user_attrs.profile_url,
        user_attrs.title,
        user_attrs.user_type,
        user_attrs.preferred_language,
        user_attrs.locale,
        user_attrs.timezone,
        user_attrs.active,
        user_attrs.password,
        user_attrs.emails,
        user_attrs.ims,
        user_attrs.photos,
        user_attrs.addresses,
        user_attrs.groups,
        user_attrs.entitlements,
        user_attrs.roles,
        user_attrs.x509_certificates,
    ],
).with_extension(USER_ENTERPRISE_EXTENSION, required=True)
