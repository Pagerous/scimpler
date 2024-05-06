import re
import zoneinfo

import iso3166
import phonenumbers
import precis_i18n

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
from src.error import ValidationError, ValidationIssues, ValidationWarning

user_name = String(
    name="userName",
    precis=precis_i18n.get_profile("UsernameCaseMapped"),
    required=True,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    uniqueness=AttributeUniqueness.SERVER,
)


name = Complex(
    sub_attributes=[
        String(
            name="formatted",
            required=False,
            case_exact=False,
            multi_valued=False,
            mutability=AttributeMutability.READ_WRITE,
            returned=AttributeReturn.DEFAULT,
        ),
        String(
            name="familyName",
            required=False,
            case_exact=False,
            multi_valued=False,
            mutability=AttributeMutability.READ_WRITE,
            returned=AttributeReturn.DEFAULT,
        ),
        String(
            name="givenName",
            required=False,
            case_exact=False,
            multi_valued=False,
            mutability=AttributeMutability.READ_WRITE,
            returned=AttributeReturn.DEFAULT,
        ),
        String(
            name="middleName",
            required=False,
            case_exact=False,
            multi_valued=False,
            mutability=AttributeMutability.READ_WRITE,
            returned=AttributeReturn.DEFAULT,
        ),
        String(
            name="honorificPrefix",
            required=False,
            case_exact=False,
            multi_valued=False,
            mutability=AttributeMutability.READ_WRITE,
            returned=AttributeReturn.DEFAULT,
        ),
        String(
            name="honorificSuffix",
            required=False,
            case_exact=False,
            multi_valued=False,
            mutability=AttributeMutability.READ_WRITE,
            returned=AttributeReturn.DEFAULT,
        ),
    ],
    name="name",
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)

display_name = String(
    name="displayName",
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)

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


_ACCEPT_LANGUAGE_REGEX = re.compile(
    r"\s*([a-z]{2})(?:-[A-Z]{2})?(?:\s*;q=([0-9]\.[0-9]))?(?:\s*,|$)"
)


def _validate_preferred_language(value: str) -> ValidationIssues:
    issues = ValidationIssues()
    if _ACCEPT_LANGUAGE_REGEX.fullmatch(value) is None:
        issues.add_error(
            issue=ValidationError.bad_value_syntax(),
            proceed=True,
        )
    return issues


preferred_language = String(
    name="preferredLanguage",
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    validators=[_validate_preferred_language],
)


_LANGUAGE_TAG_REGEX = re.compile(
    "^(((en-GB-oed|i-ami|i-bnn|i-default|i-enochian|i-hak|i-klingon|i-lux|"
    "-mingo|i-navajo|i-pwn|i-tao|i-tay|i-tsu|sgn-BE-FR|sgn-BE-NL|sgn-CH-DE)|(art-lojban|"
    "el-gaulish|no-bok|no-nyn|zh-guoyu|zh-hakka|zh-min|zh-min-nan|zh-xiang))|(("
    "([A-Za-z]{2,3}(-([A-Za-z]{3}(-[A-Za-z]{3}){0,2}))?)|[A-Za-z]{4}|[A-Za-z]{5,8})"
    "(-([A-Za-z]{4}))?(-([A-Za-z]{2}|[0-9]{3}))?(-([A-Za-z0-9]{5,8}"
    "|[0-9][A-Za-z0-9]{3}))*(-([0-9A-WY-Za-wy-z](-[A-Za-z0-9]{2,8})+))*"
    "(-(x(-[A-Za-z0-9]{1,8})+))?)|(x(-[A-Za-z0-9]{1,8})+))$"
)


def _validate_locale(value: str) -> ValidationIssues:
    issues = ValidationIssues()
    if _LANGUAGE_TAG_REGEX.fullmatch(value) is None:
        issues.add_error(
            issue=ValidationError.bad_value_syntax(),
            proceed=True,
        )
    return issues


locale = String(
    name="locale",
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    validators=[_validate_locale],
)


def _validate_timezone(value: str) -> ValidationIssues:
    issues = ValidationIssues()
    try:
        zoneinfo.ZoneInfo(value)
    except zoneinfo.ZoneInfoNotFoundError:
        issues.add_error(
            issue=ValidationError.bad_value_content(),
            proceed=True,
        )
    return issues


timezone = String(
    name="timezone",
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
    validators=[_validate_timezone],
)

active = Boolean(
    name="active",
    required=False,
    multi_valued=False,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)

password = String(
    name="password",
    required=False,
    case_exact=False,
    multi_valued=False,
    mutability=AttributeMutability.WRITE_ONLY,
    returned=AttributeReturn.NEVER,
)


_EMAIL_REGEX = re.compile(
    r"(?:[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*|\""
    r"(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21\x23-\x5b\x5d-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])*\""
    r")@(?:(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?|"
    r"\[(?:(2(5[0-5]|[0-4][0-9])|1[0-9][0-9]|[1-9]?[0-9])\.){3}(?:(2(5[0-5]|[0-4][0-9])"
    r"|1[0-9][0-9]|[1-9]?[0-9])|[a-z0-9-]*[a-z0-9]:"
    r"(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21-\x5a\x53-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])+)])"
)


def _validate_email(value: str) -> ValidationIssues:
    issues = ValidationIssues()
    if _EMAIL_REGEX.fullmatch(value) is None:
        issues.add_error(
            issue=ValidationError.bad_value_syntax(),
            proceed=True,
        )
    return issues


emails = Complex(
    sub_attributes=[
        String(
            name="value",
            required=False,
            case_exact=False,
            multi_valued=False,
            mutability=AttributeMutability.READ_WRITE,
            returned=AttributeReturn.DEFAULT,
            validators=[_validate_email],
        ),
        String(
            name="display",
            required=False,
            case_exact=False,
            multi_valued=False,
            mutability=AttributeMutability.READ_WRITE,
            returned=AttributeReturn.DEFAULT,
        ),
        String(
            name="type",
            required=False,
            case_exact=False,
            multi_valued=False,
            canonical_values=["work", "home", "other"],
            mutability=AttributeMutability.READ_WRITE,
            returned=AttributeReturn.DEFAULT,
        ),
        Boolean(
            name="primary",
            required=False,
            multi_valued=False,
            mutability=AttributeMutability.READ_WRITE,
            returned=AttributeReturn.DEFAULT,
        ),
    ],
    name="emails",
    required=False,
    multi_valued=True,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)


def _validate_phone_number(value: str) -> ValidationIssues:
    issues = ValidationIssues()
    try:
        phonenumbers.parse(value, _check_region=False)
    except phonenumbers.NumberParseException:
        issues.add_warning(issue=ValidationWarning.unexpected_content("not a valid phone number"))
    return issues


phone_numbers = Complex(
    sub_attributes=[
        String(
            name="value",
            required=False,
            case_exact=False,
            multi_valued=False,
            mutability=AttributeMutability.READ_WRITE,
            returned=AttributeReturn.DEFAULT,
            validators=[_validate_phone_number],
        ),
        String(
            name="type",
            required=False,
            case_exact=False,
            multi_valued=False,
            canonical_values=["work", "home", "mobile", "fax", "pager", "other"],
            mutability=AttributeMutability.READ_WRITE,
            returned=AttributeReturn.DEFAULT,
        ),
        String(
            name="display",
            required=False,
            case_exact=False,
            multi_valued=False,
            mutability=AttributeMutability.READ_WRITE,
            returned=AttributeReturn.DEFAULT,
        ),
        Boolean(
            name="primary",
            required=False,
            multi_valued=False,
            mutability=AttributeMutability.READ_WRITE,
            returned=AttributeReturn.DEFAULT,
        ),
    ],
    name="phoneNumbers",
    required=False,
    multi_valued=True,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)

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


def _validate_country(value: str) -> ValidationIssues:
    issues = ValidationIssues()
    if iso3166.countries_by_alpha2.get(value) is None:
        issues.add_error(issue=ValidationError.bad_value_content(), proceed=True)
    return issues


addresses = Complex(
    sub_attributes=[
        String(
            name="formatted",
            required=False,
            case_exact=False,
            multi_valued=False,
            mutability=AttributeMutability.READ_WRITE,
            returned=AttributeReturn.DEFAULT,
        ),
        String(
            name="locality",
            required=False,
            case_exact=False,
            multi_valued=False,
            mutability=AttributeMutability.READ_WRITE,
            returned=AttributeReturn.DEFAULT,
        ),
        String(
            name="streetAddress",
            required=False,
            case_exact=False,
            multi_valued=False,
            mutability=AttributeMutability.READ_WRITE,
            returned=AttributeReturn.DEFAULT,
        ),
        String(
            name="region",
            required=False,
            case_exact=False,
            multi_valued=False,
            mutability=AttributeMutability.READ_WRITE,
            returned=AttributeReturn.DEFAULT,
        ),
        String(
            name="postalCode",
            required=False,
            case_exact=False,
            multi_valued=False,
            mutability=AttributeMutability.READ_WRITE,
            returned=AttributeReturn.DEFAULT,
        ),
        String(
            name="country",
            required=False,
            case_exact=False,
            multi_valued=False,
            mutability=AttributeMutability.READ_WRITE,
            returned=AttributeReturn.DEFAULT,
            validators=[_validate_country],
        ),
        String(
            name="type",
            required=False,
            case_exact=False,
            canonical_values=["work", "home", "other"],
            multi_valued=False,
            mutability=AttributeMutability.READ_WRITE,
            returned=AttributeReturn.DEFAULT,
        ),
    ],
    name="addresses",
    required=False,
    multi_valued=True,
    mutability=AttributeMutability.READ_WRITE,
    returned=AttributeReturn.DEFAULT,
)

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
    description="User Account",
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
        name="EnterpriseUser",
    ),
    required=True,
)
