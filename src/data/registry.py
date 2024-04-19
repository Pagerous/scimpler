from typing import TYPE_CHECKING, Dict

if TYPE_CHECKING:
    from src.data.schemas import ResourceSchema


resource_schemas: Dict[str, ResourceSchema] = {}


def register_resource_schema(resource_schema: ResourceSchema):
    if resource_schema.name in resource_schemas:
        raise RuntimeError(f"schema {resource_schema.schema!r} already registered")
    resource_schemas[resource_schema.name] = resource_schema
