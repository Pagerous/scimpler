from typing import Iterable, Optional, cast

import marshmallow

from src.assets.schemas import ListResponse
from src.container import AttrName, BoundedAttrRep, AttrRep
from src.data import attrs
from src.data.schemas import BaseSchema, ResourceSchema
from src.request.validator import Validator


_marshmallow_field_by_attr_type: dict[type[attrs.Attribute], type[marshmallow.fields.Field]] = {}


def initialize(
    fields_by_attrs: Optional[dict[type[attrs.Attribute], type[marshmallow.fields.Field]]] = None,
):
    global _marshmallow_field_by_attr_type

    default = {
        attrs.Unknown: marshmallow.fields.Raw,
        attrs.Boolean: marshmallow.fields.Boolean,
        attrs.Integer: marshmallow.fields.Integer,
        attrs.Decimal: marshmallow.fields.Float,
        attrs.DateTime: marshmallow.fields.DateTime,
        attrs.Binary: marshmallow.fields.String,
        attrs.ExternalReference: marshmallow.fields.String,
        attrs.URIReference: marshmallow.fields.String,
        attrs.SCIMReference: marshmallow.fields.String,
        attrs.String: marshmallow.fields.String,
    }
    if fields_by_attrs is not None:
        default.update(fields_by_attrs)
    _marshmallow_field_by_attr_type = default


def _get_fields(
    attrs_: Iterable[tuple[BoundedAttrRep, attrs.Attribute]],
    field_by_attr_rep: Optional[dict[AttrRep, marshmallow.fields.Field]] = None,
) -> dict[str, marshmallow.fields.Field]:
    field_by_attr_rep = field_by_attr_rep or {}
    fields_: dict[str, marshmallow.fields.Field] = {}
    for attr_rep, attr in attrs_:
        if attr_rep in field_by_attr_rep:
            field = field_by_attr_rep[attr_rep]
        else:
            kwargs = _get_kwargs(attr)
            if attr.multi_valued:
                field = marshmallow.fields.List(_get_field(attr), **kwargs)
            else:
                field = _get_field(attr, **kwargs)
        fields_[str(attr_rep.attr)] = field
    return fields_


def _get_complex_sub_fields(
    attrs_: Iterable[tuple[AttrName, attrs.Attribute]],
    field_by_attr_name: Optional[dict[str, marshmallow.fields.Field]] = None,
) -> dict[str, marshmallow.fields.Field]:
    field_by_attr_name = field_by_attr_name or {}
    fields_: dict[str, marshmallow.fields.Field] = {}
    for name, attr in attrs_:
        if name in field_by_attr_name:
            field = field_by_attr_name[name]
        else:
            kwargs = _get_kwargs(attr)
            if attr.multi_valued:
                field = marshmallow.fields.List(_get_field(attr), **kwargs)
            else:
                field = _get_field(attr, **kwargs)
        fields_[str(name)] = field
    return fields_


def _get_field(attr, **kwargs):
    if isinstance(attr, attrs.Complex):
        return marshmallow.fields.Nested(_get_complex_sub_fields(attr.attrs))
    return _marshmallow_field_by_attr_type[type(attr)](**kwargs)


def _get_kwargs(attr: attrs.Attribute):
    return {"required": attr.returned == attrs.AttributeReturn.ALWAYS}


def _apply_validator_on_schema(schema, scimple_schema):
    marshmallow_schema_attrs = {}

    if isinstance(scimple_schema, ListResponse) and len(scimple_schema.contained_schemas) > 1:

        def _post_dump(self, data, **kwargs):
            serialized = []
            for resource in data.get("Resources", []):
                schema_uris = [
                    item.lower() for item in resource.get("schemas", []) if isinstance(item, str)
                ]
                for resource_schema in scimple_schema.contained_schemas:
                    if resource_schema.schema in schema_uris:
                        marshmallow_schema = _get_marshmallow_schema(resource_schema)()
                        serialized.append(marshmallow_schema.dump(resource))
            if serialized:
                data["Resources"] = serialized
            return data

        marshmallow_schema_attrs["_post_dump"] = marshmallow.post_dump(_post_dump, pass_many=False)

    if isinstance(scimple_schema, ResourceSchema):

        def _pre_dump(self, data, **kwargs):
            for extension_uri in scimple_schema.extensions:
                extension_uri_lower = extension_uri.lower()
                for k, v in data.copy().items():
                    if k.lower() == extension_uri_lower:
                        key_parts = k.split(".")
                        if len(key_parts) == 1:
                            continue

                        data[key_parts[0]] = _transform_extension_key_parts(
                            key_parts[1:], data.pop(k)
                        )
            return data

        marshmallow_schema_attrs["_pre_dump"] = marshmallow.pre_dump(_pre_dump)

    class_ = type(
        type(scimple_schema).__name__,
        (schema,),
        marshmallow_schema_attrs,
    )
    return class_


def _transform_extension_key_parts(keys, value):
    def insert(d, keys_, value_):
        key = keys_[0]
        if len(keys_) == 1:
            d[key] = value_
        else:
            if key not in d:
                d[key] = {}
            insert(d[key], keys_[1:], value_)

    result = {}
    insert(result, keys, value)
    return result


def _get_marshmallow_schema(scimple_schema: BaseSchema) -> type[marshmallow.Schema]:
    if isinstance(scimple_schema, ListResponse) and len(scimple_schema.contained_schemas) == 1:
        resources_attr = cast(attrs.Attribute, scimple_schema.attrs.get("resources"))
        fields = _get_fields(
            scimple_schema.attrs,
            field_by_attr_rep={
                scimple_schema.attrs.resources: marshmallow.fields.List(
                    marshmallow.fields.Nested(
                        _get_fields(scimple_schema.contained_schemas[0].attrs)
                    ),
                    **_get_kwargs(resources_attr),
                )
            },
        )
    else:
        fields = _get_fields(scimple_schema.attrs)

    if isinstance(scimple_schema, ResourceSchema):
        extension_fields = {}
        for extension_uri, attrs_ in scimple_schema.attrs.extensions.items():
            extension_fields[str(extension_uri)] = marshmallow.fields.Nested(
                _get_fields(attrs_)
            )
        fields.update(extension_fields)

    schema_cls = marshmallow.Schema.from_dict(fields={**fields})
    return cast(type[marshmallow.Schema], _apply_validator_on_schema(schema_cls, scimple_schema))


def response_serializer(validator: Validator):
    scimple_schema = validator.response_schema
    return _get_marshmallow_schema(scimple_schema)
