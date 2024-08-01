import re
import zoneinfo
from typing import Optional

import iso3166
import phonenumbers
import precis_i18n

from scimpler.container import SCIMData
from scimpler.data.attrs import (
    Attribute,
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
from scimpler.data.schemas import AttrFilter, ResourceSchema, SchemaExtension
from scimpler.error import ValidationError, ValidationIssues, ValidationWarning

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


def _validate_phone_number(value: str) -> ValidationIssues:
    issues = ValidationIssues()
    try:
        phonenumbers.parse(value, _check_region=False)
    except phonenumbers.NumberParseException:
        issues.add_warning(issue=ValidationWarning.unexpected_content("not a valid phone number"))
    return issues


def _validate_country(value: str) -> ValidationIssues:
    issues = ValidationIssues()
    if iso3166.countries_by_alpha2.get(value) is None:
        issues.add_error(issue=ValidationError.bad_value_content(), proceed=True)
    return issues


def _process_ims_value(value: str) -> str:
    return re.sub(r"\s", "", value.lower())


class UserSchema(ResourceSchema):
    base_attrs: list[Attribute] = [
        String(
            name="userName",
            description=(
                "Unique identifier for the User, typically used by the user to directly "
                "authenticate to the service provider. Each User MUST include a non-empty "
                "userName value. This identifier MUST be unique across "
                "the service provider's entire set of Users."
            ),
            precis=precis_i18n.get_profile("UsernameCaseMapped"),
            required=True,
            uniqueness=AttributeUniqueness.SERVER,
        ),
        Complex(
            name="name",
            description=(
                "The components of the user's real name. "
                "Providers MAY return just the full name as a single string in the "
                "formatted sub-attribute, or they MAY return just the individual "
                "component attributes using the other sub-attributes, or they MAY "
                "return both. If both variants are returned, they SHOULD be "
                "describing the same name, with the formatted name indicating how the "
                "component attributes should be combined."
            ),
            sub_attributes=[
                String(
                    name="formatted",
                    description=(
                        "The full name, including all middle "
                        "names, titles, and suffixes as appropriate, formatted for display "
                        "(e.g., 'Ms. Barbara J Jensen, III')."
                    ),
                ),
                String(
                    name="familyName",
                    description=(
                        "The family name of the User, or "
                        "last name in most Western languages (e.g., 'Jensen' given "
                        "the full name 'Ms. Barbara J Jensen, III')."
                    ),
                ),
                String(
                    name="givenName",
                    description=(
                        "The given name of the User, or "
                        "first name in most Western languages (e.g., 'Barbara' given the "
                        "full name 'Ms. Barbara J Jensen, III')."
                    ),
                ),
                String(
                    name="middleName",
                    description=(
                        "The middle name(s) of the User "
                        "(e.g., 'Jane' given the full name 'Ms. Barbara J Jensen, III')."
                    ),
                ),
                String(
                    name="honorificPrefix",
                    description=(
                        "The honorific prefix(es) of the User, or "
                        "title in most Western languages (e.g., 'Ms.' given the full name "
                        "'Ms. Barbara J Jensen, III')."
                    ),
                ),
                String(
                    name="honorificSuffix",
                    description=(
                        "The honorific suffix(es) of the User, or "
                        "suffix in most Western languages (e.g., 'III' given the full name "
                        "'Ms. Barbara J Jensen, III')."
                    ),
                ),
            ],
        ),
        String(
            name="displayName",
            description=(
                "The name of the User, suitable for display "
                "to end-users.  The name SHOULD be the full name of the User being "
                "described, if known."
            ),
        ),
        String(
            name="nickName",
            description=(
                "The casual way to address the user in real "
                "life, e.g., 'Bob' or 'Bobby' instead of 'Robert'.  This attribute "
                "SHOULD NOT be used to represent a User's username (e.g., 'bjensen' or "
                "'mpepperidge')."
            ),
        ),
        ExternalReference(
            name="profileUrl",
            description=(
                "A fully qualified URL pointing to a page "
                "representing the User's online profile."
            ),
        ),
        String(
            name="title",
            description="The user's title, such as 'Vice President'",
        ),
        String(
            name="userType",
            description=(
                "Used to identify the relationship between "
                "the organization and the user.  Typical values used might be "
                "'Contractor', 'Employee', 'Intern', 'Temp', 'External', and "
                "'Unknown', but any value may be used."
            ),
        ),
        String(
            name="preferredLanguage",
            description=(
                "Indicates the User's preferred written or "
                "spoken language.  Generally used for selecting a localized user "
                "interface; e.g., 'en_US' specifies the language English and country US."
            ),
            validators=[_validate_preferred_language],
        ),
        String(
            name="locale",
            description=(
                "Used to indicate the User's default location "
                "for purposes of localizing items such as currency, date time format, or "
                "numerical representations."
            ),
            validators=[_validate_locale],
        ),
        String(
            name="timezone",
            description=(
                "The User's time zone in the 'Olson' time zone "
                "database format, e.g., 'America/Los_Angeles'."
            ),
            validators=[_validate_timezone],
        ),
        Boolean(
            name="active",
            description="A Boolean value indicating the User's administrative status.",
        ),
        String(
            name="password",
            description=(
                "The User's cleartext password.  This "
                "attribute is intended to be used as a means to specify an initial "
                "password when creating a new User or to reset an existing User's password."
            ),
            mutability=AttributeMutability.WRITE_ONLY,
            returned=AttributeReturn.NEVER,
        ),
        Complex(
            name="emails",
            description=(
                "Email addresses for the user.  The value "
                "SHOULD be canonicalized by the service provider, e.g., "
                "'bjensen@example.com' instead of 'bjensen@EXAMPLE.COM'. "
                "Canonical type values of 'work', 'home', and 'other'."
            ),
            multi_valued=True,
            sub_attributes=[
                String(
                    name="value",
                    description=(
                        "Email addresses for the user.  The value "
                        "SHOULD be canonicalized by the service provider, e.g., "
                        "'bjensen@example.com' instead of 'bjensen@EXAMPLE.COM'. "
                        "Canonical type values of 'work', 'home', and 'other'."
                    ),
                    validators=[_validate_email],
                ),
                String(
                    name="display",
                    description="A human-readable name, primarily used for display purposes.",
                ),
                String(
                    name="type",
                    description=(
                        "A label indicating the attribute's function, e.g., 'work' " "or 'home'."
                    ),
                    canonical_values=["work", "home", "other"],
                ),
                Boolean(
                    name="primary",
                    description=(
                        "A Boolean value indicating the 'primary' "
                        "or preferred attribute value for this attribute, "
                        "e.g., the preferred mailing address or primary email address.  "
                        "The primary attribute value 'true' MUST appear no more than once."
                    ),
                ),
            ],
        ),
        Complex(
            name="phoneNumbers",
            description=(
                "Phone numbers for the User.  The value "
                "SHOULD be canonicalized by the service provider according to the "
                "format specified in RFC 3966, e.g., 'tel:+1-201-555-0123'. "
                "Canonical type values of 'work', 'home', 'mobile', 'fax', 'pager', "
                "and 'other'."
            ),
            multi_valued=True,
            sub_attributes=[
                String(
                    name="value",
                    description="Phone number of the User.",
                    validators=[_validate_phone_number],
                ),
                String(
                    name="type",
                    description=(
                        "A label indicating the attribute's function, "
                        "e.g., 'work', 'home', 'mobile'."
                    ),
                    canonical_values=["work", "home", "mobile", "fax", "pager", "other"],
                ),
                String(
                    name="display",
                    description="A human-readable name, primarily used for display purposes.",
                ),
                Boolean(
                    name="primary",
                    description=(
                        "A Boolean value indicating the 'primary' "
                        "or preferred attribute value for this attribute, "
                        "e.g., the preferred phone number or primary phone number. "
                        "The primary attribute value 'true' MUST appear no more than once."
                    ),
                ),
            ],
        ),
        Complex(
            name="ims",
            description="Instant messaging addresses for the User.",
            multi_valued=True,
            sub_attributes=[
                String(
                    name="value",
                    description="Instant messaging addresses for the User.",
                    deserializer=_process_ims_value,
                    serializer=_process_ims_value,
                ),
                String(
                    name="type",
                    description="A label indicating the attribute's function",
                ),
                String(
                    name="display",
                    description="A human-readable name, primarily used for display purposes.",
                ),
                Boolean(
                    name="primary",
                    description=(
                        "A Boolean value indicating the 'primary' "
                        "or preferred attribute value for this attribute, "
                        "e.g., the preferred messenger or primary messenger. "
                        "The primary attribute value 'true' MUST appear no more than once."
                    ),
                ),
            ],
        ),
        Complex(
            name="photos",
            description="URLs of photos of the User.",
            multi_valued=True,
            sub_attributes=[
                ExternalReference(
                    name="value",
                    description="URLs of photos of the User.",
                ),
                String(
                    name="type",
                    description=(
                        "A label indicating the attribute's "
                        "function, i.e., 'photo' or 'thumbnail'."
                    ),
                    canonical_values=["photo", "thumbnail"],
                ),
                String(
                    name="display",
                    description="A human-readable name, primarily used for display purposes.",
                ),
                Boolean(
                    name="primary",
                    description=(
                        "A Boolean value indicating the 'primary' "
                        "or preferred attribute value for this attribute, "
                        "e.g., the preferred photo or thumbnail. "
                        "The primary attribute value 'true' MUST appear no more than once."
                    ),
                ),
            ],
        ),
        Complex(
            name="addresses",
            description=(
                "A physical mailing address for this User. "
                "Canonical type values of 'work', 'home', and 'other'.  This attribute "
                "is a complex type with the following sub-attributes."
            ),
            multi_valued=True,
            sub_attributes=[
                String(
                    name="formatted",
                    description=(
                        "The full mailing address, formatted for "
                        "display or use with a mailing label.  This attribute MAY contain "
                        "newlines."
                    ),
                ),
                String(
                    name="locality",
                    description="The city or locality component.",
                ),
                String(
                    name="streetAddress",
                    description=(
                        "The full street address component, "
                        "which may include house number, street name, P.O. box, "
                        "and multi-line extended street address information.  "
                        "This attribute MAY contain newlines."
                    ),
                ),
                String(
                    name="region",
                    description="The state or region component.",
                ),
                String(
                    name="postalCode",
                    description="The zip code or postal code component.",
                ),
                String(
                    name="country",
                    description="The country name component.",
                    validators=[_validate_country],
                ),
                String(
                    name="type",
                    description=(
                        "A label indicating the attribute's " "function, e.g., 'work' or 'home'."
                    ),
                    canonical_values=["work", "home", "other"],
                ),
            ],
        ),
        Complex(
            name="groups",
            description=(
                "A list of groups to which the user belongs, "
                "either through direct membership, through nested groups, or "
                "dynamically calculated."
            ),
            multi_valued=True,
            mutability=AttributeMutability.READ_ONLY,
            sub_attributes=[
                String(
                    name="value",
                    description="The identifier of the User's group.",
                    mutability=AttributeMutability.READ_ONLY,
                ),
                URIReference(
                    name="$ref",
                    description=(
                        "The URI of the corresponding 'Group' "
                        "resource to which the user belongs."
                    ),
                    mutability=AttributeMutability.READ_ONLY,
                ),
                String(
                    name="display",
                    description="A human-readable name, primarily used for display purposes.",
                    mutability=AttributeMutability.READ_ONLY,
                ),
                String(
                    name="type",
                    description=(
                        "A label indicating the attribute's "
                        "function, e.g., 'direct' or 'indirect'."
                    ),
                    canonical_values=["direct", "indirect"],
                    mutability=AttributeMutability.READ_ONLY,
                ),
            ],
        ),
        Complex(
            name="entitlements",
            description=(
                "A list of entitlements for the User that " "represent a thing the User has."
            ),
            multi_valued=True,
            sub_attributes=[
                String(
                    name="value",
                    description="The value of an entitlement.",
                ),
                String(
                    name="display",
                    description="A human-readable name, primarily used for display purposes.",
                ),
                String(name="type", description="A label indicating the attribute's function."),
                Boolean(
                    name="primary",
                    description=(
                        "A Boolean value indicating the 'primary' "
                        "or preferred attribute value for this attribute.  The primary "
                        "attribute value 'true' MUST appear no more than once."
                    ),
                ),
            ],
        ),
        Complex(
            name="roles",
            description=(
                "A list of roles for the User that "
                "collectively represent who the User is, e.g., 'Student', 'Faculty'."
            ),
            multi_valued=True,
            sub_attributes=[
                String(
                    name="value",
                    description="The value of a role.",
                ),
                String(
                    name="display",
                    description="A human-readable name, primarily used for display purposes.",
                ),
                String(name="type", description="A label indicating the attribute's function."),
                Boolean(
                    name="primary",
                    description=(
                        "A Boolean value indicating the 'primary' "
                        "or preferred attribute value for this attribute.  The primary "
                        "attribute value 'true' MUST appear no more than once."
                    ),
                ),
            ],
        ),
        Complex(
            name="x509Certificates",
            description="A list of certificates issued to the User.",
            multi_valued=True,
            sub_attributes=[
                Binary(
                    name="value",
                    description="The value of an X.509 certificate.",
                ),
                String(
                    name="display",
                    description="A human-readable name, primarily used for display purposes",
                ),
                String(
                    name="type",
                    description="A label indicating the attribute's function.",
                ),
                Boolean(
                    name="primary",
                    description=(
                        "A Boolean value indicating the 'primary' "
                        "or preferred attribute value for this attribute.  The primary "
                        "attribute value 'true' MUST appear no more than once."
                    ),
                ),
            ],
        ),
    ]

    def __init__(self, attr_filter: Optional[AttrFilter] = None):
        super().__init__(
            schema="urn:ietf:params:scim:schemas:core:2.0:User",
            name="User",
            plural_name="Users",
            description="User Account",
            endpoint="/Users",
            attr_filter=attr_filter,
        )

    def _validate(self, data: SCIMData, **kwargs) -> ValidationIssues:
        issues = super()._validate(data)
        username = data.get("userName")
        nickname = data.get("nickName")
        if username and nickname and username == nickname:
            issues.add_warning(
                issue=ValidationWarning.should_not_equal_to("'userName' attribute"),
                location=("nickName",),
            )
        return issues


class EnterpriseUserSchemaExtension(SchemaExtension):
    default_attrs: list[Attribute] = [
        String(
            name="employeeNumber",
            description=(
                "Numeric or alphanumeric identifier assigned "
                "to a person, typically based on order of hire or association with an "
                "organization."
            ),
        ),
        String(
            name="costCenter",
            description="Identifies the name of a cost center.",
        ),
        String(
            name="division",
            description="Identifies the name of a division.",
        ),
        String(
            name="department",
            description="Identifies the name of a department.",
        ),
        String(
            name="organization",
            description="Identifies the name of an organization.",
        ),
        Complex(
            name="manager",
            description=(
                "The User's manager.  A complex type that "
                "optionally allows service providers to represent organizational "
                "hierarchy by referencing the 'id' attribute of another User."
            ),
            sub_attributes=[
                String(
                    name="value",
                    description="The id of the SCIM resource representing the User's manager.",
                    required=True,
                ),
                SCIMReference(
                    name="$ref",
                    description="The URI of the SCIM resource representing the User's manager",
                    reference_types=["User"],
                    required=True,
                ),
                String(
                    name="displayName",
                    description="The displayName of the User's manager.",
                    mutability=AttributeMutability.READ_ONLY,
                ),
            ],
        ),
    ]

    def __init__(self, attr_filter: Optional[AttrFilter] = None):
        super().__init__(
            schema="urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
            name="EnterpriseUser",
            attr_filter=attr_filter,
        )
