from typing import List, Tuple, Union

from src.data import type as type_
from src.data.attributes import (
    Attribute,
    AttributeIssuer,
    AttributeMutability,
    ComplexAttribute,
)
from src.data.container import Invalid, Missing, SCIMDataContainer
from src.data.schemas import BaseSchema, ResourceSchema
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


def dump_attributes(
    value: List[SCIMDataContainer],
) -> Tuple[List[Union[Invalid, SCIMDataContainer]], ValidationIssues]:
    issues = ValidationIssues()
    for i, item in enumerate(value):
        attr_type = item[_attributes__type.rep]
        sub_attributes = item[_attributes__sub_attributes.rep]
        if sub_attributes not in [Missing, None]:
            if attr_type != "complex":
                del item[_attributes__sub_attributes.rep]
            else:
                dumped, issues_ = attributes.dump(sub_attributes)
                issues.merge(
                    issues_,
                    location=(i, _attributes__sub_attributes.rep.attr),
                )
                item[_attributes__sub_attributes.rep] = dumped
        if attr_type == "string":
            if item[_attributes__case_exact.rep] in [None, Missing]:
                issues.add(
                    issue=ValidationError.missing(),
                    location=(i, _attributes__case_exact.rep),
                    proceed=False,
                )
        else:
            del item[_attributes__case_exact.rep]
    return value, issues


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
    complex_dumpers=[dump_attributes],
)


class Schema(ResourceSchema):
    def __init__(self):
        super().__init__(
            schema="urn:ietf:params:scim:schemas:core:2.0:Schema",
            attrs=[name, description, attributes],
            name="Schema",
            attr_overrides={"id": id_},
        )
