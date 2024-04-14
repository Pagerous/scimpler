from typing import List

from src.data import type as type_
from src.data.attributes import (
    Attribute,
    AttributeIssuer,
    AttributeMutability,
    ComplexAttribute,
)
from src.data.container import Missing, SCIMDataContainer
from src.data.schemas import ResourceSchema
from src.error import ValidationError, ValidationIssues

id_ = Attribute(
    name="id",
    type_=type_.String,
    mutability=AttributeMutability.READ_ONLY,
    issuer=AttributeIssuer.SERVER,
)


name = Attribute(
    name="name",
    type_=type_.String,
    mutability=AttributeMutability.READ_ONLY,
    issuer=AttributeIssuer.SERVER,
)


description = Attribute(
    name="description",
    type_=type_.String,
    mutability=AttributeMutability.READ_ONLY,
    issuer=AttributeIssuer.SERVER,
)


_attributes__name = Attribute(
    name="name",
    type_=type_.String,
    required=True,
    mutability=AttributeMutability.READ_ONLY,
    issuer=AttributeIssuer.SERVER,
)

_attributes__type = Attribute(
    name="type",
    type_=type_.String,
    canonical_values=["string", "integer", "boolean", "reference", "dateTime", "binary", "complex"],
    validate_canonical_values=True,
    required=True,
    mutability=AttributeMutability.READ_ONLY,
    issuer=AttributeIssuer.SERVER,
)

_attributes__sub_attributes = Attribute(
    name="subAttributes",
    type_=type_.Unknown,
    required=False,
    mutability=AttributeMutability.READ_ONLY,
    issuer=AttributeIssuer.SERVER,
)

_attributes__multi_valued = Attribute(
    name="multiValued",
    type_=type_.Boolean,
    required=True,
    mutability=AttributeMutability.READ_ONLY,
    issuer=AttributeIssuer.SERVER,
)

_attributes__description = Attribute(
    name="description",
    type_=type_.String,
    required=False,
    mutability=AttributeMutability.READ_ONLY,
    issuer=AttributeIssuer.SERVER,
)

_attributes__required = Attribute(
    name="required",
    type_=type_.Boolean,
    required=True,
    mutability=AttributeMutability.READ_ONLY,
    issuer=AttributeIssuer.SERVER,
)

_attributes__canonical_values = Attribute(
    name="canonicalValues",
    type_=type_.Unknown,
    multi_valued=True,
    required=False,
    mutability=AttributeMutability.READ_ONLY,
    issuer=AttributeIssuer.SERVER,
)

_attributes__case_exact = Attribute(
    name="caseExact",
    type_=type_.Boolean,
    required=False,
    mutability=AttributeMutability.READ_ONLY,
    issuer=AttributeIssuer.SERVER,
)

_attributes__mutability = Attribute(
    name="mutability",
    type_=type_.String,
    canonical_values=["readOnly", "readWrite", "immutable", "writeOnly"],
    validate_canonical_values=True,
    required=True,
    mutability=AttributeMutability.READ_ONLY,
    issuer=AttributeIssuer.SERVER,
)

_attributes__returned = Attribute(
    name="returned",
    type_=type_.String,
    canonical_values=["always", "never", "default", "request"],
    validate_canonical_values=True,
    required=True,
    mutability=AttributeMutability.READ_ONLY,
    issuer=AttributeIssuer.SERVER,
)

_attributes__uniqueness = Attribute(
    name="uniqueness",
    type_=type_.String,
    canonical_values=["none", "server", "global"],
    validate_canonical_values=True,
    required=True,
    mutability=AttributeMutability.READ_ONLY,
    issuer=AttributeIssuer.SERVER,
)

_attributes__reference_types = Attribute(
    name="referenceTypes",
    type_=type_.String,
    multi_valued=True,
    required=False,
    mutability=AttributeMutability.READ_ONLY,
    issuer=AttributeIssuer.SERVER,
)


def validate_attributes(value: List[SCIMDataContainer]) -> ValidationIssues:
    issues = ValidationIssues()
    for i, item in enumerate(value):
        attr_type = item.get(_attributes__type.rep)
        sub_attributes = item.get(_attributes__sub_attributes.rep)
        if sub_attributes not in [Missing, None]:
            if attr_type == "complex":
                issues.merge(
                    attributes.validate(sub_attributes),
                    location=(i, _attributes__sub_attributes.rep.attr),
                )
        if attr_type == "string" and item.get(_attributes__case_exact.rep) in [None, Missing]:
            issues.add(
                issue=ValidationError.missing(),
                location=(i, _attributes__case_exact.rep),
                proceed=False,
            )
    return issues


def dump_attributes(value: List[SCIMDataContainer]) -> List[SCIMDataContainer]:
    for i, item in enumerate(value):
        attr_type = item.get(_attributes__type.rep)
        sub_attributes = item.get(_attributes__sub_attributes.rep)
        if sub_attributes not in [Missing, None]:
            if attr_type != "complex":
                item.pop(_attributes__sub_attributes.rep)
            else:
                item[_attributes__sub_attributes.rep] = attributes.dump(sub_attributes)
        if attr_type != "string":
            item.pop(_attributes__case_exact.rep)
    return value


attributes = ComplexAttribute(
    sub_attributes=[
        _attributes__name,
        _attributes__type,
        _attributes__sub_attributes,
        _attributes__multi_valued,
        _attributes__description,
        _attributes__required,
        _attributes__canonical_values,
        _attributes__case_exact,
        _attributes__mutability,
        _attributes__returned,
        _attributes__uniqueness,
        _attributes__reference_types,
    ],
    name="attributes",
    multi_valued=True,
    mutability=AttributeMutability.READ_ONLY,
    validators=[validate_attributes],
    dumper=dump_attributes,
)


class Schema(ResourceSchema):
    def __init__(self):
        super().__init__(
            schema="urn:ietf:params:scim:schemas:core:2.0:Schema",
            attrs=[name, description, attributes],
            name="Schema",
            attr_overrides={"id": id_},
        )
