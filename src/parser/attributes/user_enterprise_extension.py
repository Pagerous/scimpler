from ..attributes import type as at
from .attributes import (
    Attribute,
    AttributeMutability,
    AttributeReturn,
    AttributeUniqueness,
    ComplexAttribute,
)

employee_number = Attribute(
    name="employeeNumber",
    type_=at.String,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

cost_center = Attribute(
    name="costCenter",
    type_=at.String,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

organization = Attribute(
    name="organization",
    type_=at.String,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

division = Attribute(
    name="division",
    type_=at.String,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

department = Attribute(
    name="department",
    type_=at.String,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)


_manager__value = Attribute(
    name="value",
    type_=at.String,
    multi_valued=False,
    required=False,
    case_exact=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

_manager__ref = Attribute(
    name="$ref",
    type_=at.SCIMReference,
    reference_types=["User"],
    multi_valued=False,
    required=False,
    case_exact=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

_manager__display_name = Attribute(
    name="displayName",
    type_=at.String,
    multi_valued=False,
    required=False,
    case_exact=False,
    mutability=AttributeMutability.READ_ONLY,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

manager = ComplexAttribute(
    sub_attributes=[
        _manager__value,
        _manager__ref,
        _manager__display_name,
    ],
    name="manager",
    required=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)
