import warnings
from copy import copy
from typing import (
    Any,
    Iterable,
    Mapping,
    MutableMapping,
    Optional,
    TypeVar,
    Union,
    cast,
)

from typing_extensions import Self

from scimpler._registry import register_resource_schema, register_schema
from scimpler.data.attr_value_presence import (
    AttrValuePresenceConfig,
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
    create_attribute_from_schema_rep,
)
from scimpler.data.identifiers import BoundedAttrRep, SchemaUri
from scimpler.data.scim_data import Invalid, Missing, ScimData
from scimpler.error import ValidationError, ValidationIssues
from scimpler.warning import ScimplerUserWarning


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
            cls.schema = SchemaUri(cls.schema)
            register_schema(SchemaUri(cls.schema))


class BaseSchema(metaclass=SchemaMeta):
    """
    Base class for all schemas. Includes `schemas` attribute to attributes defined in subclasses.
    """

    schema: Union[str, SchemaUri]
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
            schema=cast(SchemaUri, self.schema),
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
    def schemas(self) -> list[SchemaUri]:
        """
        All schema URIs by which the schema is identified.
        """
        return [cast(SchemaUri, self.schema)]

    def _get_attrs(self) -> list[Attribute]:
        attrs = []
        for cls in reversed(self.__class__.mro()):
            if issubclass(cls, BaseSchema) and "base_attrs" in cls.__dict__:
                attrs.extend(getattr(cls, "base_attrs"))
        return attrs

    def deserialize(self, data: Mapping[str, Any]) -> ScimData:
        """
        Deserializes the provided data according to the schema attributes and their deserialization
        logic. Unknown attributes are not included in the result.
        """
        data = ScimData(data)
        deserialized = ScimData()
        for attr_rep, attr in self.attrs:
            value = data.get(attr_rep)
            if value or value in [0, False]:
                deserialized.set(attr_rep, attr.deserialize(value))
        return self._deserialize(deserialized)

    def serialize(self, data: Mapping[str, Any]) -> ScimData:
        """
        Serializes the provided data according to the schema attributes and their serialization
        logic. Unknown attributes are not included in the result.
        """
        data = ScimData(data)
        serialized = ScimData()
        for attr_rep, attr in self.attrs:
            value = data.get(attr_rep)
            if value or value in [0, False]:
                serialized.set(attr_rep, attr.serialize(value))
        return self._serialize(serialized)

    def filter(self, data: Mapping[str, Any], attr_filter: AttrFilter) -> ScimData:
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
        data: Mapping[str, Any],
        presence_config: Optional[AttrValuePresenceConfig] = None,
        **kwargs: Any,
    ) -> ValidationIssues:
        """
        Validates the provided data according to the schema attributes configuration.

        In addition, it validates the ` schemas ` attribute:

        - If there are no duplicates,
        - if base schema is included,
        - if all provided schemas are known.

        Optionally, one can pass `AttrValuePresenceConfig`, so attribute requiredness,
        returnability, and issuer are checked, depending on the data flow direction.

        Extended built-in validation logic is supplied with the `_validate` method, implemented
        in subclasses.

        Args:
            data: The data to be validated.
            presence_config: Presence config that enables additional validation of value presence.
            **kwargs: Additional parameters passed to the ` _ validate ` method.

        Returns:
            Validation issues.
        """
        issues = ValidationIssues()
        data = ScimData(data)
        issues.merge(self._validate_data(data, presence_config))

        if data.get("schemas"):
            issues.merge(
                self._validate_schemas_field(data),
                location=["schemas"],
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

    def _validate_schemas_field(self, data: ScimData) -> ValidationIssues:
        issues = ValidationIssues()
        provided_schemas = data.get("schemas")
        valid_schemas_parsed = []
        for i, item in enumerate(provided_schemas):
            if item is Invalid:
                continue
            try:
                parsed = SchemaUri(item)
                provided_schemas[i] = parsed
                valid_schemas_parsed.append(parsed)
            except ValueError:
                issues.add_error(
                    issue=ValidationError.bad_value_syntax(),
                    location=[i],
                    proceed=False,
                )
                provided_schemas[i] = Invalid

        if len(valid_schemas_parsed) > len(set(valid_schemas_parsed)):
            issues.add_error(
                issue=ValidationError.duplicated_values(),
                proceed=True,
            )

        main_schema_included = False
        mismatch = False
        for schema in valid_schemas_parsed:
            if schema == self.schema:
                main_schema_included = True

            elif schema not in self.schemas and not mismatch:
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
        presence_config: Optional[AttrValuePresenceConfig] = None,
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
        presence_config: AttrValuePresenceConfig,
        required_by_schema: bool,
    ) -> ValidationIssues:
        if isinstance(attr, Complex):
            return self._validate_presence_complex(
                attr=attr,
                attr_rep=attr_rep,
                value=value,
                presence_config=presence_config,
                required_by_schema=required_by_schema,
            )

        issues = ValidationIssues()
        if attr.multi_valued and value:
            for _i, item in enumerate(value):
                issues.merge(
                    self._validate_attr_value_presence(
                        attr=attr,
                        attr_rep=attr_rep,
                        value=item,
                        presence_config=presence_config,
                        required_by_schema=required_by_schema,
                    ),
                )
            return issues

        issues.merge(
            self._validate_attr_value_presence(
                attr=attr,
                attr_rep=attr_rep,
                value=value,
                presence_config=presence_config,
                required_by_schema=required_by_schema,
            ),
        )
        return issues

    def _validate_presence_complex(
        self,
        attr: Complex,
        attr_rep: BoundedAttrRep,
        value: Any,
        presence_config: AttrValuePresenceConfig,
        required_by_schema: bool,
    ) -> ValidationIssues:
        issues = self._validate_attr_value_presence(
            attr=attr,
            attr_rep=attr_rep,
            value=value,
            presence_config=presence_config,
            required_by_schema=required_by_schema,
        )
        if issues.has_errors():
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
                        self._validate_attr_value_presence(
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
                    self._validate_attr_value_presence(
                        attr=sub_attr,
                        attr_rep=bounded_sub_attr_rep,
                        value=value.get(sub_attr_name) if value else Missing,
                        presence_config=presence_config,
                        required_by_schema=required_by_schema,
                    ),
                    location=[sub_attr_name],
                )
        return issues

    @classmethod
    def _validate_attr_value_presence(
        cls,
        attr: Attribute,
        attr_rep: BoundedAttrRep,
        value: Any,
        presence_config: AttrValuePresenceConfig,
        required_by_schema: bool,
    ):
        return validate_presence(
            attr=attr,
            value=value,
            direction=presence_config.direction,
            ignore_issuer=attr_rep in presence_config.ignore_issuer,
            inclusivity=cls._get_inclusivity(attr, attr_rep, presence_config),
            required_by_schema=required_by_schema,
        )

    @classmethod
    def _get_inclusivity(  # noqa: PLR0911
        cls,
        attr: Attribute,
        attr_rep: BoundedAttrRep,
        presence_config: AttrValuePresenceConfig,
    ) -> Optional[DataInclusivity]:
        if presence_config.include is None:
            # for example, "userName" attribute, but not "manager.value"
            # from enterprise user extension
            if attr.required and not attr_rep.is_sub_attr:
                return DataInclusivity.INCLUDE
            return None

        if attr_rep in presence_config.attr_reps:
            if presence_config.include:
                return DataInclusivity.INCLUDE
            return DataInclusivity.EXCLUDE

        if isinstance(attr, Complex):
            return cls._get_inclusivity_complex(attr_rep, presence_config)

        if not attr_rep.is_sub_attr:
            return cls._get_inclusivity_simple(attr_rep, presence_config)

        parent_attr_rep = BoundedAttrRep(schema=attr_rep.schema, attr=attr_rep.attr)
        if parent_attr_rep in presence_config.attr_reps:
            # it means the parent is specified in attr_reps
            # and potential errors should be delegated to it
            return None

        return cls._get_inclusivity_based_on_siblings(attr_rep, presence_config)

    @classmethod
    def _get_inclusivity_simple(
        cls,
        attr_rep: BoundedAttrRep,
        presence_config: AttrValuePresenceConfig,
    ):
        if presence_config.include:
            if attr_rep in presence_config.attr_reps:
                return DataInclusivity.INCLUDE
            return DataInclusivity.EXCLUDE

        if attr_rep in presence_config.attr_reps:
            return DataInclusivity.EXCLUDE
        return DataInclusivity.INCLUDE

    @classmethod
    def _get_inclusivity_complex(
        cls,
        attr_rep: BoundedAttrRep,
        presence_config: AttrValuePresenceConfig,
    ) -> Optional[DataInclusivity]:
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

    @classmethod
    def _get_inclusivity_based_on_siblings(
        cls,
        attr_rep: BoundedAttrRep,
        presence_config: AttrValuePresenceConfig,
    ) -> Optional[DataInclusivity]:
        # handling "siblings", so if other sub-attributes
        # of the same complex attribute are included in attr_reps
        for rep in presence_config.attr_reps:
            if not rep.is_sub_attr:
                continue

            if (
                isinstance(rep, BoundedAttrRep)
                and rep.schema == attr_rep.schema
                and rep.attr == attr_rep.attr
                and rep.sub_attr != attr_rep.sub_attr
            ):
                if presence_config.include:
                    return DataInclusivity.EXCLUDE
                return DataInclusivity.INCLUDE

            if rep.attr == attr_rep.attr and rep.sub_attr != attr_rep.sub_attr:
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

    def attach_schemas(self, data: MutableMapping) -> None:
        """
        Attaches the `schemas` attribute value in the provided `data`.
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
    endpoint: str
    base_attrs: list[Attribute] = [
        Complex(
            name="meta",
            issuer=AttributeIssuer.SERVICE_PROVIDER,
            mutability=AttributeMutability.READ_ONLY,
            sub_attributes=[
                String(
                    name="resourceType",
                    case_exact=True,
                    issuer=AttributeIssuer.SERVICE_PROVIDER,
                    mutability=AttributeMutability.READ_ONLY,
                ),
                DateTime(
                    name="created",
                    issuer=AttributeIssuer.SERVICE_PROVIDER,
                    mutability=AttributeMutability.READ_ONLY,
                ),
                DateTime(
                    name="lastModified",
                    issuer=AttributeIssuer.SERVICE_PROVIDER,
                    mutability=AttributeMutability.READ_ONLY,
                ),
                UriReference(
                    name="location",
                    issuer=AttributeIssuer.SERVICE_PROVIDER,
                    mutability=AttributeMutability.READ_ONLY,
                ),
                String(
                    name="version",
                    issuer=AttributeIssuer.SERVICE_PROVIDER,
                    case_exact=True,
                    mutability=AttributeMutability.READ_ONLY,
                ),
            ],
        )
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.endpoint = self.endpoint or f"/{self.name}"

    def get_location(self, resource_id: str) -> str:
        return f"{self.endpoint}/{resource_id}"

    def attach_meta(
        self,
        data: MutableMapping,
        resource_type: bool = True,
        resource_id: Optional[str] = None,
        sub_attrs: Optional[dict[str, Any]] = None,
    ) -> None:
        """
        Includes `meta` attributes in the `data`.

        The `meta.resourceType` attribute is added conditionally, depending on the
        `resource_type` parameter. Its value is the name of the schema.

        The `meta.location` attribute is added if `resource_id` is provided. Its
        value is the schema's `endpoint` attribute value + resource_id.

        The rest of `meta` sub-attributes can be added manually:
            - created
            - lastModified
            - version
        """
        meta_data = {}
        if resource_type:
            meta_data["resourceType"] = self.name

        if resource_id:
            meta_data["location"] = self.get_location(resource_id)

        available_sub_attrs = {"created", "lastModified", "version"}

        for sub_attr, value in (sub_attrs or {}).items():
            if sub_attr in available_sub_attrs:
                meta_data[sub_attr] = value

        if meta_data:
            data.setdefault("meta", {})
            data["meta"].update(meta_data)


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

    - Validates the consistency of `meta.resourceType` with the configured
      `ResourceSchema.name`
    - Validates if `schemas` contains schema URIs for all attributes in data
    """

    plural_name: str
    description: str = ""
    base_attrs: list[Attribute] = [
        String(
            name="id",
            required=True,
            issuer=AttributeIssuer.SERVICE_PROVIDER,
            case_exact=True,
            mutability=AttributeMutability.READ_ONLY,
            returned=AttributeReturn.ALWAYS,
            uniqueness=AttributeUniqueness.SERVER,
            validators=[_bulk_id_validator],
        ),
        String(
            name="externalId",
            issuer=AttributeIssuer.PROVISIONING_CLIENT,
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
        register_resource_schema(self)
        self.plural_name = getattr(self, "plural_name", self.name)
        self.endpoint = self.endpoint or f"/{self.plural_name}"
        self._common_attrs = ["id", "externalId", "meta"]
        super().__init__(attr_filter=attr_filter, common_attrs=self._common_attrs)
        self._schema_extensions: dict[str, dict] = {}

    @property
    def schemas(self) -> list[SchemaUri]:
        """
        Schema URIs by which the schema is identified. Includes schema extension URIs.
        """
        return [cast(SchemaUri, self.schema)] + [
            extension["extension"].schema for extension in self._schema_extensions.values()
        ]

    @property
    def extensions(self) -> dict[SchemaUri, bool]:
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
                is required, all required fields from the extension become required in the base
                schema during presence checks. If the extension is not required and some of
                its attributes are required, they are not considered required in the base schema.
        """
        if extension.schema in self.schemas:
            raise ValueError(f"schema {extension.schema!r} already in {self.name!r} resource")
        if extension.name.lower() in self._schema_extensions:
            raise RuntimeError(f"extension {extension.name!r} already in resource")
        self._schema_extensions[extension.name.lower()] = {
            "extension": extension,
            "required": required,
        }
        for attr_rep, _attr in extension.attrs:
            if (
                self.attrs.get(BoundedAttrRep(schema=self.schema, attr=attr_rep.attr)) is not None
                or attr_rep.attr in self._common_attrs
            ):
                warnings.warn(
                    message=(
                        f"Resource extension {extension.name!r} defines {attr_rep.attr!r} "
                        f"attribute, which is also present in base {self.name!r} schema."
                    ),
                    category=ScimplerUserWarning,
                    stacklevel=2,
                )
        self._attrs.extend(
            schema=cast(SchemaUri, extension.schema),
            attrs=extension.attrs,
        )

    def _validate(self, data: ScimData, **kwargs) -> ValidationIssues:
        issues = ValidationIssues()
        resource_type_rep = getattr(self.attrs, "meta__resourcetype", None)
        # it means that the schema doesn't contain 'meta.resourceType'
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
        issues = super()._validate_schemas_field(data)
        provided_schemas = data.get("schemas")
        for k, _v in data.items():
            possible_schema = SchemaUri(k)
            if possible_schema in self.schemas and possible_schema not in provided_schemas:
                issues.add_error(
                    issue=ValidationError.missing_schema_extension(k),
                    proceed=True,
                )
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

    def attach_schemas(self, data: MutableMapping) -> None:
        """
        Includes `schemas` attribute values in the provided `data`.

        The exact content of `schemas` depends on the rest of the data. If the data contains
        attributes from the extensions, the extension URIs appear in the attached `schemas`.
        """
        super().attach_schemas(data)
        scim_data = ScimData(data)
        for extension, extension_attrs in self.attrs.extensions.items():
            for attr_rep, _ in extension_attrs:
                if attr_rep in scim_data:
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

    schema: Union[str, SchemaUri]
    name: str
    description: str = ""
    base_attrs: list[Attribute] = []

    def __init__(self, attr_filter: Optional[AttrFilter] = None):
        self.schema = SchemaUri(self.schema)
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


_T = TypeVar("_T", bound=Union[ResourceSchema, SchemaExtension])


def create_from_rep(
    base_cls: type[_T],
    schema_rep: Mapping[str, Any],
    **kwargs,
) -> type[_T]:
    """
    Creates `ResourceSchema` or `SchemaExtension` subclass, based on
    the `schema_rep`. The `schema_rep` must be compliant with SCIM Schema
    Definition, as specified in [RFC-7643](https://www.rfc-editor.org/rfc/rfc7643#section-7).

    Additional parameters, not present in SCIM Schema Definition must
    be passed in `kwargs`.

    Examples:
        >>> schema_cls = create_from_rep(
        >>>     base_cls=ResourceSchema,
        >>>     schema_rep={...},
        >>>     endpoint="/MyResources"
        >>> )
        >>>
        >>> assert issubclass(schema_cls, ResourceSchema)

    """
    schema_rep = ScimData(schema_rep)
    attrs = []
    for attribute_schema_rep in schema_rep["attributes"]:
        attrs.append(create_attribute_from_schema_rep(attribute_schema_rep))

    name = schema_rep["name"]
    kwargs.update(
        {
            "schema": schema_rep["id"],
            "name": name,
            "description": schema_rep["description"],
            "base_attrs": attrs,
        }
    )
    return cast(type[_T], type(name, (base_cls,), kwargs))
