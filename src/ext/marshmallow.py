from typing import Any, Dict, Iterable, Optional

from marshmallow import Schema, fields, post_dump

from src.data import type as type_
from src.data.attributes import Attribute, AttributeReturn, ComplexAttribute
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
    if attr.type == type_.Unknown:
        field = fields.Raw(**kwargs)
    elif attr.type == type_.Boolean:
        field = fields.Boolean(**kwargs)
    elif attr.type == type_.Integer:
        field = fields.Integer(**kwargs)
    elif attr.type == type_.Decimal:
        field = fields.Float(**kwargs)
    elif attr.type == type_.String:
        field = fields.String(**kwargs)
    elif attr.type == type_.DateTime:
        field = fields.DateTime(**kwargs)
    elif attr.type == type_.Binary:
        field = fields.String(**kwargs)
    elif attr.type == type_.ExternalReference:
        field = fields.Url(absolute=True, **kwargs)
    elif attr.type == type_.URIReference:
        field = fields.String(**kwargs)
    elif attr.type == type_.SCIMReference:
        field = fields.String(**kwargs)
    elif attr.type == type_.Complex:
        attr: ComplexAttribute
        field = fields.Nested(_get_fields(attr.attrs))
    else:
        raise RuntimeError(f"unknown attr type {attr.type}")
    return field


def _get_kwargs(attr: Attribute):
    return {"required": attr.returned == AttributeReturn.ALWAYS}


def _apply_validator_on_schema(schema, validator: Validator):
    def _post_dump(self, data, **kwargs):
        context_ = {k: v() if callable(v) else v for k, v in self.context.items()}
        issues = validator.validate_response(
            status_code=context_.get("status_code"),
            body=data,
            headers=context_.get("headers", {}),
            **context_,
        )
        return data

    class_ = type(
        schema.__name__, (schema,), {"_post_dump": post_dump(_post_dump, pass_many=False)}
    )
    return class_


def response_dumper(validator: Validator):
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
