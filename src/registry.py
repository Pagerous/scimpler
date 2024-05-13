from typing import TYPE_CHECKING, Any, Callable, Dict, Type

if TYPE_CHECKING:
    from src.operator import BinaryAttributeOperator, UnaryAttributeOperator
    from src.schemas import ResourceSchema


resource_schemas: Dict[str, "ResourceSchema"] = {}


def register_resource_schema(resource_schema: "ResourceSchema"):
    if resource_schema.name in resource_schemas:
        raise RuntimeError(f"schema {resource_schema.schema!r} already registered")
    resource_schemas[resource_schema.name] = resource_schema


TypeConverter = Callable[[Any], Any]


converters: Dict[str, TypeConverter] = {}


def register_converter(scim_type: str, converter: TypeConverter) -> None:
    if scim_type not in [
        "binary",
        "dateTime",
        "reference",
    ]:
        raise ValueError(f"can not register converter for {scim_type!r}")

    if scim_type in converters:
        raise RuntimeError(f"converter for {scim_type!r} already registered")

    converters[scim_type] = converter


unary_operators = {}
binary_operators = {}


def register_unary_operator(operator: Type["UnaryAttributeOperator"]):
    if operator.SCIM_OP in unary_operators:
        raise RuntimeError(f"unary operator {operator.SCIM_OP!r} already registered")

    unary_operators[operator.SCIM_OP] = operator


def register_binary_operator(operator: Type["BinaryAttributeOperator"]):
    if operator.SCIM_OP in binary_operators:
        raise RuntimeError(f"binary operator {operator.SCIM_OP!r} already registered")

    binary_operators[operator.SCIM_OP] = operator
