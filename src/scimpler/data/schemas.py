import warnings
from copy import copy
from typing import Any, Iterable, MutableMapping, Optional, cast

from typing_extensions import Self

from scimpler.data.attr_presence import (
    AttrPresenceConfig,
    DataInclusivity,
    validate_presence,
)
from scimpler.data.attrs import (
    AttrFilter,
    Attribute,
    AttributeIssuer,
    AttributeMutability,
    AttributeReturn,
    AttributeUniqueness,
    BoundedAttrs,
    Complex,
    DateTime,
    String,
    UriReference,
)
from scimpler.data.identifiers import BoundedAttrRep, SchemaURI
from scimpler.data.scim_data import Invalid, Missing, ScimData
from scimpler.error import ValidationError, ValidationIssues
from scimpler.registry import register_schema
from scimpler.warning import ScimpleUserWarning


def _bulk_id_validator(value) -> ValidationIssues:
    issues = ValidationIssues()
    if "bulkId" in value:
        issues.add_error(
            issue=ValidationError.bad_value_content(),
            proceed=False,
        )
    return issues


class SchemaMeta(type):
    def __init__(cls, name, bases, dct):
        super().__init__(name, bases, dct)
        if hasattr(cls, "schema"):
            cls.schema = SchemaURI(cls.schema)
            register_schema(SchemaURI(cls.schema))


class BaseSchema(metaclass=SchemaMeta):
    """
    Base class for all schemas. Includes `schemas` attribute to attributes defined in subclasses.
    """

    schema: str | SchemaURI
    base_attrs: list[Attribute] = [
        UriReference(
            name="schemas",
            required=True,
            multi_valued=True,
            mutability=AttributeMutability.READ_ONLY,
            returned=AttributeReturn.ALWAYS,
        )
    ]

    def __init__(
        self,
        attr_filter: Optional[AttrFilter] = None,
        common_attrs: Optional[Iterable[str]] = None,
    ):
        attrs = self._get_attrs()
        filtered_attrs = attr_filter(attrs) if attr_filter else attrs
        for attr in filtered_attrs:
            if attr.name == "schemas":
                break
        else:
            filtered_attrs.insert(0, BaseSchema.base_attrs[0])

        self._attrs = BoundedAttrs(
            schema=cast(SchemaURI, self.schema),
            attrs=filtered_attrs,
            common_attrs=list(common_attrs or []) + ["schemas"],
        )

    @property
    def attrs(self) -> BoundedAttrs:
        """
        Attributes that belong to the schema.
        """
        return self._attrs

    @property
    def schemas(self) -> list[SchemaURI]:
        """
        All schema URIs by which the schema is identified.
        """
        return [cast(SchemaURI, self.schema)]

    def _get_attrs(self) -> list[Attribute]:
        attrs = []
        for cls in reversed(self.__class__.mro()):
            if issubclass(cls, BaseSchema) and "base_attrs" in cls.__dict__:
                attrs.extend(getattr(cls, "base_attrs"))
        return attrs

    def deserialize(self, data: MutableMapping[str, Any]) -> ScimData:
        """
        Deserializes the provided data according to the schema attributes and their deserialization
        logic. Unknown attributes are not included in the result.
        """
        data = ScimData(data)
        deserialized = ScimData()
        for attr_rep, attr in self.attrs:
            value = data.get(attr_rep)
            if value is not Missing:
                deserialized.set(attr_rep, attr.deserialize(value))
        return self._deserialize(deserialized)

    def serialize(self, data: MutableMapping[str, Any]) -> ScimData:
        """
        Serializes the provided data according to the schema attributes and their serialization
        logic. Unknown attributes are not included in the result.
        """
        data = ScimData(data)
        serialized = ScimData()
        for attr_rep, attr in self.attrs:
            value = data.get(attr_rep)
            if value is not Missing:
                serialized.set(attr_rep, attr.serialize(value))
        return self._serialize(serialized)

    def filter(self, data: MutableMapping[str, Any], attr_filter: AttrFilter) -> ScimData:
        """
        Filters the provided data according to the provided `attr_filter`.
        """
        data = ScimData(data)
        filtered = ScimData()
        for attr_rep, attr in attr_filter(self.attrs):
            value = data.get(attr_rep)
            if value is Missing:
                continue
            if isinstance(attr, Complex):
                value = attr.filter(value, AttrFilter())
            filtered.set(attr_rep, value)
        return filtered

    def _deserialize(self, data: ScimData) -> ScimData:
        return data

    def _serialize(self, data: ScimData) -> ScimData:
        return data

    def validate(
        self,
        data: MutableMapping[str, Any],
        presence_config: Optional[AttrPresenceConfig] = None,
        **kwargs: Any,
    ) -> ValidationIssues:
        """
        Validates the provided data according to the schema attributes configuration.

        In addition, it validates `schemas` attribute:

        - if there are no duplicates,
        - if base schema is included,
        - if all provided schemas are known.

        Optionally, one can pass `AttrPresenceConfig`, so attribute requiredness, returnability,
        and issuer is checked, depending on the data flow direction.

        Extended built-in validation logic is supplied with `_validate` method, implemented
        in subclasses.

        Args:
            data: The data to be validated.
            presence_config: Presence config that enables additional validation of correctness
                of values presence.
            **kwargs: Additional parameters passed to `_validate` method.

        Returns:
            Validation issues.
        """
        issues = ValidationIssues()
        data = ScimData(data)
        issues.merge(self._validate_data(data, presence_config))
        if issues.can_proceed(("schemas",)):
            issues.merge(
                self._validate_schemas_field(data),
                location=("schemas",),
            )
        issues.merge(self._validate(data, **kwargs))
        return issues

    def clone(self, attr_filter: AttrFilter) -> Self:
        """
        Clones the schema with attributes filtered with the provided `attr_filter`.
        """
        cloned = copy(self)
        cloned._attrs = self._attrs.clone(attr_filter, ignore_filter=["schemas"])
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

    def _validate(self, data: ScimData, **kwargs) -> ValidationIssues:
        return ValidationIssues()

    def _validate_data(
        self,
        data: ScimData,
        presence_config: Optional[AttrPresenceConfig] = None,
    ) -> ValidationIssues:
        issues = ValidationIssues()
        for attr_rep, attr in self.attrs:
            value = data.get(attr_rep)
            issues_ = attr.validate(value)
            issues.merge(
                issues=issues_,
                location=attr_rep.location,
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
        presence_config: AttrPresenceConfig,
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

            for sub_attr_name, sub_attr in attr.attrs:
                bounded_sub_attr_rep = BoundedAttrRep(
                    schema=attr_rep.schema,
                    attr=attr_rep.attr,
                    sub_attr=sub_attr_name,
                )
                if attr.multi_valued:
                    if not value:
                        continue

                    for i, item in enumerate(value):
                        issues.merge(
                            self._validate_attr_presence(
                                attr=sub_attr,
                                attr_rep=bounded_sub_attr_rep,
                                value=item.get(sub_attr_name),
                                presence_config=presence_config,
                                required_by_schema=required_by_schema,
                            ),
                            location=[i, sub_attr_name],
                        )
                else:
                    issues.merge(
                        self._validate_attr_presence(
                            attr=sub_attr,
                            attr_rep=bounded_sub_attr_rep,
                            value=value.get(sub_attr_name) if value else Missing,
                            presence_config=presence_config,
                            required_by_schema=required_by_schema,
                        ),
                        location=[sub_attr_name],
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
        presence_config: AttrPresenceConfig,
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
        presence_config: AttrPresenceConfig,
    ) -> Optional[DataInclusivity]:
        if presence_config.include is None:
            # for example "userName" attribute, but not "manager.value"
            # from enterprise user extension
            if attr.required and not attr_rep.is_sub_attr:
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

        if not attr_rep.is_sub_attr:
            return None

        parent_attr_rep = BoundedAttrRep(schema=attr_rep.schema, attr=attr_rep.attr)
        if parent_attr_rep in presence_config.attr_reps:
            # it means the parent is specified in attr_reps
            # and potential errors should be delegated to it
            return None

        # handling "siblings", so if other sub-attributes
        # of the same complex attribute are included in attr_reps
        for rep in presence_config.attr_reps:
            if not rep.is_sub_attr:
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
        data: ScimData,
    ) -> bool:
        return True

    def include_schema_data(self, data: MutableMapping) -> None:
        """
        Includes the `schemas` attribute value in the provided `data`.
        """
        data["schemas"] = [self.schema]


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
    """
    Base class for system and user resources.
    """

    name: str
    endpoint: Optional[str] = None
    base_attrs: list[Attribute] = [
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
                UriReference(
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
        )
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.endpoint = self.endpoint or f"/{self.name}"

    def include_schema_data(self, data: MutableMapping) -> None:
        """
        Includes `schemas` and `meta.resourceType` attribute values in the provided `data`.
        """
        super().include_schema_data(data)
        if "meta" in data:
            data["meta"]["resourceType"] = self.name
        else:
            data["meta"] = {"resourceType": self.name}


class ResourceSchema(BaseResourceSchema):
    """
    Base class for all user-defined resources. Attributes: `schemas`, `meta`, `id`, and `externalId`
    are already defined in the schema.

    To define the schema, besides `base_attrs`, one must specify `schema`, `name` and `endpoint`
    class attributes. Optional class attributes are `plural_name`, and `description`.

    If `plural_name` is not specified, it is defaulted to `name`.

    Examples:
        >>> class MyResourceSchema(ResourceSchema):
        >>>     schema = "urn:my:resource"
        >>>     name = "Resource"
        >>>     plural_name = "Resources"
        >>>     endpoint = "/Resources"
        >>>     description = "The best resource."
        >>>     base_attrs = [...]

    The built-in validation is extended. Apart from constraints checked by the parent classes,
    `ResourceSchema`:

    - validates the consistency od `meta.resourceType` with the configured
      `ResourceSchema.name`,
    - validates if `schemas` contains schema URIs for all attributes in data.
    """

    plural_name: str
    description: str = ""
    base_attrs: list[Attribute] = [
        String(
            name="id",
            required=True,
            issuer=AttributeIssuer.SERVER,
            case_exact=True,
            mutability=AttributeMutability.READ_ONLY,
            returned=AttributeReturn.ALWAYS,
            uniqueness=AttributeUniqueness.SERVER,
            validators=[_bulk_id_validator],
        ),
        String(
            name="externalId",
            issuer=AttributeIssuer.CLIENT,
            case_exact=True,
        ),
    ]

    def __init__(self, attr_filter: Optional[AttrFilter] = None):
        """
        Args:
            attr_filter: Attribute filter used to filter attributes defined in class-level
                `base_attrs` attribute. Useful for creating different schemas, e.g. with
                only "readWrite" attributes, so serialization and deserialization also
                filter the data.
        """
        self.plural_name = getattr(self, "plural_name", self.name)
        self.endpoint = self.endpoint or f"/{self.plural_name}"
        self._common_attrs = ["id", "externalId", "meta"]
        super().__init__(attr_filter=attr_filter, common_attrs=self._common_attrs)
        self._schema_extensions: dict[str, dict] = {}

    @property
    def schemas(self) -> list[SchemaURI]:
        """
        Schema URIs by which the schema is identified. Includes schema extension URIs.
        """
        return [cast(SchemaURI, self.schema)] + [
            extension["extension"].schema for extension in self._schema_extensions.values()
        ]

    @property
    def extensions(self) -> dict[SchemaURI, bool]:
        """
        Extensions added to the schema. Map containing schema extension URIs and flags indicating
        whether they are required extensions.
        """
        return {
            item["extension"].schema: item["required"] for item in self._schema_extensions.values()
        }

    def extend(self, extension: "SchemaExtension", required: bool = False) -> None:
        """
        Extends the base schema with the provided schema `extension`. Extension attributes
        become part of the schema and are available in `ResourceSchema.attrs`.

        Args:
            extension: Schema extension which extends the base schema.
            required: Flag indicating whether the extension is required. If the extension
                is required, all required fields from the extension become required in base
                schema during presence checks. If the extension is not required and some of
                its attributes are required, they are not considered required in the base schema.
        """
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
            schema=cast(SchemaURI, extension.schema),
            attrs=extension.attrs,
        )

    def _validate(self, data: ScimData, **kwargs) -> ValidationIssues:
        issues = ValidationIssues()
        resource_type_rep = getattr(self.attrs, "meta__resourcetype", None)
        # it means that schema doesn't contain 'meta.resourceType'
        if resource_type_rep is None:
            return issues
        resource_type = data.get(resource_type_rep)
        if resource_type not in [Missing, Invalid]:
            issues.merge(
                validate_resource_type_consistency(
                    resource_type=resource_type,
                    expected=self.name,
                )
            )
        return issues

    def _validate_schemas_field(self, data: ScimData) -> ValidationIssues:
        provided_schemas = data.get(self.attrs.schemas)
        if not provided_schemas:
            return ValidationIssues()

        issues = super()._validate_schemas_field(data)
        known_schemas = [item.lower() for item in self.schemas]
        provided_schemas = [item.lower() for item in provided_schemas if item is not Invalid]
        reported_missing = set()
        for k, v in data.items():
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
        data: ScimData,
    ) -> bool:
        if (
            attr_rep.schema not in (data.get("schemas") or [])
            and self.extensions.get(attr_rep.schema) is False
        ):
            return False
        return True

    def include_schema_data(self, data: MutableMapping) -> None:
        """
        Includes `schemas` and `meta.resourceType` attribute values in the provided `data`.
        The exact content of `schemas` depends on the rest of the data. If the data contains
        attributes from the extensions, the extension URIs appear in the attached `schemas`.
        """
        super().include_schema_data(data)
        for extension, extension_attrs in self.attrs.extensions.items():
            for attr_rep, _ in extension_attrs:
                if attr_rep in data:
                    data["schemas"].append(str(extension))
                    break


class SchemaExtension:
    """
    Base class for all user-defined schema extensions.

    To define the schema extension, besides `base_attrs`, one must specify `schema` and `name`
    class attributes. Optionally, `description` can be provided.

    Examples:
        >>> class MyResourceSchemaExtension(SchemaExtension):
        >>>     schema = "urn:my:resource:extension"
        >>>     name = "ResourceExtension"
        >>>     description = "The best resource extension."
        >>>     base_attrs = [...]
    """

    schema: str | SchemaURI
    name: str
    description: str = ""
    base_attrs: list[Attribute] = []

    def __init__(self, attr_filter: Optional[AttrFilter] = None):
        self.schema = SchemaURI(self.schema)
        register_schema(self.schema, True)
        self._attrs = BoundedAttrs(
            schema=self.schema,
            attrs=(attr_filter(self.base_attrs) if attr_filter else self.base_attrs),
        )

    @property
    def attrs(self) -> BoundedAttrs:
        """
        Attributes that belong to the extension.
        """
        return self._attrs
