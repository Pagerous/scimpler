import abc
from typing import Any, Dict, Iterable, List, Optional, Union

from src.data.attributes import (
    Attribute,
    AttributeIssuer,
    AttributeMutability,
    AttributeReturn,
    Attributes,
    AttributeUniqueness,
    BoundedAttributes,
    Complex,
    DateTime,
    String,
    URIReference,
)
from src.data.container import Invalid, Missing, SCIMDataContainer
from src.error import ValidationError, ValidationIssues


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
        if issues.can_proceed(("schemas",)):
            issues.merge(
                self._validate_schemas_field(data),
                location=(schemas.rep.attr,),
            )
        if issues.can_proceed():
            issues.merge(self._validate(data))
        return issues

    def _validate_schemas_field(self, data):
        issues = ValidationIssues()
        provided_schemas = data.get(self._attrs.schemas.rep)
        if not provided_schemas:
            return issues

        main_schema = self.schema.lower()
        provided_schemas = [item.lower() for item in provided_schemas]
        if len(provided_schemas) > len(set(provided_schemas)):
            issues.add_error(
                issue=ValidationError.duplicated_values(),
                proceed=True,
            )

        known_schemas = [item.lower() for item in self.schemas]
        main_schema_included = False
        mismatch = False
        for schema in provided_schemas:
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

    def extend(self, extension: "SchemaExtension", required: bool = False) -> None:
        if extension.schema in map(lambda x: x.lower(), self.schemas):
            raise ValueError(f"schema {extension.schema!r} already in {self.name!r} resource")
        if extension.name.lower() in self._schema_extensions:
            raise ValueError(f"extension {extension.name!r} already in resource")
        self._schema_extensions[extension.name.lower()] = {
            "extension": extension,
            "required": required,
        }
        self._attrs.extend(extension.attrs, extension.schema, required)

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

    def _validate_schemas_field(self, data: SCIMDataContainer) -> ValidationIssues:
        provided_schemas = data.get(self.attrs.schemas.rep)
        if not provided_schemas:
            return ValidationIssues()

        issues = super()._validate_schemas_field(data)
        if not issues.can_proceed():
            return issues

        known_schemas = [item.lower() for item in self.schemas]
        provided_schemas = [item.lower() for item in provided_schemas]
        reported_missing = set()
        for k, v in data.to_dict().items():
            k_lower = k.lower()
            if k_lower in known_schemas and k_lower not in provided_schemas:
                issues.add_error(
                    issue=ValidationError.missing_schema_extension(k),
                    proceed=True,
                )
                reported_missing.add(k_lower)
                break

        for extension in self._schema_extensions.values():
            extension_schema = extension["extension"].schema.lower()
            if (
                extension["required"]
                and extension_schema not in provided_schemas
                and extension_schema not in reported_missing
            ):
                issues.add_error(
                    issue=ValidationError.missing_schema_extension(extension_schema),
                    proceed=True,
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
        self._attrs = Attributes(attrs)
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
    def attrs(self) -> Attributes:
        return self._attrs
