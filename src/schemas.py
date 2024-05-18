import abc
import copy
import warnings
from typing import Any, Callable, Dict, Iterable, List, Optional, TypeVar, Union

from src.attributes import (
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
from src.container import BoundedAttrRep, Invalid, Missing, SCIMDataContainer
from src.error import ValidationError, ValidationIssues
from src.wanings import ScimpleUserWarning


def bulk_id_validator(value) -> ValidationIssues:
    issues = ValidationIssues()
    if "bulkId" in value:
        issues.add_error(
            issue=ValidationError.reserved_keyword("bulkId"),
            proceed=False,
        )
    return issues


TData = TypeVar("TData", bound=Union[SCIMDataContainer, Dict])


class BaseSchema(abc.ABC):
    def __init__(
        self,
        schema: str,
        attrs: Iterable[Attribute],
        common_attrs: Optional[Iterable[str]] = None,
    ):
        self._attrs = BoundedAttributes(
            schema=schema,
            attrs=[
                URIReference(
                    name="schemas",
                    required=True,
                    multi_valued=True,
                    mutability=AttributeMutability.READ_ONLY,
                    returned=AttributeReturn.ALWAYS,
                ),
                *attrs,
            ],
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

    def deserialize(self, data: TData) -> SCIMDataContainer:
        data = SCIMDataContainer(data)
        deserialized = SCIMDataContainer()
        for attr in self.attrs:
            value = data.get(attr.rep)
            if value is not Missing:
                deserialized.set(attr.rep, attr.deserialize(value))
        return deserialized

    def serialize(self, data: Any) -> Dict[str, Any]:
        data = SCIMDataContainer(data)
        serialized = SCIMDataContainer()
        for attr in self.attrs:
            value = data.get(attr.rep)
            if value is not Missing:
                serialized.set(attr.rep, attr.serialize(value))
        return self._serialize(data).to_dict()

    def filter(self, data: TData, attr_filter: Callable[[Attribute], bool]) -> TData:
        is_dict = isinstance(data, dict)
        if is_dict:
            data = SCIMDataContainer(data)

        filtered = SCIMDataContainer()
        for attr in self.attrs:
            value = data.get(attr.rep)
            if value is Missing:
                continue

            if isinstance(attr, Complex):
                value = attr.filter(value, attr_filter)
                if all(value) if isinstance(value, List) else value:
                    filtered.set(attr.rep, value)
            elif attr_filter(attr):
                filtered.set(attr.rep, value)

        return filtered.to_dict() if is_dict else filtered

    def _serialize(self, data: SCIMDataContainer) -> SCIMDataContainer:  # noqa
        return data

    def validate(self, data: Union[SCIMDataContainer, Dict[str, Any]]) -> ValidationIssues:
        issues = ValidationIssues()
        if isinstance(data, Dict):
            data = SCIMDataContainer(data)
        issues.merge(self._validate_data(data))
        if issues.can_proceed(("schemas",)):
            issues.merge(
                self._validate_schemas_field(data),
                location=("schemas",),
            )
        if issues.can_proceed():
            issues.merge(self._validate(data))
        return issues

    def clone(self, attr_filter: Callable[[Attribute], bool]) -> "BaseSchema":
        cloned = copy.copy(self)
        cloned._attrs = self._attrs.clone(attr_filter)
        return cloned

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


class BaseResourceSchema(BaseSchema):
    def __init__(self, name: str, endpoint: str = "", **kwargs):
        attrs = kwargs.pop("attrs", [])
        attrs = [
            Complex(
                name="meta",
                issuer=AttributeIssuer.SERVER,
                mutability=AttributeMutability.READ_ONLY,
                sub_attributes=[
                    String(
                        name="resourceType",
                        case_exact=True,
                        issuer=AttributeIssuer.SERVER,
                        mutability=AttributeMutability.READ_ONLY,
                    ),
                    DateTime(
                        name="created",
                        issuer=AttributeIssuer.SERVER,
                        mutability=AttributeMutability.READ_ONLY,
                    ),
                    DateTime(
                        name="lastModified",
                        issuer=AttributeIssuer.SERVER,
                        mutability=AttributeMutability.READ_ONLY,
                    ),
                    URIReference(
                        name="location",
                        issuer=AttributeIssuer.SERVER,
                        mutability=AttributeMutability.READ_ONLY,
                    ),
                    String(
                        name="version",
                        issuer=AttributeIssuer.SERVER,
                        case_exact=True,
                        mutability=AttributeMutability.READ_ONLY,
                    ),
                ],
            ),
            *attrs,
        ]
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


class ResourceSchema(BaseResourceSchema):
    def __init__(
        self,
        schema: str,
        name: str,
        plural_name: Optional[str] = None,
        description: str = "",
        endpoint: Optional[str] = None,
        attrs: Optional[Iterable[Attribute]] = None,
    ):
        self._common_attrs = ["id", "externalid", "meta"]
        super().__init__(
            name=name,
            schema=schema,
            attrs=[
                String(
                    name="id",
                    required=True,
                    issuer=AttributeIssuer.SERVER,
                    case_exact=True,
                    mutability=AttributeMutability.READ_ONLY,
                    returned=AttributeReturn.ALWAYS,
                    uniqueness=AttributeUniqueness.SERVER,
                    validators=[bulk_id_validator],
                ),
                String(
                    name="externalId",
                    issuer=AttributeIssuer.CLIENT,
                    case_exact=True,
                ),
                *(attrs or []),
            ],
            common_attrs=self._common_attrs,
        )
        self._schema_extensions: Dict[str, Dict] = {}
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
        for attr in extension.attrs:
            if (
                self.attrs.get(BoundedAttrRep(schema=self.schema, attr=attr.rep.attr)) is not None
                or attr.rep.attr.lower() in self._common_attrs
            ):
                warnings.warn(
                    message=(
                        f"Resource extension {extension.name!r} defines {attr.rep.attr!r} "
                        f"attribute, which is also present in base {self.name!r} schema."
                    ),
                    category=ScimpleUserWarning,
                )

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
        return issues


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
