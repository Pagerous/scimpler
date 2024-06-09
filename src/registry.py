from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from src.data.operator import BinaryAttributeOperator, UnaryAttributeOperator
    from src.data.schemas import ResourceSchema


resources: dict[str, "ResourceSchema"] = {}
schemas: dict[str, bool] = {}


def register_resource_schema(resource_schema: "ResourceSchema"):
    if resource_schema.name in resources:
        raise RuntimeError(f"resource {resource_schema.name!r} already registered")
    resources[resource_schema.name] = resource_schema

    if resource_schema.schema in schemas:
        raise RuntimeError(f"schema {resource_schema.schema!r} already registered")

    schemas[resource_schema.schema] = False
    for schema in resource_schema.extensions:
        schemas[schema] = True


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
