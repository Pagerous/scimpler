from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from scimpler.data.identifiers import SchemaUri
    from scimpler.data.operator import BinaryAttributeOperator, UnaryAttributeOperator
    from scimpler.data.schemas import ResourceSchema


resources: dict[str, str] = {}
schemas: dict[str, bool] = {}


def register_resource_schema(resource_schema: "ResourceSchema"):
    endpoint = resources.get(resource_schema.name)
    if endpoint is not None and endpoint != resource_schema.endpoint:
        raise RuntimeError(
            f"resource {resource_schema.name!r} already defined for different endpoint {endpoint!r}"
        )
    resources[resource_schema.name] = resource_schema.endpoint


def register_schema(schema: "SchemaUri", extension: bool = False):
    if schema.lower().startswith("urn:ietf:params:scim:api:messages:2.0:") and schema in schemas:
        raise RuntimeError("schemas for SCIM API messages can not be overridden")
    schemas[schema] = extension


unary_operators: dict[str, type["UnaryAttributeOperator"]] = {}
binary_operators: dict[str, type["BinaryAttributeOperator"]] = {}


def register_unary_operator(operator: type["UnaryAttributeOperator"]):
    op = operator.op.lower()
    existing_operator = unary_operators.get(op)
    if existing_operator is not None and existing_operator != operator:
        raise RuntimeError(f"different implementation for unary operator {op!r} already provided")
    unary_operators[op] = operator


def register_binary_operator(operator: type["BinaryAttributeOperator"]):
    op = operator.op.lower()
    existing_operator = binary_operators.get(op)
    if existing_operator is not None and existing_operator != operator:
        raise RuntimeError(f"different implementation for binary operator {op!r} already provided")
    binary_operators[op] = operator
