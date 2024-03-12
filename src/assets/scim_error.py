INVALID_FILTER = {
    "status": "400",
    "scimType": "invalidFilter",
    "detail": (
        "The specified filter syntax is invalid, "
        "or the specified attribute and filter comparison combination is not supported."
    ),
}


TOO_MANY = {
    "status": "400",
    "scimType": "tooMany",
    "detail": (
        "The specified filter yields many more results than the server is willing to calculate"
        "or process."
    ),
}


UNIQUENESS = {
    "status": "400",
    "scimType": "uniqueness",
    "detail": "One or more of the attribute values are already in use or are reserved.",
}


MUTABILITY = {
    "status": "400",
    "scimType": "mutability",
    "detail": (
        "The attempted modification is not compatible with the target attribute's mutability "
        "or current state."
    ),
}


INVALID_SYNTAX = {
    "status": "400",
    "scimType": "invalidSyntax",
    "detail": (
        "The request body message structure was invalid or did not conform to the request schema."
    ),
}


INVALID_PATH = {
    "status": "400",
    "scimType": "invalidPath",
    "detail": "The 'path' attribute was invalid or malformed.",
}


NO_TARGET = {
    "status": "400",
    "scimType": "noTarget",
    "detail": (
        "The specified 'path' did not yield an attribute or attribute value "
        "that could be operated on."
    ),
}


INVALID_VALUE = {
    "status": "400",
    "scimType": "invalidValue",
    "detail": (
        "A required value was missing, or the value specified was not compatible "
        "with the operation or attribute type, or resource schema."
    ),
}


INVALID_VERS = {
    "status": "400",
    "scimType": "invalidVers",
    "detail": "The specified SCIM protocol version is not supported.",
}


SENSITIVE = {
    "status": "400",
    "scimType": "sensitive",
    "detail": (
        "The specified request cannot be completed, "
        "due to the passing of sensitive information in a request URI."
    ),
}
