from typing import TYPE_CHECKING, Any, Callable, Dict

if TYPE_CHECKING:
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
