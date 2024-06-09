from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from src.container import SchemaURI
    from src.data.operator import BinaryAttributeOperator, UnaryAttributeOperator
    from src.data.schemas import ResourceSchema


resources: dict[str, "ResourceSchema"] = {}
schemas: dict[str, bool] = {}


def register_resource_schema(resource_schema: "ResourceSchema"):
    if resource_schema.name in resources:
        raise RuntimeError(f"resource {resource_schema.name!r} already registered")
    resources[resource_schema.name] = resource_schema


def register_schema(schema: "SchemaURI", extension: bool = False):
    schemas[schema] = extension


Converter = Callable[[Any], Any]


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
