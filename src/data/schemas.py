import copy
import warnings
from typing import Any, Callable, Iterable, Optional, TypeVar, Union

from src.container import BoundedAttrRep, Invalid, Missing, SchemaURI, SCIMDataContainer
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
from src.data.attributes_presence import (
    AttributePresenceConfig,
    DataInclusivity,
    validate_presence,
)
from src.error import ValidationError, ValidationIssues
from src.registry import register_schema
from src.warning import ScimpleUserWarning


def bulk_id_validator(value) -> ValidationIssues:
    issues = ValidationIssues()
    if "bulkId" in value:
        issues.add_error(
            issue=ValidationError.bad_value_content(),
            proceed=False,
        )
    return issues


TData = TypeVar("TData", bound=Union[SCIMDataContainer, dict])


class BaseSchema:
    def __init__(
        self,
        schema: str,
        attrs: Iterable[Attribute],
        common_attrs: Optional[Iterable[str]] = None,
    ):
        schema = SchemaURI(schema)
        register_schema(schema)
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
    def schemas(self) -> list[str]:
        return [self._schema]

    @property
    def schema(self) -> SchemaURI:
        return self._schema

    def deserialize(self, data: TData) -> SCIMDataContainer:
        data = SCIMDataContainer(data)
        deserialized = SCIMDataContainer()
        for attr_rep, attr in self.attrs:
            value = data.get(attr_rep)
            if value is not Missing:
                deserialized.set(attr_rep, attr.deserialize(value))
        return deserialized

    def serialize(self, data: TData) -> dict[str, Any]:
        data = SCIMDataContainer(data)
        serialized = SCIMDataContainer()
        for attr_rep, attr in self.attrs:
            value = data.get(attr_rep)
            if value is not Missing:
                serialized.set(attr_rep, attr.serialize(value))
        return self._serialize(serialized).to_dict()

    def filter(self, data: TData, attr_filter: Callable[[Attribute], bool]) -> TData:
        is_dict = isinstance(data, dict)
        if is_dict:
            data = SCIMDataContainer(data)

        filtered = SCIMDataContainer()
        for attr_rep, attr in self.attrs:
            value = data.get(attr_rep)
            if value is Missing:
                continue

            if isinstance(attr, Complex):
                value = attr.filter(value, attr_filter)
                if all(value) if isinstance(value, list) else value:
                    filtered.set(attr_rep, value)
            elif attr_filter(attr):
                filtered.set(attr_rep, value)

        return filtered.to_dict() if is_dict else filtered

    def _serialize(self, data: SCIMDataContainer) -> SCIMDataContainer:  # noqa
        return data

    def validate(
        self,
        data: Union[SCIMDataContainer, dict[str, Any]],
        presence_config: Optional[AttributePresenceConfig] = None,
        **kwargs,
    ) -> ValidationIssues:
        issues = ValidationIssues()
        if isinstance(data, dict):
            data = SCIMDataContainer(data)
        issues.merge(self._validate_data(data, presence_config))
        if issues.can_proceed(("schemas",)):
            issues.merge(
                self._validate_schemas_field(data),
                location=("schemas",),
            )
        issues.merge(self._validate(data, **kwargs))
        return issues

    def clone(self, attr_filter: Callable[[Attribute], bool]) -> "BaseSchema":
        cloned = copy.copy(self)
        cloned._attrs = self._attrs.clone(attr_filter)
        return cloned

    def _validate_schemas_field(self, data):
        issues = ValidationIssues()
        provided_schemas = data.get(self._attrs.schemas)
        if not provided_schemas:
            return issues

        main_schema = self.schema.lower()
        provided_schemas = [item.lower() for item in provided_schemas if item is not Invalid]
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

    def _validate(self, data: SCIMDataContainer, **kwargs) -> ValidationIssues:
        return ValidationIssues()

    def _validate_data(
        self,
        data: SCIMDataContainer,
        presence_config: Optional[AttributePresenceConfig] = None,
    ) -> ValidationIssues:
        issues = ValidationIssues()
        for attr_rep, attr in self.attrs:
            value = data.get(attr_rep)
            issues_ = attr.validate(value)
            location = (attr_rep.attr,)
            if attr_rep.extension:
                location = (attr_rep.schema,) + location
            issues.merge(
                issues=issues_,
                location=location,
            )
            if not issues_.can_proceed():
                data.set(attr_rep, Invalid)
            elif presence_config:
                issues.merge(
                    self._validate_presence(
                        attr=attr,
                        attr_rep=attr_rep,
                        value=value,
                        presence_config=presence_config,
                        required_by_schema=self._is_attr_required_by_schema(attr_rep, data),
                    ),
                    location=attr_rep.location,
                )
        return issues

    def _validate_presence(
        self,
        attr: Attribute,
        attr_rep: BoundedAttrRep,
        value: Any,
        presence_config: AttributePresenceConfig,
        required_by_schema: bool,
    ) -> ValidationIssues:
        issues = ValidationIssues()
        if isinstance(attr, Complex):
            issues_ = self._validate_attr_presence(
                attr=attr,
                attr_rep=attr_rep,
                value=value,
                presence_config=presence_config,
                required_by_schema=required_by_schema,
            )
            issues.merge(issues_)
            if issues_.has_errors():
                return issues

            for sub_attr_rep, sub_attr in attr.attrs:
                bounded_sub_attr_rep = BoundedAttrRep(
                    schema=attr_rep.schema,
                    attr=attr_rep.attr,
                    sub_attr=sub_attr_rep.attr,
                )
                if attr.multi_valued:
                    if not value:
                        continue

                    for i, item in enumerate(value):
                        issues.merge(
                            self._validate_attr_presence(
                                attr=sub_attr,
                                attr_rep=bounded_sub_attr_rep,
                                value=item.get(sub_attr_rep),
                                presence_config=presence_config,
                                required_by_schema=required_by_schema,
                            ),
                            location=[i, bounded_sub_attr_rep.sub_attr],
                        )
                else:
                    issues.merge(
                        self._validate_attr_presence(
                            attr=sub_attr,
                            attr_rep=bounded_sub_attr_rep,
                            value=value.get(sub_attr_rep) if value else Missing,
                            presence_config=presence_config,
                            required_by_schema=required_by_schema,
                        ),
                        location=[bounded_sub_attr_rep.sub_attr],
                    )
            return issues

        if attr.multi_valued and value:
            for i, item in enumerate(value):
                issues.merge(
                    self._validate_attr_presence(
                        attr=attr,
                        attr_rep=attr_rep,
                        value=item,
                        presence_config=presence_config,
                        required_by_schema=required_by_schema,
                    ),
                )
            return issues

        issues.merge(
            self._validate_attr_presence(
                attr=attr,
                attr_rep=attr_rep,
                value=value,
                presence_config=presence_config,
                required_by_schema=required_by_schema,
            ),
        )
        return issues

    @staticmethod
    def _validate_attr_presence(
        attr: Attribute,
        attr_rep: BoundedAttrRep,
        value: Any,
        presence_config: AttributePresenceConfig,
        required_by_schema: bool,
    ):
        return validate_presence(
            attr=attr,
            value=value,
            direction=presence_config.direction,
            ignore_issuer=attr_rep in presence_config.ignore_issuer,
            inclusivity=BaseSchema._get_inclusivity(attr, attr_rep, presence_config),
            required_by_schema=required_by_schema,
        )

    @staticmethod
    def _get_inclusivity(
        attr: Attribute,
        attr_rep: BoundedAttrRep,
        presence_config: AttributePresenceConfig,
    ) -> Optional[DataInclusivity]:
        if presence_config.include is None:
            # for example "userName" attribute, but not "manager.value"
            # from enterprise user extension
            if attr.required and not attr_rep.sub_attr:
                return DataInclusivity.INCLUDE
            return None

        if attr_rep in presence_config.attr_reps:
            if presence_config.include:
                return DataInclusivity.INCLUDE
            return DataInclusivity.EXCLUDE

        if isinstance(attr, Complex):
            # handling "children", so if they exist within
            # attr_reps, the presence check is delegated to them
            for rep in presence_config.attr_reps:
                if attr_rep.attr != rep.attr:
                    continue

                if isinstance(rep, BoundedAttrRep):
                    if attr_rep == (BoundedAttrRep(schema=rep.schema, attr=rep.attr)):
                        return None
                else:
                    return None

            if presence_config.include:
                return DataInclusivity.EXCLUDE
            return DataInclusivity.INCLUDE

        if not attr_rep.sub_attr:
            return None

        parent_attr_rep = BoundedAttrRep(schema=attr_rep.schema, attr=attr_rep.attr)
        if parent_attr_rep in presence_config.attr_reps:
            # it means the parent is specified in attr_reps
            # and potential errors should be delegated to it
            return None

        # handling "siblings", so if other sub-attributes
        # of the same complex attribute are included in attr_reps
        for rep in presence_config.attr_reps:
            if not rep.sub_attr:
                continue

            if (
                isinstance(rep, BoundedAttrRep)
                and rep.schema == attr_rep.schema
                and rep.attr == attr_rep.attr
            ):
                if presence_config.include:
                    return DataInclusivity.EXCLUDE
                return DataInclusivity.INCLUDE

            if rep.attr == attr_rep.attr:
                if presence_config.include:
                    return DataInclusivity.EXCLUDE
                return DataInclusivity.INCLUDE

        return None

    def _is_attr_required_by_schema(
        self,
        attr_rep: BoundedAttrRep,
        data: SCIMDataContainer,
    ) -> bool:
        return True


def validate_resource_type_consistency(
    resource_type: str,
    expected: str,
) -> ValidationIssues:
    issues = ValidationIssues()
    if resource_type != expected:
        issues.add_error(
            issue=ValidationError.must_be_equal_to(expected),
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
        schema: str | SchemaURI,
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
        self._schema_extensions: dict[str, dict] = {}
        self._plural_name = plural_name or name
        self._endpoint = endpoint or f"/{self._plural_name}"
        self._description = description

    @property
    def endpoint(self) -> str:
        return self._endpoint

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
    def schemas(self) -> list[str]:
        return [self.schema] + [
            extension["extension"].schema for extension in self._schema_extensions.values()
        ]

    @property
    def extensions(self) -> dict[SchemaURI, bool]:
        return {
            item["extension"].schema: item["required"] for item in self._schema_extensions.values()
        }

    def get_extension(self, name: str) -> "SchemaExtension":
        name_lower = name.lower()
        if name_lower not in self._schema_extensions:
            raise ValueError(f"{self.name!r} has no {name!r} extension")
        return self._schema_extensions[name_lower]["extension"]

    def extend(self, extension: "SchemaExtension", required: bool = False) -> None:
        if extension.schema in map(lambda x: x.lower(), self.schemas):
            raise ValueError(f"schema {extension.schema!r} already in {self.name!r} resource")
        if extension.name.lower() in self._schema_extensions:
            raise RuntimeError(f"extension {extension.name!r} already in resource")
        self._schema_extensions[extension.name.lower()] = {
            "extension": extension,
            "required": required,
        }
        for attr_rep, attr in extension.attrs:
            if (
                self.attrs.get(BoundedAttrRep(schema=self.schema, attr=attr_rep.attr)) is not None
                or attr_rep.attr in self._common_attrs
            ):
                warnings.warn(
                    message=(
                        f"Resource extension {extension.name!r} defines {attr_rep.attr!r} "
                        f"attribute, which is also present in base {self.name!r} schema."
                    ),
                    category=ScimpleUserWarning,
                )
        self._attrs.extend(
            schema=extension.schema,
            attrs=extension.attrs,
        )

    def _validate(self, data: SCIMDataContainer, **kwargs) -> ValidationIssues:
        issues = ValidationIssues()
        resource_type = data.get(self.attrs.meta__resourcetype)
        if resource_type not in [Missing, Invalid]:
            issues.merge(
                validate_resource_type_consistency(
                    resource_type=resource_type,
                    expected=self.name,
                )
            )
        return issues

    def _validate_schemas_field(self, data: SCIMDataContainer) -> ValidationIssues:
        provided_schemas = data.get(self.attrs.schemas)
        if not provided_schemas:
            return ValidationIssues()

        issues = super()._validate_schemas_field(data)
        known_schemas = [item.lower() for item in self.schemas]
        provided_schemas = [item.lower() for item in provided_schemas if item is not Invalid]
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

    def _is_attr_required_by_schema(
        self,
        attr_rep: BoundedAttrRep,
        data: SCIMDataContainer,
    ) -> bool:
        if (
            attr_rep.schema not in (data.get("schemas") or [])
            and self.extensions.get(attr_rep.schema) is False
        ):
            return False
        return True


class SchemaExtension:
    def __init__(
        self,
        schema: str,
        name: str,
        attrs: Optional[Iterable[Attribute]] = None,
        description: str = "",
    ):
        self._schema = SchemaURI(schema)
        register_schema(self._schema, True)
        self._attrs = BoundedAttributes(self._schema, attrs)
        self._name = name
        self._description = description

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def schema(self) -> SchemaURI:
        return self._schema

    @property
    def attrs(self) -> BoundedAttributes:
        return self._attrs
