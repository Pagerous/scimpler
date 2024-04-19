from typing import List

from src.data.attributes import (
    AttributeIssuer,
    AttributeMutability,
    Boolean,
    Complex,
    String,
    Unknown,
)
from src.data.container import Missing, SCIMDataContainer
from src.data.schemas import ResourceSchema
from src.error import ValidationError, ValidationIssues

id_ = String(
    name="id",
    mutability=AttributeMutability.READ_ONLY,
    issuer=AttributeIssuer.SERVER,
)


name = String(
    name="name",
    mutability=AttributeMutability.READ_ONLY,
    issuer=AttributeIssuer.SERVER,
)


description = String(
    name="description",
    mutability=AttributeMutability.READ_ONLY,
    issuer=AttributeIssuer.SERVER,
)


_attributes__name = String(
    name="name",
    required=True,
    mutability=AttributeMutability.READ_ONLY,
    issuer=AttributeIssuer.SERVER,
)

_attributes__type = String(
    name="type",
    canonical_values=["string", "integer", "boolean", "reference", "dateTime", "binary", "complex"],
    restrict_canonical_values=False,
    required=True,
    mutability=AttributeMutability.READ_ONLY,
    issuer=AttributeIssuer.SERVER,
)

_attributes__sub_attributes = Unknown(
    name="subAttributes",
    mutability=AttributeMutability.READ_ONLY,
    issuer=AttributeIssuer.SERVER,
)

_attributes__multi_valued = Boolean(
    name="multiValued",
    required=True,
    mutability=AttributeMutability.READ_ONLY,
    issuer=AttributeIssuer.SERVER,
)

_attributes__description = String(
    name="description",
    mutability=AttributeMutability.READ_ONLY,
    issuer=AttributeIssuer.SERVER,
)

_attributes__required = Boolean(
    name="required",
    required=True,
    mutability=AttributeMutability.READ_ONLY,
    issuer=AttributeIssuer.SERVER,
)

_attributes__canonical_values = Unknown(
    name="canonicalValues",
    multi_valued=True,
    mutability=AttributeMutability.READ_ONLY,
    issuer=AttributeIssuer.SERVER,
)

_attributes__case_exact = Boolean(
    name="caseExact",
    mutability=AttributeMutability.READ_ONLY,
    issuer=AttributeIssuer.SERVER,
)

_attributes__mutability = String(
    name="mutability",
    canonical_values=["readOnly", "readWrite", "immutable", "writeOnly"],
    restrict_canonical_values=True,
    required=True,
    mutability=AttributeMutability.READ_ONLY,
    issuer=AttributeIssuer.SERVER,
)

_attributes__returned = String(
    name="returned",
    canonical_values=["always", "never", "default", "request"],
    restrict_canonical_values=True,
    required=True,
    mutability=AttributeMutability.READ_ONLY,
    issuer=AttributeIssuer.SERVER,
)

_attributes__uniqueness = String(
    name="uniqueness",
    canonical_values=["none", "server", "global"],
    restrict_canonical_values=True,
    required=True,
    mutability=AttributeMutability.READ_ONLY,
    issuer=AttributeIssuer.SERVER,
)

_attributes__reference_types = String(
    name="referenceTypes",
    multi_valued=True,
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
            issues.add_error(
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
                item.set(_attributes__sub_attributes.rep, attributes.dump(sub_attributes))
        if attr_type != "string":
            item.pop(_attributes__case_exact.rep)
    return value


attributes = Complex(
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


Schema = ResourceSchema(
    schema="urn:ietf:params:scim:schemas:core:2.0:Schema",
    attrs=[name, description, attributes],
    name="Schema",
    attr_overrides={"id": id_},
)
