from typing import TYPE_CHECKING, Any, Callable, Union

from src.constants import SCIMType

if TYPE_CHECKING:
    from src.data.operator import BinaryAttributeOperator, UnaryAttributeOperator
    from src.data.schemas import ResourceSchema


resource_schemas: dict[str, "ResourceSchema"] = {}


def register_resource_schema(resource_schema: "ResourceSchema"):
    if resource_schema.name in resource_schemas:
        raise RuntimeError(f"schema {resource_schema.schema!r} already registered")
    resource_schemas[resource_schema.name] = resource_schema


Converter = Callable[[Any], Any]


serializers: dict[str, Converter] = {}
deserializers: dict[str, Converter] = {}


def register_serializer(scim_type: Union[SCIMType, str], converter: Converter) -> None:
    scim_type = SCIMType(scim_type)

    if scim_type in serializers:
        raise RuntimeError(f"serializer for {scim_type!r} already registered")

    serializers[scim_type] = converter


def register_deserializer(scim_type: Union[SCIMType, str], converter: Converter) -> None:
    scim_type = SCIMType(scim_type)

    if scim_type in deserializers:
        raise RuntimeError(f"deserializer for {scim_type!r} already registered")

    deserializers[scim_type] = converter


unary_operators = {}
binary_operators = {}


def register_unary_operator(operator: type["UnaryAttributeOperator"]):
    if operator.SCIM_OP.lower() in unary_operators:
        raise RuntimeError(f"unary operator {operator.SCIM_OP!r} already registered")

    unary_operators[operator.SCIM_OP.lower()] = operator


def register_binary_operator(operator: type["BinaryAttributeOperator"]):
    if operator.SCIM_OP.lower() in binary_operators:
        raise RuntimeError(f"binary operator {operator.SCIM_OP!r} already registered")

    binary_operators[operator.SCIM_OP.lower()] = operator
