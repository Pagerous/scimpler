from scimpler.data.attrs import (
    Attribute,
    AttributeIssuer,
    AttributeMutability,
    AttributeReturn,
    AttributeUniqueness,
    Boolean,
    Complex,
    ExternalReference,
    Integer,
    String,
)
from scimpler.data.schemas import BaseResourceSchema


class ServiceProviderConfigSchema(BaseResourceSchema):
    """
    ServiceProviderConfig schema, identified by
    `urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig` URI.

    The default endpoint is `/ServiceProviderConfig`.
    """

    schema = "urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig"
    name = "ServiceProviderConfig"
    endpoint = "/ServiceProviderConfig"
    base_attrs: list[Attribute] = [
        String(
            name="id",
            required=False,
            issuer=AttributeIssuer.SERVICE_PROVIDER,
            case_exact=True,
            multi_valued=False,
            mutability=AttributeMutability.READ_ONLY,
            returned=AttributeReturn.ALWAYS,
            uniqueness=AttributeUniqueness.SERVER,
        ),
        ExternalReference(
            name="documentationUri",
            description=(
                "An HTTP-addressable URL pointing to the "
                "service provider's human-consumable help documentation."
            ),
            mutability=AttributeMutability.READ_ONLY,
        ),
        Complex(
            name="patch",
            description="A complex type that specifies PATCH configuration options.",
            sub_attributes=[
                Boolean(
                    name="supported",
                    description=(
                        "A Boolean value specifying whether or not the operation is supported."
                    ),
                    required=True,
                    mutability=AttributeMutability.READ_ONLY,
                )
            ],
            required=True,
            mutability=AttributeMutability.READ_ONLY,
        ),
        Complex(
            name="bulk",
            description="A complex type that specifies bulk configuration options.",
            sub_attributes=[
                Boolean(
                    name="supported",
                    description=(
                        "A Boolean value specifying whether or not the operation is supported."
                    ),
                    required=True,
                    mutability=AttributeMutability.READ_ONLY,
                ),
                Integer(
                    name="maxOperations",
                    description="An integer value specifying the maximum number of operations.",
                    required=True,
                    mutability=AttributeMutability.READ_ONLY,
                ),
                Integer(
                    name="maxPayloadSize",
                    description="An integer value specifying the maximum payload size in bytes.",
                    required=True,
                    mutability=AttributeMutability.READ_ONLY,
                ),
            ],
            required=True,
            mutability=AttributeMutability.READ_ONLY,
        ),
        Complex(
            name="filter",
            sub_attributes=[
                Boolean(
                    name="supported",
                    description=(
                        "A Boolean value specifying whether or not the operation is supported."
                    ),
                    required=True,
                    mutability=AttributeMutability.READ_ONLY,
                ),
                Integer(
                    name="maxResults",
                    description=(
                        "An integer value specifying the maximum "
                        "number of resources returned in a response."
                    ),
                    required=True,
                    mutability=AttributeMutability.READ_ONLY,
                ),
            ],
            required=True,
            mutability=AttributeMutability.READ_ONLY,
        ),
        Complex(
            name="changePassword",
            description=(
                "A complex type that specifies configuration "
                "options related to changing a password."
            ),
            sub_attributes=[
                Boolean(
                    name="supported",
                    description=(
                        "A Boolean value specifying whether or not the operation is supported."
                    ),
                    required=True,
                    mutability=AttributeMutability.READ_ONLY,
                )
            ],
            required=True,
            mutability=AttributeMutability.READ_ONLY,
        ),
        Complex(
            name="sort",
            description="A complex type that specifies sort result options.",
            sub_attributes=[
                Boolean(
                    name="supported",
                    description=(
                        "A Boolean value specifying whether or not the operation is supported."
                    ),
                    required=True,
                    mutability=AttributeMutability.READ_ONLY,
                )
            ],
            required=True,
            mutability=AttributeMutability.READ_ONLY,
        ),
        Complex(
            name="etag",
            description="A complex type that specifies ETag configuration options.",
            required=True,
            mutability=AttributeMutability.READ_ONLY,
            sub_attributes=[
                Boolean(
                    name="supported",
                    description=(
                        "A Boolean value specifying whether or not the operation is supported."
                    ),
                    required=True,
                    mutability=AttributeMutability.READ_ONLY,
                )
            ],
        ),
        Complex(
            name="authenticationSchemes",
            description="A complex type that specifies supported authentication scheme properties.",
            multi_valued=True,
            mutability=AttributeMutability.READ_ONLY,
            required=True,
            sub_attributes=[
                String(
                    name="type",
                    description=(
                        "The authentication scheme.  This specification defines the "
                        "values 'oauth', 'oauth2', 'oauthbearertoken', 'httpbasic', and "
                        "'httpdigest'"
                    ),
                    required=True,
                    canonical_values=[
                        "oauth",
                        "oauth2",
                        "oauthbearertoken",
                        "httpbasic",
                        "httpdigest",
                    ],
                    mutability=AttributeMutability.READ_ONLY,
                ),
                String(
                    name="name",
                    description="The common authentication scheme name, e.g., HTTP Basic.",
                    required=True,
                    mutability=AttributeMutability.READ_ONLY,
                ),
                String(
                    name="description",
                    description="A description of the authentication scheme.",
                    required=True,
                    mutability=AttributeMutability.READ_ONLY,
                ),
                ExternalReference(
                    name="specUri",
                    description=(
                        "An HTTP-addressable URL pointing to the "
                        "authentication scheme's specification."
                    ),
                    mutability=AttributeMutability.READ_ONLY,
                ),
                ExternalReference(
                    name="documentationUri",
                    description=(
                        "An HTTP-addressable URL pointing to the "
                        "authentication scheme's usage documentation."
                    ),
                    mutability=AttributeMutability.READ_ONLY,
                ),
            ],
        ),
    ]
