import abc
from typing import Any, Dict, Iterable, List, Sequence, Tuple, Union

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
from src.data.type import get_scim_type
from src.error import ValidationError, ValidationIssues


def bulk_id_validator(value) -> Tuple[Any, ValidationIssues]:
    issues = ValidationIssues()
    if "bulkId" in value:
        issues.add(
            issue=ValidationError.reserved_keyword("bulkId"),
            proceed=False,
        )
        return Invalid, issues
    return value, issues


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
    parsers=[bulk_id_validator],
    dumpers=[bulk_id_validator],
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
                parsers=attr.parsers,
                dumpers=attr.dumpers,
                complex_parsers=attr.complex_parsers,
                complex_dumpers=attr.complex_dumpers,
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
            parsers=attr.parsers,
            dumpers=attr.dumpers,
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

    @abc.abstractmethod
    def __repr__(self) -> str:
        ...

    def parse(self, data: Any) -> Tuple[Union[Invalid, SCIMDataContainer], ValidationIssues]:
        return self._process(data, method="parse")

    def dump(self, data: Any) -> Tuple[Union[Invalid, SCIMDataContainer], ValidationIssues]:
        return self._process(data, method="dump")

    def _process(
        self, data: Any, method: str
    ) -> Tuple[Union[Invalid, SCIMDataContainer], ValidationIssues]:
        issues = ValidationIssues()
        if data is None:
            issues.add(
                issue=ValidationError.missing(),
                proceed=False,
            )
            data = Invalid
        elif not isinstance(data, (SCIMDataContainer, dict)):
            issues.add(
                issue=ValidationError.bad_type(
                    get_scim_type(SCIMDataContainer), get_scim_type(type(data))
                ),
                proceed=False,
            )
            data = Invalid

        if issues:
            return data, issues

        data, issues_ = self._process_data(data, method)
        issues.merge(issues_)

        schemas_ = data[self._attrs.schemas.rep]
        if issues.can_proceed(("schemas",)) and schemas_:
            issues.merge(
                validate_schemas_field(
                    data=data,
                    schemas_=schemas_,
                    main_schema=self.schema,
                    known_schemas=self.schemas,
                )
            )
        return data, issues

    def _process_data(
        self,
        data: Dict[str, Any],
        method: str,
    ) -> Tuple[SCIMDataContainer, ValidationIssues]:
        issues = ValidationIssues()
        data = SCIMDataContainer(data)
        processed = SCIMDataContainer()
        for attr in self.attrs.top_level:
            value = data[attr.rep]
            if value is Missing:
                continue
            value, issues_ = getattr(attr, method)(value)
            location = (attr.rep.attr,)
            if attr.rep.extension:
                location = (attr.rep.schema,) + location
            issues.merge(
                issues=issues_,
                location=location,
            )
            processed[attr.rep] = value
        return processed, issues


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
    def __init__(self, schema: str, attrs: Iterable[Attribute]):
        super().__init__(
            schema=schema,
            attrs=[
                id_,
                external_id,
                meta,
                *attrs,
            ],
        )
        self._schema_extensions: Dict[str, bool] = {}

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

    def dump(self, data: Any) -> Tuple[Union[Invalid, SCIMDataContainer], ValidationIssues]:
        data, issues = super().dump(data)
        if not issues.can_proceed():
            return data, issues

        if issues.can_proceed(("meta", "resourceType")):
            resource_type = data[self.attrs.meta.attrs.resourcetype.rep]
            if resource_type is not Missing:
                issues.merge(
                    validate_resource_type_consistency(
                        resource_type=resource_type,
                        expected=repr(self),
                    )
                )
        return data, issues


class SchemaExtension:
    def __init__(self, schema: str, attrs: Iterable[Attribute]):
        self._schema = schema
        self._attrs = list(attrs)

    @property
    def schema(self) -> str:
        return self._schema

    @property
    def attrs(self) -> List[Attribute]:
        return self._attrs
