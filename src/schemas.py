import abc
from copy import deepcopy
from typing import Dict, Iterable, List, Optional, Tuple, Union

from src.attributes import common as common_attrs
from src.attributes.attributes import Attribute, AttributeName, ComplexAttribute


class Schema(abc.ABC):
    def __init__(self, schema: str, repr_: str, attrs: Iterable[Attribute]):
        self._top_level_attr_names: List[AttributeName] = []
        self._attr_names: List[AttributeName] = []
        self._attrs: Dict[Tuple[str, str, str], Attribute] = {}
        for attr in [common_attrs.schemas, *attrs]:
            attr = self._bound_attr_to_schema(schema, attr)
            self._attrs[schema, attr.name.attr, attr.name.sub_attr] = attr
            self._attr_names.append(attr.name)
            self._top_level_attr_names.append(attr.name)
            if isinstance(attr, ComplexAttribute):
                for sub_attr in attr.sub_attributes:
                    self._attrs[schema, sub_attr.name.attr, sub_attr.name.sub_attr] = sub_attr
                    self._attr_names.append(
                        AttributeName(schema, sub_attr.name.attr, sub_attr.name.sub_attr)
                    )
        self._repr = repr_
        self._schema = schema

    @staticmethod
    def _bound_attr_to_schema(schema: str, attr: Attribute) -> Attribute:
        if isinstance(attr, ComplexAttribute):
            return ComplexAttribute(
                sub_attributes=attr.sub_attributes,
                name=AttributeName(schema=schema, attr=attr.name.attr),
                required=attr.required,
                issuer=attr.issuer,
                multi_valued=attr.multi_valued,
                mutability=attr.mutability,
                returned=attr.returned,
                uniqueness=attr.uniqueness,
                parsers=attr.parsers,
                dumpers=attr.dumpers,
                complex_parsers=attr.complex_parsers,
                complex_dumpers=attr.complex_dumpers,
            )
        return Attribute(
            name=AttributeName(schema=schema, attr=attr.name.attr, sub_attr=attr.name.sub_attr),
            type_=attr.type,
            reference_types=attr.reference_types,
            issuer=attr.issuer,
            required=attr.required,
            case_exact=attr.case_exact,
            multi_valued=attr.multi_valued,
            canonical_values=attr.canonical_values,
            mutability=attr.mutability,
            returned=attr.returned,
            uniqueness=attr.uniqueness,
            parsers=attr.parsers,
            dumpers=attr.dumpers,
        )

    @property
    def attrs(self) -> List[Attribute]:
        return list(self._attrs.values())

    @property
    def top_level_attr_names(self) -> List[AttributeName]:
        return self._top_level_attr_names

    @property
    def all_attr_names(self) -> List[AttributeName]:
        return self._attr_names

    @property
    def schemas(self) -> List[str]:
        return [self._schema]

    @property
    def schema(self) -> str:
        return self._schema

    def __repr__(self) -> str:
        return self._repr

    def get_attr(self, attr_name: AttributeName) -> Optional[Union[Attribute, ComplexAttribute]]:
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

    @property
    def schema_extensions(self) -> List[str]:
        return list(self._schema_extensions)

    def with_extension(
        self, extension: "SchemaExtension", required: bool = False
    ) -> "ResourceSchema":
        if extension.schema in self._schema_extensions:
            raise ValueError(f"extension {extension!r} already in {self!r} schema")

        copy = deepcopy(self)
        copy._schema_extensions[extension.schema] = required
        for attr in extension.attrs:
            attr = self._bound_attr_to_schema(extension.schema, attr)
            copy._attrs[extension.schema, attr.name.attr, ""] = attr
            copy._attr_names.append(attr.name)
            copy._top_level_attr_names.append(attr.name)
            if isinstance(attr, ComplexAttribute):
                for sub_attr in attr.sub_attributes:
                    copy._attrs[
                        (extension.schema, sub_attr.name.attr, sub_attr.name.sub_attr)
                    ] = sub_attr
                    copy._attr_names.append(
                        AttributeName(extension.schema, sub_attr.name.attr, sub_attr.name.sub_attr)
                    )
        return copy


class SchemaExtension:
    def __init__(self, schema: str, attrs: Iterable[Attribute]):
        self._schema = schema.lower()
        self._attrs = list(attrs)

    @property
    def schema(self) -> str:
        return self._schema

    @property
    def attrs(self) -> List[Attribute]:
        return self._attrs
