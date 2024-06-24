from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Optional, Protocol, Union, cast

import marshmallow

from src.assets.schemas import BulkRequest, BulkResponse, ListResponse, PatchOp
from src.container import AttrName, AttrRep, BoundedAttrRep, Missing, SCIMData
from src.data import attrs
from src.data.attrs import Attribute
from src.data.schemas import BaseSchema, ResourceSchema
from src.request.validator import BulkOperations, Validator

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
            field = _get_field(attr)
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
            field = _get_field(attr)
        fields_[str(name)] = field
    return fields_


def _get_field(attr):
    if attr.has_custom_processing:
        field = marshmallow.fields.Raw()
    else:
        if isinstance(attr, attrs.Complex):
            field = _get_nested_field(_get_complex_sub_fields(attr.attrs))
        else:
            field = _marshmallow_field_by_attr_type[type(attr)]()
    if attr.multi_valued:
        field = marshmallow.fields.List(field)
    return field


def _get_nested_field(*args, **kwargs):
    field = marshmallow.fields.Nested(*args, **kwargs)
    field.get_attribute = _get_field_value
    return field


def _get_field_value(_, obj, key, default):
    return obj.get(key) or default


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


def _get_list_response_processors(
    scimple_schema: ListResponse,
    processors: Processors,
    context_provider: Optional[ResponseContextProvider],
):
    processors_ = {}

    def deserialize(data):
        resources = data.pop("Resources", [])
        deserialized = scimple_schema.deserialize(data)
        deserialized_resources = []
        for resource in resources:
            resource_schema = scimple_schema.get_schema(SCIMData(resource))
            if resource_schema is None:
                deserialized_resource = SCIMData()
            else:
                deserialized_resource = _create_schema(
                    scimple_schema=resource_schema,
                    processors=Processors(),
                    context_provider=None,
                    validator=None,
                )().load(resource)
            deserialized_resources.append(deserialized_resource)
        if deserialized_resources:
            deserialized.set("Resources", deserialized_resources)
        return deserialized

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
        return SCIMData(data)

    def _pre_dump(_, data, **__):
        resources_ = data.pop("Resources") or []
        serialized = scimple_schema.serialize(data)
        serialized_resources = []
        for resource in resources_:
            resource_schema = scimple_schema.get_schema(resource)
            if resource_schema is None:
                serialized_resource = {}
            else:
                serialized_resource = _create_schema(
                    scimple_schema=resource_schema,
                    processors=Processors(),
                    context_provider=None,
                    validator=None,
                )().dump(resource.to_dict())
            serialized_resources.append(serialized_resource)
        if serialized_resources:
            serialized["Resources"] = serialized_resources
        return serialized

    processors_["_pre_load"] = marshmallow.pre_load(_pre_load, pass_many=False)
    processors_["_post_load"] = marshmallow.post_load(_post_load)
    processors_["_pre_dump"] = marshmallow.pre_dump(_pre_dump, pass_many=False)
    return processors_


def _get_resource_processors(
    scimple_schema: ResourceSchema,
    processors: Processors,
    context_provider: Optional[Union[ResponseContextProvider, RequestContextProvider]],
):
    processors_ = {}

    def deserialize(data):
        return scimple_schema.deserialize(data)

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
        return SCIMData(data)

    def _pre_dump(_, data, **__):
        return scimple_schema.serialize(data)

    processors_["_pre_load"] = marshmallow.pre_load(_pre_load)
    processors_["_post_load"] = marshmallow.post_load(_post_load, pass_original=True)
    processors_["_pre_dump"] = marshmallow.pre_dump(_pre_dump)

    return processors_


def _get_patch_op_processors(
    scimple_schema: PatchOp,
    processors: Processors,
    context_provider: Optional[RequestContextProvider],
):
    processors_ = {}

    def deserialize(data):
        values = [operation.pop("value", Missing) for operation in data.get("Operations", [])]
        deserialized = scimple_schema.deserialize(data)
        for operation, value in zip(deserialized.get("Operations") or [], values):
            if value is Missing:
                continue
            value_schema = _create_schema(
                scimple_schema=scimple_schema.get_value_schema(
                    path=operation.get("path"),
                    value=value,
                ),
                processors=Processors(validator=None),
                context_provider=None,
                validator=None,
            )
            operation.set("value", value_schema().load(value))
        return deserialized

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
        return SCIMData(data)

    def _pre_dump(_, data, **__):
        values = [operation.pop("value") for operation in data.get("Operations") or []]
        serialized = scimple_schema.serialize(data)
        for operation, value in zip(serialized.get("Operations", []), values):
            if value in [None, Missing]:
                continue
            value_schema = _create_schema(
                scimple_schema=scimple_schema.get_value_schema(
                    path=operation.get("path"),
                    value=value,
                ),
                processors=Processors(validator=None),
                context_provider=None,
                validator=None,
            )
            operation["value"] = value_schema().dump(value)
        return serialized

    processors_["_pre_load"] = marshmallow.pre_load(_pre_load)
    processors_["_post_load"] = marshmallow.post_load(_post_load)
    processors_["_pre_dump"] = marshmallow.pre_dump(_pre_dump)

    return processors_


def _get_bulk_response_processors(
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
                scimple_schema=validator.error_validator.response_schema,
                processors=Processors(validator=None),
                context_provider=None,
                validator=None,
            )
        location = operation.get("location", "")
        for resource_name, sub_validator in validator.sub_validators[
            operation["method"].upper()
        ].items():
            if f"/{resource_name}/" in location:
                return _create_schema(
                    scimple_schema=sub_validator.response_schema,
                    processors=Processors(validator=None),
                    context_provider=None,
                    validator=None,
                )
        raise marshmallow.ValidationError("unknown resource")

    def deserialize(data):
        responses = [operation.pop("response") for operation in data.get("Operations", [])]
        deserialized = scimple_schema.deserialize(data)
        for operation, response in zip(deserialized.get("Operations") or [], responses):
            if response:
                response_schema = _get_operation_response_schema(operation)
                operation.set("response", response_schema().load(response))
        return deserialized

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
        return SCIMData(data)

    def _pre_dump(_, data, **__):
        responses = [operation.pop("response") for operation in data.get("Operations") or []]
        serialized = scimple_schema.serialize(data)
        for operation, response in zip(serialized.get("Operations", []), responses):
            if response:
                response_schema = _get_operation_response_schema(operation)
                operation["response"] = response_schema().dump(response)
        return serialized

    processors_["_pre_load"] = marshmallow.pre_load(_pre_load)
    processors_["_post_load"] = marshmallow.post_load(_post_load)
    processors_["_pre_dump"] = marshmallow.pre_dump(_pre_dump)

    return processors_


def _get_bulk_request_processors(
    scimple_schema: BulkRequest,
    processors: Processors,
    context_provider: Optional[Union[ResponseContextProvider, RequestContextProvider]],
    validator: BulkOperations,
):
    processors_ = {}

    def _get_operation_request_schema(operation: dict):
        method = operation["method"].upper()
        if method == "POST":
            path_parts = operation.get("path", "").split("/", 1)
        else:
            path_parts = operation.get("path", "").split("/", 2)

        if len(path_parts) < 2:
            raise marshmallow.ValidationError(f"invalid path {operation['path']!r}")

        resource_name = path_parts[1]
        sub_validator = validator.sub_validators.get(method, {}).get(resource_name)
        if sub_validator is None:
            raise marshmallow.ValidationError("unknown resource")
        return _create_schema(
            scimple_schema=sub_validator.request_schema,
            processors=Processors(validator=None),
            context_provider=None,
            validator=None,
        )

    def deserialize(data):
        deserialized = scimple_schema.deserialize(data)
        for operation in deserialized.get("Operations") or []:
            operation_dict = operation
            data = operation_dict.get("data")
            if data:
                request_schema = _get_operation_request_schema(operation_dict)
                operation.set("data", request_schema().load(data))
        return deserialized

    if processors.validator:

        def _pre_load(_, data, **__):
            if context_provider is None:
                raise ValueError("context must be provided when loading data")
            context = context_provider()
            if isinstance(context, RequestContext):
                _validate_request(data, processors.validator, context)
            else:
                raise NotImplementedError
            return deserialize(data)
    else:

        def _pre_load(_, data, **__):
            return deserialize(data)

    def _post_load(_, data, **__):
        return SCIMData(data)

    def _pre_dump(_, data, **__):
        operation_data = [operation.pop("data") for operation in data.get("Operations") or []]
        serialized = scimple_schema.serialize(data)
        for operation, data_item in zip(serialized.get("Operations", []), operation_data):
            if data_item:
                request_schema = _get_operation_request_schema(operation)
                operation["data"] = request_schema().dump(data_item)
        return serialized

    processors_["_pre_load"] = marshmallow.pre_load(_pre_load)
    processors_["_post_load"] = marshmallow.post_load(_post_load)
    processors_["_pre_dump"] = marshmallow.pre_dump(_pre_dump)

    return processors_


def _get_generic_processors(
    scimple_schema: BaseSchema,
    processors: Processors,
    context_provider: Optional[Union[ResponseContextProvider, RequestContextProvider]] = None,
):
    processors_ = {}

    def deserialize(data):
        return scimple_schema.deserialize(data)

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

    def _post_load(_, data, **__):
        return SCIMData(data)

    def _pre_dump(_, data, **__):
        return scimple_schema.serialize(data)

    processors_["_pre_load"] = marshmallow.pre_load(_pre_load)
    processors_["_post_load"] = marshmallow.post_load(_post_load)
    processors_["_pre_dump"] = marshmallow.pre_dump(_pre_dump)

    return processors_


def _get_generic_attr_processors(
    scimple_schema: Attribute,
):
    processors_ = {}

    def _pre_load(_, data, **__):
        return {str(scimple_schema.name): scimple_schema.deserialize(data)}

    def _post_load(_, data, **__):
        data = data.get(str(scimple_schema.name))
        if data is None:
            return data
        if isinstance(data, Mapping):
            return SCIMData(data)
        if isinstance(data, list):
            return [SCIMData(item) if isinstance(item, Mapping) else item for item in data]
        return data

    def _pre_dump(_, data, **__):
        return {str(scimple_schema.name): scimple_schema.serialize(data)}

    def _post_dump(_, data, **__):
        return data.get(str(scimple_schema.name))

    processors_["_pre_load"] = marshmallow.pre_load(_pre_load)
    processors_["_post_load"] = marshmallow.post_load(_post_load)
    processors_["_pre_dump"] = marshmallow.pre_dump(_pre_dump)
    processors_["_post_dump"] = marshmallow.post_dump(_post_dump)

    return processors_


def _include_processing_in_schema(
    schema_cls: type[marshmallow.Schema],
    scimple_schema: Union[BaseSchema, Attribute],
    processors: Processors,
    context_provider: Optional[Union[ResponseContextProvider, ResponseContextProvider]],
    validator: Optional[Validator],
) -> type[marshmallow.Schema]:
    if isinstance(scimple_schema, ListResponse):
        processors = _get_list_response_processors(
            scimple_schema=scimple_schema,
            processors=processors,
            context_provider=context_provider,
        )
    elif isinstance(scimple_schema, ResourceSchema):
        processors = _get_resource_processors(
            scimple_schema=scimple_schema,
            processors=processors,
            context_provider=context_provider,
        )
    elif isinstance(scimple_schema, BulkResponse) and isinstance(validator, BulkOperations):
        processors = _get_bulk_response_processors(
            scimple_schema=scimple_schema,
            processors=processors,
            context_provider=context_provider,
            validator=validator,
        )
    elif isinstance(scimple_schema, BulkRequest) and isinstance(validator, BulkOperations):
        processors = _get_bulk_request_processors(
            scimple_schema=scimple_schema,
            processors=processors,
            context_provider=context_provider,
            validator=validator,
        )
    elif isinstance(scimple_schema, PatchOp):
        processors = _get_patch_op_processors(
            scimple_schema=scimple_schema,
            processors=processors,
            context_provider=context_provider,
        )
    elif isinstance(scimple_schema, Attribute):
        processors = _get_generic_attr_processors(
            scimple_schema=scimple_schema,
        )
    else:
        processors = _get_generic_processors(
            scimple_schema=scimple_schema,
            processors=processors,
            context_provider=context_provider,
        )

    processors["get_attribute"] = _get_field_value
    class_ = type(
        type(scimple_schema).__name__,
        (schema_cls,),
        processors,
    )
    return cast(type[marshmallow.Schema], class_)


def _create_schema(
    scimple_schema: Union[BaseSchema, Attribute],
    processors: Processors,
    context_provider: Optional[Union[ResponseContextProvider, RequestContextProvider]],
    validator: Optional[Validator],
) -> type[marshmallow.Schema]:
    if isinstance(scimple_schema, BaseSchema):
        if isinstance(scimple_schema, ListResponse) and len(scimple_schema.contained_schemas) == 1:
            fields = _get_fields(
                scimple_schema.attrs,
                field_by_attr_rep={
                    scimple_schema.attrs.resources: marshmallow.fields.List(
                        _get_nested_field(_get_fields(scimple_schema.contained_schemas[0].attrs)),
                    )
                },
            )
        else:
            fields = _get_fields(scimple_schema.attrs)

        if isinstance(scimple_schema, ResourceSchema):
            extension_fields = {}
            for extension_uri, attrs_ in scimple_schema.attrs.extensions.items():
                extension_fields[str(extension_uri)] = _get_nested_field(_get_fields(attrs_))
            fields.update(extension_fields)
    else:
        fields = {str(scimple_schema.name): _get_field(scimple_schema)}

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
