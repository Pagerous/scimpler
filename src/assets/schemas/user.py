from src.data.attributes import (
    AttributeMutability,
    AttributeReturn,
    AttributeUniqueness,
    Binary,
    Boolean,
    Complex,
    ExternalReference,
    SCIMReference,
    String,
    URIReference,
)
from src.data.schemas import ResourceSchema, SchemaExtension

user_name = String(
    name="userName",
    required=True,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.SERVER,
)

_name__formatted = String(
    name="formatted",
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)

_name__family_name = String(
    name="familyName",
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)

_name__given_name = String(
    name="givenName",
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)

_name__middle_name = String(
    name="middleName",
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)

_name__honorific_prefix = String(
    name="honorificPrefix",
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)

_name__honorific_suffix = String(
    name="honorificSuffix",
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)

# TODO: warn if "formatted" does not contain information from all the other sub-attributes
name = Complex(
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
)

# TODO: warn if 'displayName' does not match any of: 'userName', 'name' (any of its sub-attributes)
display_name = String(
    name="displayName",
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)

# TODO: warn if 'nickName' is equal to 'username'
nick_name = String(
    name="nickName",
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)

profile_url = ExternalReference(
    name="profileUrl",
    required=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)

title = String(
    name="title",
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)

user_type = String(
    name="userType",
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)

# TODO: write proper validator for this field according to: https://www.rfc-editor.org/rfc/rfc7231#section-5.3.5
preferred_language = String(
    name="preferredLanguage",
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)

# TODO: write proper validator for this field according to: https://www.rfc-editor.org/rfc/rfc7231#section-5.3.5
locale = String(
    name="locale",
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)

# TODO: write proper validator for this field according to: https://www.rfc-editor.org/rfc/rfc6557 ("Olson")
timezone = String(
    name="timezone",
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)

active = Boolean(
    name="active",
    required=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)

# TODO: make password preparation according to https://www.rfc-editor.org/rfc/rfc7644#section-7.8
password = String(
    name="password",
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.WRITE_ONLY,
    returned=AttributeReturn.NEVER,
)

_email_value = String(
    name="value",
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)

_email_display = String(
    name="display",
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)

_email_type = String(
    name="type",
    required=False,
    case_exact=False,
    multi_valued=False,
    canonical_values=["work", "home", "other"],
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)

_email_primary = Boolean(
    name="primary",
    required=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)

emails = Complex(
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
)

# TODO: make proper validation (warn) according to RFC3966 https://datatracker.ietf.org/doc/html/rfc3966
_phone_number_value = String(
    name="value",
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)

_phone_number_display = String(
    name="display",
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)

_phone_number_type = String(
    name="type",
    required=False,
    case_exact=False,
    multi_valued=False,
    canonical_values=["work", "home", "mobile", "fax", "pager", "other"],
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)

_phone_number_primary = Boolean(
    name="primary",
    required=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)

phone_numbers = Complex(
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
)

# TODO: warn if value contain whitespaces and isn't lowercase
_ims_value = String(
    name="value",
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)

_ims_display = String(
    name="display",
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)

# no canonical values included, as those presented in RFC 7643 are obsolete
# and does not contain modern tools
_ims_type = String(
    name="type",
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)

_ims_primary = Boolean(
    name="primary",
    required=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)

ims = Complex(
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
)

_photos_value = ExternalReference(
    name="value",
    required=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)

_photos_display = String(
    name="display",
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)

_photos_type = String(
    name="type",
    required=False,
    case_exact=False,
    canonical_values=["photo", "thumbnail"],
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)

_photos_primary = Boolean(
    name="primary",
    required=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)

photos = Complex(
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
)

_addresses_formatted = String(
    name="formatted",
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)

_addresses_street_address = String(
    name="streetAddress",
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)

_addresses_locality = String(
    name="locality",
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)

_addresses_region = String(
    name="region",
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)

_addresses_postal_code = String(
    name="postalCode",
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)

# TODO: validate according to ISO 3166-1 "alpha-2"
_addresses_country = String(
    name="country",
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)

_addresses_type = String(
    name="type",
    required=False,
    case_exact=False,
    canonical_values=["work", "home", "other"],
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)

addresses = Complex(
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
)

# TODO: make validation of correct group id here
_groups_value = String(
    name="value",
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_ONLY,
    returned=AttributeReturn.DEFAULT,
)

_groups_ref = URIReference(
    name="$ref",
    required=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_ONLY,
    returned=AttributeReturn.DEFAULT,
)

_groups_display = String(
    name="display",
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_ONLY,
    returned=AttributeReturn.DEFAULT,
)

_groups_type = String(
    name="type",
    required=False,
    case_exact=False,
    canonical_values=["direct", "indirect"],
    multi_valued=False,
    mutability=AttributeMutability.READ_ONLY,
    returned=AttributeReturn.DEFAULT,
)

groups = Complex(
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
)

_entitlements_value = String(
    name="value",
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)

_entitlements_display = String(
    name="display",
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)

_entitlements_type = String(
    name="type",
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)

_entitlements_primary = Boolean(
    name="primary",
    required=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)

entitlements = Complex(
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
)

_roles_value = String(
    name="value",
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)

_roles_display = String(
    name="display",
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)

_roles_type = String(
    name="type",
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)

_roles_primary = Boolean(
    name="primary",
    required=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)

roles = Complex(
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
)

_x509_certificates_value = Binary(
    name="value",
    required=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)

_x509_certificates_display = String(
    name="display",
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)

_x509_certificates_type = String(
    name="type",
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)

_x509_certificates_primary = Boolean(
    name="primary",
    required=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)

x509_certificates = Complex(
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
)


# BELOW ATTRS FROM ENTERPRISE EXTENSION


employee_number = String(
    name="employeeNumber",
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)

cost_center = String(
    name="costCenter",
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)

organization = String(
    name="organization",
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)

division = String(
    name="division",
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)

department = String(
    name="department",
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)


_manager__value = String(
    name="value",
    multi_valued=False,
    required=False,
    case_exact=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)

_manager__ref = SCIMReference(
    name="$ref",
    reference_types=["User"],
    multi_valued=False,
    required=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)

_manager__display_name = String(
    name="displayName",
    multi_valued=False,
    required=False,
    case_exact=False,
    mutability=AttributeMutability.READ_ONLY,
    returned=AttributeReturn.DEFAULT,
)

manager = Complex(
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


User = ResourceSchema(
    schema="urn:ietf:params:scim:schemas:core:2.0:User",
    name="User",
    plural_name="Users",
    endpoint="/Users",
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
)
User.add_extension(
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
