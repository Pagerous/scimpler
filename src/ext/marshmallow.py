from dataclasses import dataclass
from typing import Any, Callable, Iterable, Optional, Protocol, Union, cast

import marshmallow

from src.assets.schemas import BulkResponse, ListResponse, PatchOp
from src.container import AttrName, AttrRep, BoundedAttrRep, SCIMDataContainer
from src.data import attrs
from src.data.patch_path import PatchPath
from src.data.schemas import BaseSchema, ResourceSchema
from src.registry import resources
from src.request.validator import BulkOperations, Error, Validator

_marshmallow_field_by_attr_type: dict[type[attrs.Attribute], type[marshmallow.fields.Field]] = {}


@dataclass
class Processors:
    validator: Optional[Callable] = None


class RequestContext:
    def __init__(
        self,
        query_string: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, Any]] = None,
    ) -> None:
        self._query_string = query_string or {}
        self._headers = headers or {}

    @property
    def query_string(self) -> dict[str, Any]:
        return self._query_string

    @property
    def headers(self) -> dict[str, Any]:
        return self._headers


class RequestContextProvider(Protocol):
    def __call__(self) -> RequestContext: ...


class ResponseContext:
    def __init__(
        self, status_code: int, headers: Optional[dict[str, Any]] | None = None, **kwargs: Any
    ) -> None:
        self._status_code = status_code
        self._headers = headers or {}
        self._kwargs = kwargs

    @property
    def status_code(self) -> int:
        return self._status_code

    @property
    def headers(self) -> dict[str, Any]:
        return self._headers

    @property
    def kwargs(self) -> dict[str, Any]:
        return self._kwargs


class ResponseContextProvider(Protocol):
    def __call__(self) -> ResponseContext: ...


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
            if attr.has_custom_processing:
                field = marshmallow.fields.Raw
            else:
                field = _get_field(attr)
            if attr.multi_valued:
                field = marshmallow.fields.List(field)
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
            if attr.has_custom_processing:
                field = marshmallow.fields.Raw()
            else:
                field = _get_field(attr)
            if attr.multi_valued:
                field = marshmallow.fields.List(field)
        fields_[str(name)] = field
    return fields_


def _get_field(attr, **kwargs):
    if isinstance(attr, attrs.Complex):
        return marshmallow.fields.Nested(_get_complex_sub_fields(attr.attrs))
    return _marshmallow_field_by_attr_type[type(attr)](**kwargs)


def _transform_errors_dict(input_dict):
    output_dict = {}
    for key, value in input_dict.items():
        if isinstance(value, dict):
            transformed_value = _transform_errors_dict(value)
            if "_errors" in transformed_value and len(transformed_value) == 1:
                output_dict[key] = [error["error"] for error in transformed_value["_errors"]]
            else:
                output_dict[key] = transformed_value
        else:
            output_dict[key] = value
    return output_dict


def _validate_response(data: dict, response_validator: Callable, context: ResponseContext) -> None:
    issues = response_validator(
        status_code=context.status_code,
        body=data,
        headers=context.headers,
        **context.kwargs,
    )
    if issues.has_errors():
        raise marshmallow.ValidationError(
            message=_transform_errors_dict(issues.to_dict(msg=True)),
        )


def _validate_request(data: dict, request_validator: Callable, context: RequestContext) -> None:
    issues = request_validator(
        body=data,
        headers=context.headers,
        query_string=context.query_string,
    )
    if issues.has_errors():
        raise marshmallow.ValidationError(
            message=_transform_errors_dict(issues.to_dict(msg=True)),
        )


def _get_list_response_response_processors(
    scimple_schema: ListResponse,
    processors: Processors,
    context_provider: Optional[ResponseContextProvider],
):
    processors_ = {}

    def deserialize(data):
        resources_ = data.pop("Resources", [])
        deserialized = scimple_schema.deserialize(data)
        deserialized_resources = []
        for resource in resources_:
            schema_uris = [
                item.lower() for item in resource.get("schemas", []) if isinstance(item, str)
            ]
            for resource_schema in scimple_schema.contained_schemas:
                if resource_schema.schema in schema_uris:
                    marshmallow_schema = _create_schema(
                        scimple_schema=resource_schema,
                        processors=Processors(),
                        context_provider=None,
                        validator=None,
                    )()
                    deserialized_resources.append(marshmallow_schema.load(resource))
        if deserialized_resources:
            deserialized.set("Resources", deserialized_resources)
        return deserialized.to_dict()

    if processors.validator:

        def _pre_load(_, data, **__):
            if context_provider is None:
                raise ValueError("context must be provided when loading data")
            _validate_response(data, processors.validator, context_provider())
            return deserialize(data)
    else:

        def _pre_load(_, data, **__):
            return deserialize(data)

    def _post_load(_, data, **__):
        return SCIMDataContainer(data)

    def _pre_dump(_, data, **__):
        resources_ = data.pop("Resources") or []
        serialized = scimple_schema.serialize(data)
        serialized_resources = []
        for resource in resources_:
            resource_dict = resource.to_dict()
            schema_uris = [
                item.lower() for item in resource_dict.get("schemas", []) if isinstance(item, str)
            ]
            for resource_schema in scimple_schema.contained_schemas:
                if resource_schema.schema in schema_uris:
                    marshmallow_schema = _create_schema(
                        scimple_schema=resource_schema,
                        processors=Processors(),
                        context_provider=None,
                        validator=None,
                    )
                    serialized_resources.append(marshmallow_schema().dump(resource_dict))
        if serialized_resources:
            serialized["Resources"] = serialized_resources
        return serialized

    processors_["_pre_load"] = marshmallow.pre_load(_pre_load, pass_many=False)
    processors_["_post_load"] = marshmallow.post_load(_post_load)
    processors_["_pre_dump"] = marshmallow.pre_dump(_pre_dump, pass_many=False)

    return processors_


def _get_resource_response_processors(
    scimple_schema: ResourceSchema,
    processors: Processors,
    context_provider: Optional[Union[ResponseContextProvider, RequestContextProvider]],
):
    processors_ = {}

    def deserialize(data):
        return scimple_schema.deserialize(data).to_dict()

    if processors.validator:

        def _pre_load(_, data, **__):
            if context_provider is None:
                raise ValueError("context must be provided when loading data")
            context = context_provider()
            if isinstance(context, ResponseContext):
                _validate_response(data, processors.validator, context)
            else:
                _validate_request(data, processors.validator, context)
            return deserialize(data)
    else:

        def _pre_load(_, data, **__):
            return deserialize(data)

    def _post_load(_, data, original_data, **__):
        for extension_uri in scimple_schema.extensions:
            extension_uri_lower = extension_uri.lower()
            for k in original_data:
                if k.lower() == extension_uri_lower:
                    key_parts = k.split(".")
                    if len(key_parts) == 1:
                        continue
                    extension_data = data
                    for part in key_parts:
                        extension_data = extension_data[part]
                    data.pop(key_parts[0])
                    data[k] = extension_data
        return SCIMDataContainer(data)

    def _pre_dump(_, data, **__):
        serialized = scimple_schema.serialize(data)
        for extension_uri in scimple_schema.extensions:
            extension_uri_lower = extension_uri.lower()
            for k in serialized.copy():
                if k.lower() == extension_uri_lower:
                    key_parts = k.split(".")
                    if len(key_parts) == 1:
                        continue

                    serialized[key_parts[0]] = _transform_extension_key_parts(
                        key_parts[1:], serialized.pop(k)
                    )
        return serialized

    processors_["_pre_load"] = marshmallow.pre_load(_pre_load, pass_many=False)
    processors_["_post_load"] = marshmallow.post_load(_post_load, pass_original=True)
    processors_["_pre_dump"] = marshmallow.pre_dump(_pre_dump, pass_many=False)

    return processors_


def _get_patch_op_request_processors(
    scimple_schema: PatchOp,
    processors: Processors,
    context_provider: Optional[RequestContextProvider],
):
    processors_ = {}

    def deserialize(data):
        deserialized = scimple_schema.deserialize(data)
        for operation in deserialized.get("Operations") or []:
            path = operation.get("path")
            value = operation.get("value")
            resource_request_schema = _create_schema(
                scimple_schema=scimple_schema.resource_schema,
                processors=Processors(validator=None),
                context_provider=None,
                validator=None,
            )()

            if isinstance(value, SCIMDataContainer):
                value_ = value.to_dict()
            elif isinstance(value, list):
                value_ = [
                    item.to_dict() if isinstance(item, SCIMDataContainer) else item
                    for item in value
                ]
            else:
                value_ = value

            if isinstance(path, PatchPath):
                attr = scimple_schema.resource_schema.attrs.get_by_path(path)
                if attr is None:
                    raise ValueError(f"target indicated by path {path!r} does not exist")

                if not path.sub_attr_name:
                    if path.has_filter and not isinstance(value_, list):
                        operation.set(
                            "value",
                            resource_request_schema.fields[str(attr.name)].deserialize([value_])[0],
                        )
                    else:
                        operation.set(
                            "value",
                            resource_request_schema.fields[str(attr.name)].deserialize(value_),
                        )
                else:
                    parent_field = resource_request_schema.fields[str(path.attr_rep.attr)]
                    if not isinstance(parent_field, marshmallow.fields.Nested):
                        raise TypeError(f"{path.attr_rep} is not complex")

                    operation.set(
                        "value",
                        parent_field.nested[str(attr.name)].deserialize(value_),
                    )
            else:
                operation.set("value", resource_request_schema.load(value_))
        return deserialized.to_dict()

    if processors.validator:

        def _pre_load(_, data, **__):
            if context_provider is None:
                raise ValueError("context must be provided when loading data")
            _validate_request(data, processors.validator, context_provider())
            return deserialize(data)
    else:

        def _pre_load(_, data, **__):
            return deserialize(data)

    def _post_load(_, data, **__):
        return SCIMDataContainer(data)

    def _pre_dump(_, data, **__):
        serialized = scimple_schema.serialize(data)
        for operation in serialized.get("Operations", []):
            path_str = operation.get("path")
            value = operation.get("value")
            resource_request_schema = _create_schema(
                scimple_schema=scimple_schema.resource_schema,
                processors=Processors(validator=None),
                context_provider=None,
                validator=None,
            )()
            if isinstance(path_str, str):
                path = PatchPath.deserialize(path_str)
                attr = scimple_schema.resource_schema.attrs.get_by_path(path)
                if attr is None:
                    raise ValueError(f"target indicated by path {path!r} does not exist")

                if not path.sub_attr_name:
                    if path.has_filter and not isinstance(value, list):
                        operation["value"] = resource_request_schema.fields[
                            str(attr.name)
                        ].serialize(str(attr.name), {str(attr.name): [value]})[0]
                    else:
                        operation["value"] = resource_request_schema.fields[
                            str(attr.name)
                        ].serialize(str(attr.name), {str(attr.name): value})
                else:
                    parent_field = resource_request_schema.fields[str(path.attr_rep.attr)]
                    if not isinstance(parent_field, marshmallow.fields.Nested):
                        raise TypeError(f"{path.attr_rep} is not complex")

                    operation["value"] = parent_field.nested[str(attr.name)].serialize(
                        str(attr.name), {str(attr.name): value}
                    )
            else:
                operation["value"] = resource_request_schema.dump(value)
        return serialized

    processors_["_pre_load"] = marshmallow.pre_load(_pre_load, pass_many=False)
    processors_["_post_load"] = marshmallow.post_load(_post_load)
    processors_["_pre_dump"] = marshmallow.pre_dump(_pre_dump, pass_many=False)

    return processors_


def _get_bulk_response_response_processors(
    scimple_schema: BulkResponse,
    processors: Processors,
    context_provider: Optional[ResponseContextProvider],
    validator: BulkOperations,
):
    processors_ = {}

    def _get_operation_response_schema(operation: dict):
        status = int(operation["status"])
        if status >= 300:
            return _create_schema(
                scimple_schema=Error().response_schema,
                processors=Processors(validator=None),
                context_provider=None,
                validator=validator,
            )
        for resource_schema in resources.values():
            location = operation.get("location", "")
            if f"/{resource_schema.plural_name}/" in location:
                return _create_schema(
                    scimple_schema=(
                        validator.sub_validators[operation["method"].upper()][
                            resource_schema.plural_name
                        ].response_schema
                    ),
                    processors=Processors(validator=None),
                    context_provider=None,
                    validator=None,
                )
        raise marshmallow.ValidationError("unknown resource")

    def deserialize(data):
        deserialized = scimple_schema.deserialize(data)
        for operation in deserialized.get("Operations") or []:
            operation_dict = operation.to_dict()
            response_schema = _get_operation_response_schema(operation_dict)
            operation.set("response", response_schema().load(operation_dict.get("response", {})))
        return deserialized.to_dict()

    if processors.validator:

        def _pre_load(_, data, **__):
            if context_provider is None:
                raise ValueError("context must be provided when loading data")
            _validate_response(data, processors.validator, context_provider())
            return deserialize(data)
    else:

        def _pre_load(_, data, **__):
            return deserialize(data)

    def _post_load(_, data, **__):
        return SCIMDataContainer(data)

    def _pre_dump(_, data, **__):
        serialized = scimple_schema.serialize(data)
        for operation in serialized.get("Operations", []):
            response_schema = _get_operation_response_schema(operation)
            operation["response"] = response_schema().dump(operation.get("response"))
        return serialized

    processors_["_pre_load"] = marshmallow.pre_load(_pre_load, pass_many=False)
    processors_["_post_load"] = marshmallow.post_load(_post_load)
    processors_["_pre_dump"] = marshmallow.pre_dump(_pre_dump, pass_many=False)

    return processors_


def _get_generic_response_processors(
    scimple_schema: BaseSchema,
    processors: Processors,
    context_provider: Optional[ResponseContextProvider] = None,
):
    processors_ = {}

    def deserialize(data):
        return scimple_schema.deserialize(data).to_dict()

    if processors.validator:

        def _pre_load(_, data, **__):
            if context_provider is None:
                raise ValueError("context must be provided when loading data")
            _validate_response(data, processors.validator, context_provider())
            return deserialize(data)
    else:

        def _pre_load(_, data, **__):
            return deserialize(data)

    def _post_load(_, data, **__):
        return SCIMDataContainer(data)

    def _pre_dump(_, data, **__):
        return scimple_schema.serialize(data)

    processors_["_pre_load"] = marshmallow.pre_load(_pre_load, pass_many=False)
    processors_["_post_load"] = marshmallow.post_load(_post_load)
    processors_["_pre_dump"] = marshmallow.pre_dump(_pre_dump, pass_many=False)

    return processors_


def _include_processing_in_schema(
    schema_cls: type[marshmallow.Schema],
    scimple_schema: BaseSchema,
    processors: Processors,
    context_provider: Optional[Union[ResponseContextProvider, ResponseContextProvider]],
    validator: Optional[Validator],
) -> type[marshmallow.Schema]:
    if isinstance(scimple_schema, ListResponse):
        processors = _get_list_response_response_processors(
            scimple_schema=scimple_schema,
            processors=processors,
            context_provider=context_provider,
        )
    elif isinstance(scimple_schema, ResourceSchema):
        processors = _get_resource_response_processors(
            scimple_schema=scimple_schema,
            processors=processors,
            context_provider=context_provider,
        )
    elif isinstance(scimple_schema, BulkResponse) and isinstance(validator, BulkOperations):
        processors = _get_bulk_response_response_processors(
            scimple_schema=scimple_schema,
            processors=processors,
            context_provider=context_provider,
            validator=validator,
        )
    elif isinstance(scimple_schema, PatchOp):
        processors = _get_patch_op_request_processors(
            scimple_schema=scimple_schema,
            processors=processors,
            context_provider=context_provider,
        )
    else:
        processors = _get_generic_response_processors(
            scimple_schema=scimple_schema,
            processors=processors,
            context_provider=context_provider,
        )
    class_ = type(
        type(scimple_schema).__name__,
        (schema_cls,),
        processors,
    )
    return cast(type[marshmallow.Schema], class_)


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


def _create_schema(
    scimple_schema: BaseSchema,
    processors: Processors,
    context_provider: Optional[ResponseContextProvider],
    validator: Optional[Validator],
) -> type[marshmallow.Schema]:
    if isinstance(scimple_schema, ListResponse) and len(scimple_schema.contained_schemas) == 1:
        fields = _get_fields(
            scimple_schema.attrs,
            field_by_attr_rep={
                scimple_schema.attrs.resources: marshmallow.fields.List(
                    marshmallow.fields.Nested(
                        _get_fields(scimple_schema.contained_schemas[0].attrs)
                    ),
                )
            },
        )
    else:
        fields = _get_fields(scimple_schema.attrs)

    if isinstance(scimple_schema, ResourceSchema):
        extension_fields = {}
        for extension_uri, attrs_ in scimple_schema.attrs.extensions.items():
            extension_fields[str(extension_uri)] = marshmallow.fields.Nested(_get_fields(attrs_))
        fields.update(extension_fields)

    schema_cls = cast(type[marshmallow.Schema], marshmallow.Schema.from_dict(fields={**fields}))
    return _include_processing_in_schema(
        schema_cls=schema_cls,
        processors=processors,
        scimple_schema=scimple_schema,
        context_provider=context_provider,
        validator=validator,
    )


def create_response_schema(
    validator: Validator,
    context_provider: Optional[ResponseContextProvider] = None,
) -> type[marshmallow.Schema]:
    return _create_schema(
        scimple_schema=validator.response_schema,
        processors=Processors(validator=validator.validate_response),
        context_provider=context_provider,
        validator=validator,
    )


def create_request_schema(
    validator: Validator,
    context_provider: Optional[RequestContextProvider] = None,
) -> type[marshmallow.Schema]:
    return _create_schema(
        scimple_schema=validator.request_schema,
        processors=Processors(validator=validator.validate_request),
        context_provider=context_provider,
        validator=validator,
    )
