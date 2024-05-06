import abc
from typing import Any, Dict, Iterable, List, Optional, Sequence, Union

from src.data.attributes import (
    Attribute,
    AttributeIssuer,
    AttributeMutability,
    AttributeReturn,
    AttributeUniqueness,
    BoundedAttributes,
    Complex,
    DateTime,
    String,
    URIReference,
)
from src.data.container import Invalid, Missing, SCIMDataContainer
from src.error import ValidationError, ValidationIssues
from src.registry import register_resource_schema


def bulk_id_validator(value) -> ValidationIssues:
    issues = ValidationIssues()
    if "bulkId" in value:
        issues.add_error(
            issue=ValidationError.reserved_keyword("bulkId"),
            proceed=False,
        )
    return issues


schemas = URIReference(
    name="schemas",
    required=True,
    multi_valued=True,
    mutability=AttributeMutability.READ_ONLY,
    returned=AttributeReturn.ALWAYS,
)


id_ = String(
    name="id",
    required=True,
    issuer=AttributeIssuer.SERVER,
    case_exact=True,
    mutability=AttributeMutability.READ_ONLY,
    returned=AttributeReturn.ALWAYS,
    uniqueness=AttributeUniqueness.SERVER,
    validators=[bulk_id_validator],
)

external_id = String(
    name="externalId",
    issuer=AttributeIssuer.CLIENT,
    case_exact=True,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)

_meta__resource_type = String(
    name="resourceType",
    case_exact=True,
    issuer=AttributeIssuer.SERVER,
    mutability=AttributeMutability.READ_ONLY,
    returned=AttributeReturn.DEFAULT,
)

_meta__created = DateTime(
    name="created",
    issuer=AttributeIssuer.SERVER,
    mutability=AttributeMutability.READ_ONLY,
    returned=AttributeReturn.DEFAULT,
)

_meta__last_modified = DateTime(
    name="lastModified",
    issuer=AttributeIssuer.SERVER,
    mutability=AttributeMutability.READ_ONLY,
    returned=AttributeReturn.DEFAULT,
)

_meta__location = URIReference(
    name="location",
    issuer=AttributeIssuer.SERVER,
    mutability=AttributeMutability.READ_ONLY,
    returned=AttributeReturn.DEFAULT,
)

_meta__version = String(
    name="version",
    issuer=AttributeIssuer.SERVER,
    case_exact=True,
    mutability=AttributeMutability.READ_ONLY,
    returned=AttributeReturn.DEFAULT,
)


meta = Complex(
    sub_attributes=[
        _meta__resource_type,
        _meta__created,
        _meta__last_modified,
        _meta__location,
        _meta__version,
    ],
    name="meta",
    issuer=AttributeIssuer.SERVER,
    mutability=AttributeMutability.READ_ONLY,
    returned=AttributeReturn.DEFAULT,
)


class BaseSchema(abc.ABC):
    def __init__(
        self,
        schema: str,
        attrs: Iterable[Attribute],
        common_attrs: Optional[Iterable[str]] = None,
    ):
        self._attrs = BoundedAttributes(
            schema=schema,
            extension=False,
            attrs=[schemas, *attrs],
            common_attrs=(common_attrs or []) + ["schemas"],
        )
        self._schema = schema

    @property
    def attrs(self) -> BoundedAttributes:
        return self._attrs

    @property
    def schemas(self) -> List[str]:
        return [self._schema]

    @property
    def schema(self) -> str:
        return self._schema

    def deserialize(self, data: Any) -> SCIMDataContainer:
        data = SCIMDataContainer(data)
        deserialized = SCIMDataContainer()
        for attr in self.attrs:
            value = data.get(attr.rep)
            if value is not Missing:
                deserialized.set(attr.rep, attr.deserialize(value))
        return deserialized

    def serialize(self, data: Any) -> SCIMDataContainer:
        data = SCIMDataContainer(data)
        serialized = SCIMDataContainer()
        for attr in self.attrs:
            value = data.get(attr.rep)
            if value is not Missing:
                serialized.set(attr.rep, attr.serialize(value))
        return serialized

    def validate(self, data: Union[SCIMDataContainer, Dict[str, Any]]) -> ValidationIssues:
        issues = ValidationIssues()
        if isinstance(data, Dict):
            data = SCIMDataContainer(data)
        issues.merge(self._validate_data(data))

        schemas_ = data.get(self._attrs.schemas.rep)
        if issues.can_proceed(("schemas",)) and schemas_:
            issues.merge(
                validate_schemas_field(
                    data=data,
                    schemas_=schemas_,
                    main_schema=self.schema,
                    known_schemas=schemas_,
                ),
                location=(schemas.rep.attr,),
            )

        if issues.can_proceed():
            issues.merge(self._validate(data))
        return issues

    def _validate(self, data: SCIMDataContainer) -> ValidationIssues:
        return ValidationIssues()

    def _validate_data(self, data: SCIMDataContainer) -> ValidationIssues:
        issues = ValidationIssues()
        for attr in self.attrs:
            value = data.get(attr.rep)
            if value is Missing:
                continue
            issues_ = attr.validate(value)
            location = (attr.rep.attr,)
            if attr.rep.extension:
                location = (attr.rep.schema,) + location
            issues.merge(
                issues=issues_,
                location=location,
            )
        return issues


def validate_schemas_field(
    data: SCIMDataContainer,
    schemas_: List[str],
    main_schema: str,
    known_schemas: Sequence[str],
) -> ValidationIssues:
    issues = ValidationIssues()
    main_schema = main_schema.lower()
    schemas_ = [item.lower() for item in schemas_]
    if len(schemas_) > len(set(schemas_)):
        issues.add_error(
            issue=ValidationError.duplicated_values(),
            proceed=True,
        )

    known_schemas = [item.lower() for item in known_schemas]
    main_schema_included = False
    mismatch = False
    for schema in schemas_:
        if schema == main_schema:
            main_schema_included = True

        elif schema not in known_schemas and not mismatch:
            issues.add_error(
                issue=ValidationError.unknown_schema(),
                proceed=True,
            )
            mismatch = True

    if not main_schema_included:
        issues.add_error(
            issue=ValidationError.missing_main_schema(),
            proceed=True,
        )

    for k, v in data.to_dict().items():
        k_lower = k.lower()
        if k_lower in known_schemas and k_lower not in schemas_:
            issues.add_error(
                issue=ValidationError.missing_schema_extension(k),
                proceed=True,
            )
    return issues


def validate_resource_type_consistency(
    resource_type: str,
    expected: str,
) -> ValidationIssues:
    issues = ValidationIssues()
    if resource_type != expected:
        issues.add_error(
            issue=ValidationError.resource_type_mismatch(
                resource_type=expected,
                provided=resource_type,
            ),
            proceed=True,
            location=("meta", "resourceType"),
        )
    return issues


class ResourceSchema(BaseSchema):
    def __init__(
        self,
        schema: str,
        name: str,
        plural_name: Optional[str] = None,
        description: str = "",
        endpoint: Optional[str] = None,
        attrs: Optional[Iterable[Attribute]] = None,
    ):
        super().__init__(
            schema=schema,
            attrs=[id_, external_id, meta, *(attrs or [])],
            common_attrs=["id", "externalId", "meta"],
        )
        self._schema_extensions: Dict[str, Dict] = {}
        self._name = name
        self._plural_name = plural_name or name
        self._endpoint = endpoint or f"/{self._plural_name}"
        self._description = description
        register_resource_schema(self)

    @property
    def endpoint(self) -> str:
        return self._endpoint

    @endpoint.setter
    def endpoint(self, value: str):
        self._endpoint = value

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def plural_name(self) -> str:
        return self._plural_name

    @property
    def schemas(self) -> List[str]:
        return [self.schema] + [
            extension["extension"].schema for extension in self._schema_extensions.values()
        ]

    @property
    def extensions(self) -> Dict["SchemaExtension", bool]:
        return {item["extension"]: item["required"] for item in self._schema_extensions.values()}

    def get_extension(self, name: str) -> "SchemaExtension":
        name = name.lower()
        if name not in self._schema_extensions:
            raise ValueError(f"{self.name!r} has no {name!r} extension")
        return self._schema_extensions[name]["extension"]

    def add_extension(self, extension: "SchemaExtension", required: bool = False) -> None:
        if extension.schema in map(lambda x: x.lower(), self.schemas):
            raise ValueError(f"schema {extension.schema!r} already in {self.name!r} resource")
        if extension.name.lower() in self._schema_extensions:
            raise ValueError(f"extension {extension.name!r} already in resource")
        self._schema_extensions[extension.name.lower()] = {
            "extension": extension,
            "required": required,
        }
        self._attrs.extend(extension.attrs)

    def _validate(self, data: SCIMDataContainer) -> ValidationIssues:
        issues = ValidationIssues()
        resource_type = data.get(self.attrs.meta__resourcetype.rep)
        if resource_type not in [Missing, Invalid]:
            issues.merge(
                validate_resource_type_consistency(
                    resource_type=resource_type,
                    expected=self.name,
                )
            )
        return issues


class ServiceResourceSchema(BaseSchema):
    def __init__(self, name: str, endpoint: str = "", **kwargs):
        attrs = kwargs.pop("attrs", [])
        attrs = [meta, *attrs]
        super().__init__(attrs=attrs, **kwargs)
        self._name = name
        self._endpoint = endpoint or f"/{self._name}"

    @property
    def name(self) -> str:
        return self._name

    @property
    def endpoint(self) -> str:
        return self._endpoint

    @endpoint.setter
    def endpoint(self, value) -> None:
        self._endpoint = value


class SchemaExtension:
    def __init__(
        self,
        schema: str,
        name: str,
        attrs: Optional[Iterable[Attribute]] = None,
        description: str = "",
    ):
        self._schema = schema
        self._attrs = BoundedAttributes(
            schema=schema,
            extension=True,
            attrs=attrs,
        )
        self._name = name
        self._description = description

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def schema(self) -> str:
        return self._schema

    @property
    def attrs(self) -> BoundedAttributes:
        return self._attrs

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.schema,
            "name": self.name,
            "description": self.description,
            "attributes": [attr.to_dict() for attr in self.attrs],
        }
