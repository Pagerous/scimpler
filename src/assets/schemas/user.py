from src.data import type as type_
from src.data.attributes import (
    Attribute,
    AttributeMutability,
    AttributeReturn,
    AttributeUniqueness,
    ComplexAttribute,
)
from src.data.schemas import ResourceSchema, SchemaExtension

user_name = Attribute(
    name="userName",
    type_=type_.String,
    required=True,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.SERVER,
)

_name__formatted = Attribute(
    name="formatted",
    type_=type_.String,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

_name__family_name = Attribute(
    name="familyName",
    type_=type_.String,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

_name__given_name = Attribute(
    name="givenName",
    type_=type_.String,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

_name__middle_name = Attribute(
    name="middleName",
    type_=type_.String,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

_name__honorific_prefix = Attribute(
    name="honorificPrefix",
    type_=type_.String,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

_name__honorific_suffix = Attribute(
    name="honorificSuffix",
    type_=type_.String,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

# TODO: warn if "formatted" does not contain information from all the other sub-attributes
name = ComplexAttribute(
    sub_attributes=[
        _name__formatted,
        _name__family_name,
        _name__given_name,
        _name__middle_name,
        _name__honorific_prefix,
        _name__honorific_suffix,
    ],
    name="name",
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

# TODO: warn if 'displayName' does not match any of: 'userName', 'name' (any of its sub-attributes)
display_name = Attribute(
    name="displayName",
    type_=type_.String,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

# TODO: warn if 'nickName' is equal to 'username'
nick_name = Attribute(
    name="nickName",
    type_=type_.String,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

profile_url = Attribute(
    name="profileUrl",
    type_=type_.ExternalReference,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

title = Attribute(
    name="title",
    type_=type_.String,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

user_type = Attribute(
    name="userType",
    type_=type_.String,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

# TODO: write proper validator for this field according to: https://www.rfc-editor.org/rfc/rfc7231#section-5.3.5
preferred_language = Attribute(
    name="preferredLanguage",
    type_=type_.String,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

# TODO: write proper validator for this field according to: https://www.rfc-editor.org/rfc/rfc7231#section-5.3.5
locale = Attribute(
    name="locale",
    type_=type_.String,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

# TODO: write proper validator for this field according to: https://www.rfc-editor.org/rfc/rfc6557 ("Olson")
timezone = Attribute(
    name="timezone",
    type_=type_.String,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

active = Attribute(
    name="active",
    type_=type_.Boolean,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

# TODO: make password preparation according to https://www.rfc-editor.org/rfc/rfc7644#section-7.8
password = Attribute(
    name="password",
    type_=type_.String,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.WRITE_ONLY,
    returned=AttributeReturn.NEVER,
    uniqueness=AttributeUniqueness.NONE,
)

_email_value = Attribute(
    name="value",
    type_=type_.String,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

_email_display = Attribute(
    name="display",
    type_=type_.String,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

_email_type = Attribute(
    name="type",
    type_=type_.String,
    required=False,
    case_exact=False,
    multi_valued=False,
    canonical_values=["work", "home", "other"],
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

_email_primary = Attribute(
    name="primary",
    type_=type_.Boolean,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

emails = ComplexAttribute(
    sub_attributes=[
        _email_value,
        _email_type,
        _email_display,
        _email_primary,
    ],
    name="emails",
    required=False,
    multi_valued=True,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

# TODO: make proper validation (warn) according to RFC3966 https://datatracker.ietf.org/doc/html/rfc3966
_phone_number_value = Attribute(
    name="value",
    type_=type_.String,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

_phone_number_display = Attribute(
    name="display",
    type_=type_.String,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

_phone_number_type = Attribute(
    name="type",
    type_=type_.String,
    required=False,
    case_exact=False,
    multi_valued=False,
    canonical_values=["work", "home", "mobile", "fax", "pager", "other"],
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

_phone_number_primary = Attribute(
    name="primary",
    type_=type_.Boolean,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

phone_numbers = ComplexAttribute(
    sub_attributes=[
        _phone_number_value,
        _phone_number_type,
        _phone_number_display,
        _phone_number_primary,
    ],
    name="phoneNumbers",
    required=False,
    multi_valued=True,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

# TODO: warn if value contain whitespaces and isn't lowercase
_ims_value = Attribute(
    name="value",
    type_=type_.String,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

_ims_display = Attribute(
    name="display",
    type_=type_.String,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

# no canonical values included, as those presented in RFC 7643 are obsolete
# and does not contain modern tools
_ims_type = Attribute(
    name="type",
    type_=type_.String,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

_ims_primary = Attribute(
    name="primary",
    type_=type_.Boolean,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

ims = ComplexAttribute(
    sub_attributes=[
        _ims_value,
        _ims_type,
        _ims_display,
        _ims_primary,
    ],
    name="ims",
    required=False,
    multi_valued=True,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

_photos_value = Attribute(
    name="value",
    type_=type_.ExternalReference,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

_photos_display = Attribute(
    name="display",
    type_=type_.String,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

_photos_type = Attribute(
    name="type",
    type_=type_.String,
    required=False,
    case_exact=False,
    canonical_values=["photo", "thumbnail"],
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

_photos_primary = Attribute(
    name="primary",
    type_=type_.Boolean,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

photos = ComplexAttribute(
    sub_attributes=[
        _photos_value,
        _photos_type,
        _photos_display,
        _photos_primary,
    ],
    name="photos",
    required=False,
    multi_valued=True,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

_addresses_formatted = Attribute(
    name="formatted",
    type_=type_.String,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

_addresses_street_address = Attribute(
    name="streetAddress",
    type_=type_.String,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

_addresses_locality = Attribute(
    name="locality",
    type_=type_.String,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

_addresses_region = Attribute(
    name="region",
    type_=type_.String,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

_addresses_postal_code = Attribute(
    name="postalCode",
    type_=type_.String,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

# TODO: validate according to ISO 3166-1 "alpha-2"
_addresses_country = Attribute(
    name="country",
    type_=type_.String,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

_addresses_type = Attribute(
    name="type",
    type_=type_.String,
    required=False,
    case_exact=False,
    canonical_values=["work", "home", "other"],
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

addresses = ComplexAttribute(
    sub_attributes=[
        _addresses_formatted,
        _addresses_locality,
        _addresses_street_address,
        _addresses_region,
        _addresses_postal_code,
        _addresses_country,
        _addresses_type,
    ],
    name="addresses",
    required=False,
    multi_valued=True,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

# TODO: make validation of correct group id here
_groups_value = Attribute(
    name="value",
    type_=type_.String,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_ONLY,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

_groups_ref = Attribute(
    name="$ref",
    type_=type_.URIReference,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_ONLY,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

_groups_display = Attribute(
    name="display",
    type_=type_.String,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_ONLY,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

_groups_type = Attribute(
    name="type",
    type_=type_.String,
    required=False,
    case_exact=False,
    canonical_values=["direct", "indirect"],
    multi_valued=False,
    mutability=AttributeMutability.READ_ONLY,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

groups = ComplexAttribute(
    sub_attributes=[
        _groups_value,
        _groups_ref,
        _groups_display,
        _groups_type,
    ],
    name="groups",
    required=False,
    multi_valued=True,
    mutability=AttributeMutability.READ_ONLY,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

_entitlements_value = Attribute(
    name="value",
    type_=type_.String,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

_entitlements_display = Attribute(
    name="display",
    type_=type_.String,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

_entitlements_type = Attribute(
    name="type",
    type_=type_.String,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

_entitlements_primary = Attribute(
    name="primary",
    type_=type_.Boolean,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

entitlements = ComplexAttribute(
    sub_attributes=[
        _entitlements_value,
        _entitlements_display,
        _entitlements_type,
        _entitlements_primary,
    ],
    name="entitlements",
    required=False,
    multi_valued=True,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

_roles_value = Attribute(
    name="value",
    type_=type_.String,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

_roles_display = Attribute(
    name="display",
    type_=type_.String,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

_roles_type = Attribute(
    name="type",
    type_=type_.String,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

_roles_primary = Attribute(
    name="primary",
    type_=type_.Boolean,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

roles = ComplexAttribute(
    sub_attributes=[
        _roles_value,
        _roles_display,
        _roles_type,
        _roles_primary,
    ],
    name="roles",
    required=False,
    multi_valued=True,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

_x509_certificates_value = Attribute(
    name="value",
    type_=type_.Binary,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

_x509_certificates_display = Attribute(
    name="display",
    type_=type_.String,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

_x509_certificates_type = Attribute(
    name="type",
    type_=type_.String,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

_x509_certificates_primary = Attribute(
    name="primary",
    type_=type_.Boolean,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

x509_certificates = ComplexAttribute(
    sub_attributes=[
        _x509_certificates_value,
        _x509_certificates_display,
        _x509_certificates_type,
        _x509_certificates_primary,
    ],
    name="x509Certificates",
    required=False,
    multi_valued=True,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)


# BELOW ATTRS FROM ENTERPRISE EXTENSION


employee_number = Attribute(
    name="employeeNumber",
    type_=type_.String,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

cost_center = Attribute(
    name="costCenter",
    type_=type_.String,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

organization = Attribute(
    name="organization",
    type_=type_.String,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

division = Attribute(
    name="division",
    type_=type_.String,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

department = Attribute(
    name="department",
    type_=type_.String,
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)


_manager__value = Attribute(
    name="value",
    type_=type_.String,
    multi_valued=False,
    required=False,
    case_exact=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.NONE,
)

_manager__ref = Attribute(
    name="$ref",
    type_=type_.SCIMReference,
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
    type_=type_.String,
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


class User(ResourceSchema):
    def __init__(self):
        super().__init__(
            schema="urn:ietf:params:scim:schemas:core:2.0:User",
            attrs=[
                user_name,
                name,
                display_name,
                nick_name,
                profile_url,
                title,
                user_type,
                preferred_language,
                locale,
                timezone,
                active,
                password,
                emails,
                phone_numbers,
                ims,
                photos,
                addresses,
                groups,
                entitlements,
                roles,
                x509_certificates,
            ],
            name="User",
            plural_name="Users",
        )
        self.with_extension(
            SchemaExtension(
                schema="urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
                attrs=[
                    employee_number,
                    cost_center,
                    division,
                    department,
                    organization,
                    manager,
                ],
                name="Enterprise User",
            )
        )
