from collections.abc import MutableMapping
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Optional, Protocol, Union, cast

import marshmallow

from scimpler.data import attrs
from scimpler.data.attrs import Attribute, BoundedAttrs
from scimpler.data.identifiers import AttrName, AttrRep, BoundedAttrRep
from scimpler.data.schemas import BaseResourceSchema, BaseSchema, ResourceSchema
from scimpler.data.scim_data import Missing, ScimData
from scimpler.schemas import (
    BulkRequestSchema,
    BulkResponseSchema,
    ListResponseSchema,
    PatchOpSchema,
)
from scimpler.validator import Validator

_marshmallow_field_by_attr_type: dict[type[attrs.Attribute], type[marshmallow.fields.Field]] = {
    attrs.Unknown: marshmallow.fields.Raw,
    attrs.Boolean: marshmallow.fields.Boolean,
    attrs.Integer: marshmallow.fields.Integer,
    attrs.Decimal: marshmallow.fields.Float,
    attrs.DateTime: marshmallow.fields.DateTime,
    attrs.Binary: marshmallow.fields.String,
    attrs.ExternalReference: marshmallow.fields.String,
    attrs.UriReference: marshmallow.fields.String,
    attrs.ScimReference: marshmallow.fields.String,
    attrs.String: marshmallow.fields.String,
}
_initialized = False
_auto_initialized = False


class ContextError(Exception):
    pass


@dataclass
class Processors:
    validator: Optional[Callable] = None


class ResponseContext:
    def __init__(
        self, status_code: int, headers: Optional[dict[str, Any]] = None, **kwargs: Any
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
    def __call__(self) -> ResponseContext:
        """Returns `ResponseContext`."""


ContextProvider = Union[ResponseContextProvider]


def initialize(
    fields_by_attrs: Optional[dict[type[attrs.Attribute], type[marshmallow.fields.Field]]] = None,
):
    """
    Initializes the `marshmallow` extension. Used to specify mapping of scimpler attributes to
    marshmallow fields, used during data (de)serialization.

    Default mapping is as follows:

        scimpler.data.Boolean           ---> marshmallow.fields.Boolean
        scimpler.data.Integer           ---> marshmallow.fields.Integer
        scimpler.data.Decimal           ---> marshmallow.fields.Float
        scimpler.data.DateTime          ---> marshmallow.fields.DateTime
        scimpler.data.Binary            ---> marshmallow.fields.String
        scimpler.data.ExternalReference ---> marshmallow.fields.String
        scimpler.data.UriReference      ---> marshmallow.fields.String
        scimpler.data.ScimReference     ---> marshmallow.fields.String
        scimpler.data.String            ---> marshmallow.fields.String

    `scimpler.data.Complex` is always converted to `marshmallow.fields.Nested`.

    Raises:
        RuntimeError: When attempt to initialize the extension second time.
    """
    global _marshmallow_field_by_attr_type, _initialized
    if _auto_initialized:
        raise RuntimeError(
            "marshmallow extension has been automatically initialized with default field mapping; "
            "call scimpler.ext.marshmallow.initialize() before first call to extension"
        )
    if _initialized:
        raise RuntimeError("marshmallow extension has been already initialized")

    if fields_by_attrs is not None:
        _marshmallow_field_by_attr_type.update(fields_by_attrs)
    _initialized = True


def _get_fields(
    attrs_: Iterable[tuple[BoundedAttrRep, attrs.Attribute]],
    field_by_attr_rep: Optional[dict[AttrRep, marshmallow.fields.Field]] = None,
) -> dict:
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
) -> dict:
    fields_: dict[str, marshmallow.fields.Field] = {}
    for name, attr in attrs_:
        fields_[str(name)] = _get_field(attr)
    return fields_


def _get_extension_fields(attrs_: BoundedAttrs) -> dict:
    extension_fields = {}
    for extension_uri, attrs__ in attrs_.extensions.items():
        extension_fields[str(extension_uri)] = marshmallow.fields.Nested(_get_fields(attrs__))
    return extension_fields


def _get_field(attr: Attribute) -> marshmallow.fields.Field:
    field: marshmallow.fields.Field
    if attr.has_custom_processing:
        field = marshmallow.fields.Raw()
    else:
        if isinstance(attr, attrs.Complex):
            field = marshmallow.fields.Nested(_get_complex_sub_fields(attr.attrs))
        else:
            field = _marshmallow_field_by_attr_type[type(attr)]()
    if attr.multi_valued:
        field = marshmallow.fields.List(field)
    return field


def _transform_errors_dict(input_dict: dict[str, Any]) -> dict[str, Any]:
    output_dict: dict = {}
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


def _validate_response(
    data: MutableMapping[str, Any], response_validator: Callable, context: ResponseContext
) -> None:
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


def _validate_request(data: MutableMapping[str, Any], request_validator: Callable) -> None:
    issues = request_validator(body=data)
    if issues.has_errors():
        raise marshmallow.ValidationError(
            message=_transform_errors_dict(issues.to_dict(msg=True)),
        )


def _deserialize_list_response(
    scimpler_schema: ListResponseSchema,
    data: MutableMapping[str, Any],
) -> ScimData:
    data = ScimData(data)
    if len(scimpler_schema.supported_schemas) == 1:
        return scimpler_schema.deserialize(data)

    resources = data.pop("Resources", [])
    deserialized = scimpler_schema.deserialize(data)
    deserialized_resources = []
    for resource in resources:
        resource_schema = cast(BaseResourceSchema, scimpler_schema.get_schema(resource))
        deserialized_resource = _create_schema(
            scimpler_schema=resource_schema,
            processors=Processors(),
            context_provider=None,
        )().load(resource)
        deserialized_resources.append(deserialized_resource)
    if deserialized_resources:
        deserialized.set("Resources", deserialized_resources)
    return deserialized


def _get_list_response_processors(
    scimpler_schema: ListResponseSchema,
    processors: Processors,
    response_context_provider: Optional[ResponseContextProvider],
):
    processors_ = {}

    def _pre_load(_, data: MutableMapping[str, Any], **__) -> ScimData:
        if response_context_provider is None:
            raise ContextError("response context must be provided when loading ListResponseSchema")
        _validate_response(data, cast(Callable, processors.validator), response_context_provider())
        return _deserialize_list_response(scimpler_schema, data)

    def _post_load(_, data: MutableMapping[str, Any], **__) -> ScimData:
        return ScimData(data)

    def _pre_dump(_, data: MutableMapping[str, Any], **__) -> ScimData:
        data = ScimData(data)
        if len(scimpler_schema.supported_schemas) == 1:
            return scimpler_schema.serialize(data)

        resources_ = data.pop("Resources", [])
        serialized = scimpler_schema.serialize(data)
        serialized_resources = []
        for resource in resources_:
            resource_schema = scimpler_schema.get_schema(resource)
            if resource_schema is None:
                serialized_resource = {}
            else:
                serialized_resource = _create_schema(
                    scimpler_schema=resource_schema,
                    processors=Processors(),
                    context_provider=None,
                )().dump(resource)
            serialized_resources.append(serialized_resource)
        if serialized_resources:
            serialized["Resources"] = serialized_resources
        return serialized

    processors_["_pre_load"] = marshmallow.pre_load(_pre_load, pass_many=False)
    processors_["_post_load"] = marshmallow.post_load(_post_load)
    processors_["_pre_dump"] = marshmallow.pre_dump(_pre_dump, pass_many=False)
    return processors_


def _transform_resource_data_for_loading(
    scimpler_schema: ResourceSchema,
    data: MutableMapping[str, Any],
    original_data: MutableMapping[str, Any],
) -> ScimData:
    for extension_uri in scimpler_schema.extensions:
        extension_uri_lower = extension_uri.lower()
        for k in original_data:
            if k.lower() != extension_uri_lower:
                continue
            key_parts = k.split(".")
            if len(key_parts) == 1:
                continue
            extension_data = data
            for part in key_parts:
                extension_data = extension_data[part]
            data.pop(key_parts[0])
            data[k] = extension_data
    return ScimData(data)


def _get_resource_processors(
    scimpler_schema: ResourceSchema,
    processors: Processors,
    response_context_provider: Optional[ResponseContextProvider],
) -> dict[str, Callable]:
    processors_ = {}

    def _post_load(
        _, data: MutableMapping[str, Any], original_data: MutableMapping[str, Any], **__
    ) -> ScimData:
        return _transform_resource_data_for_loading(scimpler_schema, data, original_data)

    def _pre_dump(_, data: MutableMapping[str, Any], **__) -> ScimData:
        return scimpler_schema.serialize(data)

    processors_["_pre_load"] = _get_generic_pre_load(
        scimpler_schema=scimpler_schema,
        processors=processors,
        response_context_provider=response_context_provider,
    )
    processors_["_post_load"] = marshmallow.post_load(_post_load, pass_original=True)
    processors_["_pre_dump"] = marshmallow.pre_dump(_pre_dump)

    return processors_


def _deserialize_patch_op(
    scimpler_schema: PatchOpSchema,
    data: MutableMapping[str, Any],
) -> ScimData:
    values = [operation.pop("value", Missing) for operation in data.get("Operations", [])]
    deserialized = scimpler_schema.deserialize(data)
    for operation, value in zip(deserialized.get("Operations", []), values):
        if value is Missing:
            continue
        value_schema = _create_schema(
            scimpler_schema=scimpler_schema.get_value_schema(
                path=operation.get("path"),
                value=value,
            ),
            processors=Processors(validator=None),
            context_provider=None,
        )
        operation.set("value", value_schema().load(value))
    return deserialized


def _get_patch_op_processors(
    scimpler_schema: PatchOpSchema, processors: Processors
) -> dict[str, Callable]:
    processors_ = {}
    if validator := processors.validator:  # noqa

        def _pre_load(_, data: MutableMapping[str, Any], **__) -> ScimData:
            _validate_request(data, validator)
            return _deserialize_patch_op(scimpler_schema, data)
    else:

        def _pre_load(_, data: MutableMapping[str, Any], **__) -> ScimData:
            return _deserialize_patch_op(scimpler_schema, data)

    def _post_load(_, data: MutableMapping[str, Any], **__) -> ScimData:
        return ScimData(data)

    def _pre_dump(_, data: MutableMapping[str, Any], **__) -> ScimData:
        values = [operation.pop("value", None) for operation in data.get("Operations", [])]
        serialized = scimpler_schema.serialize(data)
        for operation, value in zip(serialized.get("Operations", []), values):
            if value in [None, Missing]:
                continue
            value_schema = _create_schema(
                scimpler_schema=scimpler_schema.get_value_schema(
                    path=operation.get("path"),
                    value=value,
                ),
                processors=Processors(validator=None),
                context_provider=None,
            )
            operation["value"] = value_schema().dump(value)
        return serialized

    processors_["_pre_load"] = marshmallow.pre_load(_pre_load)
    processors_["_post_load"] = marshmallow.post_load(_post_load)
    processors_["_pre_dump"] = marshmallow.pre_dump(_pre_dump)

    return processors_


def _get_bulk_response_operation_response_schema(
    scimpler_schema: BulkResponseSchema,
    operation: MutableMapping[str, Any],
) -> Optional[type[marshmallow.Schema]]:
    response_schema = scimpler_schema.get_schema(operation)
    if response_schema is None:
        return None
    return _create_schema(
        scimpler_schema=response_schema,
        processors=Processors(validator=None),
        context_provider=None,
    )


def _deserialize_bulk_response(
    scimpler_schema: BulkResponseSchema,
    data: MutableMapping[str, Any],
) -> ScimData:
    responses = [operation.pop("response", None) for operation in data.get("Operations", [])]
    deserialized = scimpler_schema.deserialize(data)
    for operation, response in zip(deserialized.get("Operations", []), responses):
        if response:
            response_schema = cast(
                type[marshmallow.Schema],
                _get_bulk_response_operation_response_schema(scimpler_schema, operation),
            )
            operation.set("response", response_schema().load(response))
    return deserialized


def _get_bulk_response_processors(
    scimpler_schema: BulkResponseSchema,
    processors: Processors,
    response_context_provider: Optional[ResponseContextProvider],
) -> dict[str, Callable]:
    processors_ = {}

    def _pre_load(_, data: MutableMapping[str, Any], **__) -> ScimData:
        if response_context_provider is None:
            raise ContextError("context must be provided when loading BulkResponseSchema")
        _validate_response(data, cast(Callable, processors.validator), response_context_provider())
        return _deserialize_bulk_response(scimpler_schema, data)

    def _post_load(_, data: MutableMapping[str, Any], **__) -> ScimData:
        return ScimData(data)

    def _pre_dump(_, data: MutableMapping[str, Any], **__) -> ScimData:
        responses = [operation.pop("response") for operation in data.get("Operations", [])]
        serialized = scimpler_schema.serialize(data)
        for operation, response in zip(serialized.get("Operations", []), responses):
            if response:
                response_schema = _get_bulk_response_operation_response_schema(
                    scimpler_schema, operation
                )
                serialized_response = (
                    {} if response_schema is None else response_schema().dump(response)
                )
                operation.set("response", serialized_response)
        return serialized

    processors_["_pre_load"] = marshmallow.pre_load(_pre_load)
    processors_["_post_load"] = marshmallow.post_load(_post_load)
    processors_["_pre_dump"] = marshmallow.pre_dump(_pre_dump)

    return processors_


def _deserialize_bulk_request(
    scimpler_schema: BulkRequestSchema,
    data: MutableMapping[str, Any],
) -> ScimData:
    requests_data = [operation.pop("data", None) for operation in data.get("Operations", [])]
    deserialized = scimpler_schema.deserialize(data)
    for operation, data in zip(deserialized.get("Operations", []), requests_data):
        if data:
            request_scimpler_schema = cast(BaseSchema, scimpler_schema.get_schema(operation))
            request_schema = _create_schema(
                scimpler_schema=request_scimpler_schema,
                processors=Processors(validator=None),
                context_provider=None,
            )
            operation.set("data", request_schema().load(data))
    return deserialized


def _get_bulk_request_processors(
    scimpler_schema: BulkRequestSchema, processors: Processors
) -> dict[str, Callable]:
    processors_ = {}

    def _pre_load(_, data: MutableMapping[str, Any], **__) -> ScimData:
        _validate_request(data, cast(Callable, processors.validator))
        return _deserialize_bulk_request(scimpler_schema, data)

    def _post_load(_, data: MutableMapping[str, Any], **__) -> ScimData:
        return ScimData(data)

    def _pre_dump(_, data: MutableMapping[str, Any], **__) -> ScimData:
        operation_data = [operation.pop("data") for operation in data.get("Operations", [])]
        serialized = scimpler_schema.serialize(data)
        for operation, data_item in zip(serialized.get("Operations", []), operation_data):
            if data_item:
                request_scimpler_schema = scimpler_schema.get_schema(operation)
                request_schema = (
                    None
                    if request_scimpler_schema is None
                    else _create_schema(
                        scimpler_schema=request_scimpler_schema,
                        processors=Processors(validator=None),
                        context_provider=None,
                    )
                )
                serialized_data_item = (
                    {} if request_schema is None else request_schema().dump(data_item)
                )
                operation["data"] = serialized_data_item
        return serialized

    processors_["_pre_load"] = marshmallow.pre_load(_pre_load)
    processors_["_post_load"] = marshmallow.post_load(_post_load)
    processors_["_pre_dump"] = marshmallow.pre_dump(_pre_dump)

    return processors_


def _get_generic_pre_load(
    scimpler_schema: BaseSchema,
    processors: Processors,
    response_context_provider: Optional[ResponseContextProvider] = None,
) -> Callable:
    if validator := processors.validator:

        def _pre_load(_, data: MutableMapping[str, Any], **__) -> ScimData:
            if response_context_provider is None:
                _validate_request(data, validator)
            else:
                _validate_response(data, validator, response_context_provider())
            return scimpler_schema.deserialize(data)
    else:

        def _pre_load(_, data: MutableMapping[str, Any], **__) -> ScimData:
            return scimpler_schema.deserialize(data)

    return marshmallow.pre_load(_pre_load)


def _get_generic_processors(
    scimpler_schema: BaseSchema,
    processors: Processors,
    response_context_provider: Optional[ResponseContextProvider] = None,
) -> dict[str, Callable]:
    processors_ = {}

    def _post_load(_, data: MutableMapping[str, Any], **__) -> ScimData:
        return ScimData(data)

    def _pre_dump(_, data: MutableMapping[str, Any], **__) -> ScimData:
        return scimpler_schema.serialize(data)

    processors_["_pre_load"] = _get_generic_pre_load(
        scimpler_schema=scimpler_schema,
        processors=processors,
        response_context_provider=response_context_provider,
    )
    processors_["_post_load"] = marshmallow.post_load(_post_load)
    processors_["_pre_dump"] = marshmallow.pre_dump(_pre_dump)

    return processors_


def _get_generic_attr_processors(
    scimpler_schema: Attribute,
) -> dict[str, Callable]:
    processors_ = {}

    def _pre_load(_, data: Any, **__) -> dict[str, Any]:
        return {str(scimpler_schema.name): scimpler_schema.deserialize(data)}

    def _post_load(_, data: Any, **__) -> Any:
        data = data.get(str(scimpler_schema.name))
        if isinstance(data, MutableMapping):
            return ScimData(data)
        if isinstance(data, list):
            return [ScimData(item) if isinstance(item, MutableMapping) else item for item in data]
        return data

    def _pre_dump(_, data: Any, **__) -> dict[str, Any]:
        return {str(scimpler_schema.name): scimpler_schema.serialize(data)}

    def _post_dump(_, data: MutableMapping[str, Any], **__) -> Any:
        return data.get(str(scimpler_schema.name))

    processors_["_pre_load"] = marshmallow.pre_load(_pre_load)
    processors_["_post_load"] = marshmallow.post_load(_post_load)
    processors_["_pre_dump"] = marshmallow.pre_dump(_pre_dump)
    processors_["_post_dump"] = marshmallow.post_dump(_post_dump)

    return processors_


def _include_processing_in_schema(
    schema_cls: type[marshmallow.Schema],
    scimpler_schema: Union[BaseSchema, Attribute],
    processors: Processors,
    response_context_provider: Optional[ResponseContextProvider],
) -> type[marshmallow.Schema]:
    if isinstance(scimpler_schema, ListResponseSchema):
        processors_ = _get_list_response_processors(
            scimpler_schema=scimpler_schema,
            processors=processors,
            response_context_provider=response_context_provider,
        )
    elif isinstance(scimpler_schema, ResourceSchema):
        processors_ = _get_resource_processors(
            scimpler_schema=scimpler_schema,
            processors=processors,
            response_context_provider=response_context_provider,
        )
    elif isinstance(scimpler_schema, BulkResponseSchema):
        processors_ = _get_bulk_response_processors(
            scimpler_schema=scimpler_schema,
            processors=processors,
            response_context_provider=response_context_provider,
        )
    elif isinstance(scimpler_schema, BulkRequestSchema):
        processors_ = _get_bulk_request_processors(
            scimpler_schema=scimpler_schema,
            processors=processors,
        )
    elif isinstance(scimpler_schema, PatchOpSchema):
        processors_ = _get_patch_op_processors(
            scimpler_schema=scimpler_schema,
            processors=processors,
        )
    elif isinstance(scimpler_schema, Attribute):
        processors_ = _get_generic_attr_processors(
            scimpler_schema=scimpler_schema,
        )
    else:
        processors_ = _get_generic_processors(
            scimpler_schema=scimpler_schema,
            processors=processors,
            response_context_provider=response_context_provider,
        )

    if not isinstance(scimpler_schema, Attribute):
        processors_["include_schema_data"] = scimpler_schema.include_schema_data

    processors_["get_attribute"] = lambda _, obj, key, default: obj.get(key, default)
    class_ = type(
        type(scimpler_schema).__name__,
        (schema_cls,),
        processors_,
    )
    return cast(type[marshmallow.Schema], class_)


def _create_schema(
    scimpler_schema: Union[BaseSchema, Attribute],
    processors: Processors,
    context_provider: Optional[ContextProvider],
) -> type[marshmallow.Schema]:
    if isinstance(scimpler_schema, BaseSchema):
        if (
            isinstance(scimpler_schema, ListResponseSchema)
            and len(scimpler_schema.supported_schemas) == 1
        ):
            fields = _get_fields(
                scimpler_schema.attrs,
                field_by_attr_rep={
                    scimpler_schema.attrs.resources: marshmallow.fields.List(
                        marshmallow.fields.Nested(
                            _create_schema(
                                scimpler_schema=scimpler_schema.supported_schemas[0],
                                processors=Processors(),
                                context_provider=None,
                            ),
                        ),
                    )
                },
            )
        else:
            fields = _get_fields(scimpler_schema.attrs.base_attrs)

        if isinstance(scimpler_schema, ResourceSchema):
            fields.update(_get_extension_fields(scimpler_schema.attrs))
    else:
        fields = {str(scimpler_schema.name): _get_field(scimpler_schema)}

    schema_cls = cast(type[marshmallow.Schema], marshmallow.Schema.from_dict(fields={**fields}))
    return _include_processing_in_schema(
        schema_cls=schema_cls,
        processors=processors,
        scimpler_schema=scimpler_schema,
        response_context_provider=context_provider,
    )


def create_response_schema(
    validator: Validator,
    context_provider: Optional[ResponseContextProvider] = None,
) -> type[marshmallow.Schema]:
    """
    Creates `marshmallow` schema for the response from the provided `validator`.

    The fields of the resulting schema have no SCIM-specific properties and attributes. Instead,
    the scimpler schema is hidden inside, so all validations and most of (de)serialization is
    the done exactly same.

    Args:
       validator: The validator to create the schema from.
       context_provider: Callable that returns `ResponseContext`, so parameters required
          for response validation. It is impossible to pass them once `marshmallow.Schema` is
          created.


    Examples:
        >>> from scimpler.data import AttrValuePresenceConfig
        >>> from scimpler.schemas import UserSchema
        >>> from scimpler.validator import ResourcesGet
        >>>
        >>> def get_presence_config_from_request() -> AttrValuePresenceConfig:
        >>>     ...
        >>>
        >>> v = ResourcesGet(resource_schema=UserSchema())
        >>> schema_cls = create_response_schema(
        >>>     v,
        >>>     context_provider=lambda: ResponseContext(
        >>>         status_code=200,
        >>>         presence_config=get_presence_config_from_request(),
        >>>     )
        >>> )
        >>> schema = schema_cls()
        >>> schema
        <UserSchema(many=False)>
        >>> schema.dump({...})
    """
    _ensure_initialized()
    return _create_schema(
        scimpler_schema=validator.response_schema,
        processors=Processors(validator=validator.validate_response),
        context_provider=context_provider,
    )


def create_request_schema(validator: Validator) -> type[marshmallow.Schema]:
    """
    Creates `marshmallow` schema for the request from the provided `validator`.

    The fields of the resulting schema have no SCIM-specific properties and attributes. Instead,
    the scimpler schema is hidden inside, so all validations and most of (de)serialization is
    the done exactly same.

    Args:
       validator: The validator to create the schema from.

    Examples:
        >>> from scimpler.schemas import UserSchema
        >>> from scimpler.validator import ResourcesPost
        >>>
        >>> v = ResourcesPost(resource_schema=UserSchema())
        >>> schema_cls = create_request_schema(v)
        >>> schema = schema_cls()
        >>> schema
        <UserSchema(many=False)>
        >>> schema.load({...})
    """
    _ensure_initialized()
    return _create_schema(
        scimpler_schema=validator.request_schema,
        processors=Processors(validator=validator.validate_request),
        context_provider=None,
    )


def _ensure_initialized():
    global _auto_initialized
    if not _initialized:
        initialize()
        _auto_initialized = True
