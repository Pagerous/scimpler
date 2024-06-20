from typing import Optional

from src.error import SCIMErrorType

INVALID_FILTER = {
    "status": "400",
    "scimType": SCIMErrorType.INVALID_FILTER,
    "detail": (
        "The specified filter syntax is invalid, "
        "or the specified attribute and filter comparison combination is not supported."
    ),
}


TOO_MANY = {
    "status": "400",
    "scimType": SCIMErrorType.TOO_MANY,
    "detail": (
        "The specified filter yields many more results than the server is willing to calculate"
        "or process."
    ),
}


UNIQUENESS = {
    "status": "400",
    "scimType": SCIMErrorType.UNIQUENESS,
    "detail": "One or more of the attribute values are already in use or are reserved.",
}


MUTABILITY = {
    "status": "400",
    "scimType": SCIMErrorType.MUTABILITY,
    "detail": (
        "The attempted modification is not compatible with the target attribute's mutability "
        "or current state."
    ),
}


INVALID_SYNTAX = {
    "status": "400",
    "scimType": SCIMErrorType.INVALID_SYNTAX,
    "detail": (
        "The request body message structure was invalid or did not conform to the request schema."
    ),
}


INVALID_PATH = {
    "status": "400",
    "scimType": SCIMErrorType.INVALID_PATH,
    "detail": "The 'path' attribute was invalid or malformed.",
}


NO_TARGET = {
    "status": "400",
    "scimType": SCIMErrorType.NO_TARGET,
    "detail": (
        "The specified 'path' did not yield an attribute or attribute value "
        "that could be operated on."
    ),
}


INVALID_VALUE = {
    "status": "400",
    "scimType": SCIMErrorType.INVALID_VALUE,
    "detail": (
        "A required value was missing, or the value specified was not compatible "
        "with the operation or attribute type, or resource schema."
    ),
}


INVALID_VERS = {
    "status": "400",
    "scimType": SCIMErrorType.INVALID_VERS,
    "detail": "The specified SCIM protocol version is not supported.",
}


SENSITIVE = {
    "status": "400",
    "scimType": SCIMErrorType.SENSITIVE,
    "detail": (
        "The specified request cannot be completed, "
        "due to the passing of sensitive information in a request URI."
    ),
}


def create_error(
    status: int, scim_type: Optional[str] = None, detail: Optional[str] = None
) -> dict:
    output = {"status": str(status)}
    if scim_type:
        output["scimType"] = SCIMErrorType(scim_type).value
    if detail:
        output["detail"] = detail
    return output
