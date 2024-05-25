from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from src.data.operator import BinaryAttributeOperator, UnaryAttributeOperator
    from src.data.schemas import ResourceSchema


resource_schemas: dict[str, "ResourceSchema"] = {}


def register_resource_schema(resource_schema: "ResourceSchema"):
    if resource_schema.name in resource_schemas:
        raise RuntimeError(f"schema {resource_schema.schema!r} already registered")
    resource_schemas[resource_schema.name] = resource_schema


TypeConverter = Callable[[Any], Any]


converters: dict[str, TypeConverter] = {}


def register_converter(scim_type: str, converter: TypeConverter) -> None:
    if scim_type not in [
        "binary",
        "dateTime",
        "reference",
    ]:
        raise RuntimeError(f"can not register converter for {scim_type!r}")

    if scim_type in converters:
        raise RuntimeError(f"converter for {scim_type!r} already registered")

    converters[scim_type] = converter


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
