import abc
from typing import Any, Dict, Iterable, List, Optional, Sequence, Union

from src.data import type as at
from src.data.attributes import (
    Attribute,
    AttributeIssuer,
    AttributeMutability,
    AttributeReturn,
    Attributes,
    AttributeUniqueness,
    ComplexAttribute,
)
from src.data.container import AttrRep, Invalid, Missing, SCIMDataContainer
from src.error import ValidationError, ValidationIssues


def bulk_id_validator(value) -> ValidationIssues:
    issues = ValidationIssues()
    if "bulkId" in value:
        issues.add(
            issue=ValidationError.reserved_keyword("bulkId"),
            proceed=False,
        )
    return issues


schemas = Attribute(
    name="schemas",
    type_=at.URIReference,
    required=True,
    case_exact=False,
    multi_valued=True,
    mutability=AttributeMutability.READ_ONLY,
    returned=AttributeReturn.ALWAYS,
    uniqueness=AttributeUniqueness.NONE,
)


id_ = Attribute(
    name="id",
    type_=at.String,
    required=True,
    issuer=AttributeIssuer.SERVER,
    case_exact=True,
    multi_valued=False,
    mutability=AttributeMutability.READ_ONLY,
    returned=AttributeReturn.ALWAYS,
    uniqueness=AttributeUniqueness.SERVER,
    validators=[bulk_id_validator],
)

external_id = Attribute(
    name="externalId",
    type_=at.String,
    required=False,
    issuer=AttributeIssuer.CLIENT,
    case_exact=True,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,  # assumed uniqueness is controlled by clients
)

_meta__resource_type = Attribute(
    name="resourceType",
    type_=at.String,
    required=False,
    case_exact=True,
    issuer=AttributeIssuer.SERVER,
    multi_valued=False,
    mutability=AttributeMutability.READ_ONLY,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

_meta__created = Attribute(
    name="created",
    type_=at.DateTime,
    required=False,
    case_exact=False,
    issuer=AttributeIssuer.SERVER,
    multi_valued=False,
    mutability=AttributeMutability.READ_ONLY,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

_meta__last_modified = Attribute(
    name="lastModified",
    type_=at.DateTime,
    required=False,
    case_exact=False,
    issuer=AttributeIssuer.SERVER,
    multi_valued=False,
    mutability=AttributeMutability.READ_ONLY,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

# TODO: make sure it has the same value as the "Content-Location" HTTP response header
_meta__location = Attribute(
    name="location",
    type_=at.URIReference,
    required=False,
    issuer=AttributeIssuer.SERVER,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_ONLY,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

# TODO: make sure it has the same value as the "ETag" HTTP response header
_meta__version = Attribute(
    name="version",
    type_=at.String,
    required=False,
    issuer=AttributeIssuer.SERVER,
    case_exact=True,
    multi_valued=False,
    mutability=AttributeMutability.READ_ONLY,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)


meta = ComplexAttribute(
    sub_attributes=[
        _meta__resource_type,
        _meta__created,
        _meta__last_modified,
        _meta__location,
        _meta__version,
    ],
    name="meta",
    required=False,
    issuer=AttributeIssuer.SERVER,
    multi_valued=False,
    mutability=AttributeMutability.READ_ONLY,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)


class BaseSchema(abc.ABC):
    def __init__(self, schema: str, attrs: Iterable[Attribute]):
        bounded_attrs = []
        for attr in [schemas, *attrs]:
            bounded_attrs.append(self._bound_attr_to_schema(attr, AttrRep(schema, attr.rep.attr)))
            if isinstance(attr, ComplexAttribute):
                for sub_attr in attr.attrs:
                    bounded_attrs.append(
                        self._bound_attr_to_schema(
                            sub_attr, AttrRep(schema, attr.rep.attr, sub_attr.rep.attr)
                        )
                    )
        self._attrs = Attributes(bounded_attrs)
        self._schema = schema

    @staticmethod
    def _bound_attr_to_schema(attr: Attribute, attr_rep: AttrRep) -> Attribute:
        if isinstance(attr, ComplexAttribute):
            return ComplexAttribute(
                sub_attributes=list(attr.attrs),
                name=attr_rep,
                required=attr.required,
                issuer=attr.issuer,
                multi_valued=attr.multi_valued,
                mutability=attr.mutability,
                returned=attr.returned,
                uniqueness=attr.uniqueness,
                validators=attr.validators,
                parser=attr.parser,
                dumper=attr.dumper,
            )
        return Attribute(
            name=attr_rep,
            type_=attr.type,
            reference_types=attr.reference_types,
            issuer=attr.issuer,
            required=attr.required,
            case_exact=attr.case_exact,
            multi_valued=attr.multi_valued,
            canonical_values=attr.canonical_values,
            mutability=attr.mutability,
            returned=attr.returned,
            uniqueness=attr.uniqueness,
            validators=attr.validators,
            parser=attr.parser,
            dumper=attr.dumper,
        )

    @property
    def attrs(self) -> Attributes:
        return self._attrs

    @property
    def schemas(self) -> List[str]:
        return [self._schema]

    @property
    def schema(self) -> str:
        return self._schema

    def parse(self, data: Any) -> SCIMDataContainer:
        data = SCIMDataContainer(data)
        parsed = SCIMDataContainer()
        for attr in self.attrs.top_level:
            value = data.get(attr.rep)
            if value is not Missing:
                parsed.set(attr.rep, attr.parse(value))
        return parsed

    def dump(self, data: Any) -> SCIMDataContainer:
        data = SCIMDataContainer(data)
        dumped = SCIMDataContainer()
        for attr in self.attrs.top_level:
            value = data.get(attr.rep)
            if value is not Missing:
                dumped.set(attr.rep, attr.dump(value))
        return dumped

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
                )
            )

        if issues.can_proceed():
            issues.merge(self._validate(data))
        return issues

    def _validate(self, data: SCIMDataContainer) -> ValidationIssues:
        return ValidationIssues()

    def _validate_data(self, data: SCIMDataContainer) -> ValidationIssues:
        issues = ValidationIssues()
        for attr in self.attrs.top_level:
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
    known_schemas = [item.lower() for item in known_schemas]
    main_schema_included = False
    mismatch = False
    for schema in schemas_:
        if schema == main_schema:
            main_schema_included = True

        elif schema not in known_schemas and not mismatch:
            issues.add(
                issue=ValidationError.unknown_schema(),
                proceed=True,
                location=(schemas.rep.attr,),
            )
            mismatch = True

    if not main_schema_included:
        issues.add(
            issue=ValidationError.missing_main_schema(), proceed=True, location=(schemas.rep.attr,)
        )

    for k, v in data.to_dict().items():
        k_lower = k.lower()
        if k_lower in known_schemas and k_lower not in schemas_:
            issues.add(
                issue=ValidationError.missing_schema_extension(k),
                proceed=True,
                location=(schemas.rep.attr,),
            )
    return issues


def validate_resource_type_consistency(
    resource_type: str,
    expected: str,
) -> ValidationIssues:
    issues = ValidationIssues()
    if resource_type != expected:
        issues.add(
            issue=ValidationError.resource_type_mismatch(
                resource_type=expected,
                provided=resource_type,
            ),
            proceed=True,
            location=("meta", "resourceType"),
        )
    return issues


class ResourceSchema(BaseSchema, abc.ABC):
    def __init__(
        self,
        schema: str,
        attrs: Iterable[Attribute],
        name: str = "",
        description: str = "",
        plural_name: Optional[str] = None,
        attr_overrides: Optional[Dict[str, Attribute]] = None,
    ):
        attr_overrides = attr_overrides or {}
        super().__init__(
            schema=schema,
            attrs=[
                attr_overrides.get("id") or id_,
                attr_overrides.get("externalId") or external_id,
                attr_overrides.get("meta") or meta,
                *attrs,
            ],
        )
        self._schema_extensions: Dict[str, bool] = {}
        self._name = name
        self._plural_name = plural_name or name
        self._description = description

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
        return [self.schema] + list(self._schema_extensions)

    @property
    def schema_extensions(self) -> List[str]:
        return list(self._schema_extensions)

    def with_extension(self, extension: "SchemaExtension", required: bool = False) -> None:
        if extension.schema in map(lambda x: x.lower(), self.schemas):
            raise ValueError(f"extension {extension!r} already in {self!r} schema")

        self._schema_extensions[extension.schema] = required

        bounded_attrs = []
        for attr in extension.attrs:
            bounded_attrs.append(
                self._bound_attr_to_schema(
                    attr=attr,
                    attr_rep=AttrRep(extension.schema, attr.rep.attr, extension=True),
                )
            )
            if isinstance(attr, ComplexAttribute):
                for sub_attr in attr.attrs:
                    bounded_attrs.append(
                        self._bound_attr_to_schema(
                            attr=sub_attr,
                            attr_rep=AttrRep(
                                extension.schema, attr.rep.attr, sub_attr.rep.attr, extension=True
                            ),
                        )
                    )
        self._attrs = Attributes(list(self._attrs) + bounded_attrs)

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


def get_schema_rep(schema: ResourceSchema) -> Dict[str, Any]:
    return {
        "id": schema.schema,
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Schema"],
        "name": schema.name,
        "description": schema.description,
        "attributes": [attr.to_dict() for attr in schema.attrs.top_level],
        "meta": {
            "resourceType": "Schema",
        },
    }


class SchemaExtension:
    def __init__(
        self,
        schema: str,
        attrs: Iterable[Attribute],
        name: str = "",
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

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.schema,
            "name": self.name,
            "description": self.description,
            "attributes": [attr.to_dict() for attr in self.attrs],
        }
