import abc
from copy import deepcopy
from typing import Dict, Iterable, List, Optional, Tuple, Union

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
        self._attrs: Dict[Tuple[str, str, str], Attribute] = {}
        for attr in [common_attrs.schemas, *attrs]:
            attr_name = AttributeName(schema, attr.name)
            self._attrs[schema, attr.name, ""] = attr
            self._attr_names.append(attr_name)
            self._top_level_attr_names.append(attr_name)
            if isinstance(attr, ComplexAttribute):
                for sub_attr_name, sub_attr in attr.sub_attributes.items():
                    self._attrs[schema, attr.name, sub_attr_name] = sub_attr
                    self._attr_names.append(AttributeName(schema, attr.name, sub_attr_name))
        self._repr = repr_
        self._schema = schema

    @property
    def top_level_attr_names(self) -> List[AttributeName]:
        return self._top_level_attr_names

    @property
    def all_attr_names(self) -> List[AttributeName]:
        return self._attr_names

    @property
    def schemas(self) -> List[str]:
        return [self._schema]

    def __repr__(self) -> str:
        return self._repr

    def get_attr_name(self, attr: Attribute):
        for (schema, attr_name, sub_attr_name), attr_obj in self._attrs.items():
            if attr_obj == attr:
                return AttributeName(schema, attr_name, sub_attr_name)
        raise ValueError(f"no attribute {attr} in schema")

    def get_attr(
        self,
        attr_name: AttributeName,
    ) -> Optional[Union[Attribute, ComplexAttribute]]:
        if (
            attr_name.schema
            and attr_name.schema not in self.schemas
            or attr_name not in self._attr_names
        ):
            return None

        for (schema, attr, sub_attr), attr_obj in self._attrs.items():
            if AttributeName(schema, attr, sub_attr) == attr_name:
                return attr_obj

        return None


class ResourceSchema(Schema, abc.ABC):
    def __init__(self, schema: str, repr_: str, attrs: Iterable[Attribute]):
        super().__init__(
            schema=schema,
            repr_=repr_,
            attrs=[
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
            copy._attrs[extension.schema, attr.name, ""] = attr
            copy._attr_names.append(attr_name)
            copy._top_level_attr_names.append(attr_name)
            if isinstance(attr, ComplexAttribute):
                for sub_attr_name, sub_attr in attr.sub_attributes.items():
                    copy._attrs[(extension.schema, attr.name, sub_attr_name)] = sub_attr
                    copy._attr_names.append(
                        AttributeName(extension.schema, attr.name, sub_attr_name)
                    )
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
        query_result_attrs.total_results,
        query_result_attrs.start_index,
        query_result_attrs.items_per_page,
    ],
)

ERROR = Schema(
    schema="urn:ietf:params:scim:api:messages:2.0:error",
    repr_="Error",
    attrs=[
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
