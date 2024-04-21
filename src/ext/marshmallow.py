from typing import Iterable

from marshmallow import Schema, fields, post_dump

from src.data.attributes import (
    Attribute,
    AttributeReturn,
    Binary,
    Boolean,
    Complex,
    DateTime,
    Decimal,
    ExternalReference,
    Integer,
    SCIMReference,
    String,
    Unknown,
    URIReference,
)
from src.request_validator import Validator


def _get_fields(attrs: Iterable[Attribute]) -> dict[str, fields.Field]:
    fields_ = {}
    for attr in attrs:
        field = _get_field(attr, **_get_kwargs(attr))
        if attr.multi_valued:
            field = fields.List(field)
        fields_[attr.rep.attr] = field
    return fields_


def _get_field(attr, **kwargs):
    if isinstance(attr, Unknown):
        field = fields.Raw(**kwargs)
    elif isinstance(attr, Boolean):
        field = fields.Boolean(**kwargs)
    elif isinstance(attr, Integer):
        field = fields.Integer(**kwargs)
    elif isinstance(attr, Decimal):
        field = fields.Float(**kwargs)
    elif isinstance(attr, DateTime):
        field = fields.DateTime(**kwargs)
    elif isinstance(attr, Binary):
        field = fields.String(**kwargs)
    elif isinstance(attr, ExternalReference):
        field = fields.String(**kwargs)
    elif isinstance(attr, URIReference):
        field = fields.String(**kwargs)
    elif isinstance(attr, SCIMReference):
        field = fields.String(**kwargs)
    elif isinstance(attr, String):
        field = fields.String(**kwargs)
    elif isinstance(attr, Complex):
        field = fields.Nested(_get_fields(attr.attrs))
    else:
        raise RuntimeError(f"unknown attr type {attr.type}")
    return field


def _get_kwargs(attr: Attribute):
    return {"required": attr.returned == AttributeReturn.ALWAYS}


def _apply_validator_on_schema(schema, validator: Validator):
    def _post_serialize(self, data, **kwargs):
        context_ = {k: v() if callable(v) else v for k, v in self.context.items()}
        issues = validator.validate_response(
            status_code=context_.get("status_code"),
            body=data,
            headers=context_.get("headers", {}),
            **context_,
        )
        return data

    class_ = type(
        schema.__name__, (schema,), {"_post_serialize": post_dump(_post_serialize, pass_many=False)}
    )
    return class_


def response_serializeer(validator: Validator):
    pyscim_schema = validator.response_schema
    base_fields = _get_fields(pyscim_schema.attrs.base_top_level)
    extension_fields = {
        extension_name: fields.Nested(_get_fields(attrs))
        for extension_name, attrs in pyscim_schema.attrs.extensions.items()
    }
    schema = Schema.from_dict(
        fields={**base_fields, **extension_fields},
        name=pyscim_schema.__class__.__name__,
    )
    return _apply_validator_on_schema(schema, validator)
