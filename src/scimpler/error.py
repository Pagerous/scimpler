from collections import defaultdict
from enum import Enum
from typing import Any, Collection, Iterator, Optional, Sequence, TypedDict, Union

from typing_extensions import NotRequired


class ScimErrorType(str, Enum):
    INVALID_FILTER = "invalidFilter"
    TOO_MANY = "tooMany"
    UNIQUENESS = "uniqueness"
    MUTABILITY = "mutability"
    INVALID_SYNTAX = "invalidSyntax"
    INVALID_PATH = "invalidPath"
    NO_TARGET = "noTarget"
    INVALID_VALUE = "invalidValue"
    INVALID_VERS = "invalidVers"
    SENSITIVE = "sensitive"


INVALID_FILTER = {
    "status": "400",
    "scimType": ScimErrorType.INVALID_FILTER,
    "detail": (
        "The specified filter syntax is invalid, "
        "or the specified attribute and filter comparison combination is not supported."
    ),
}


TOO_MANY = {
    "status": "400",
    "scimType": ScimErrorType.TOO_MANY,
    "detail": (
        "The specified filter yields many more results than the server is willing to calculate"
        "or process."
    ),
}


UNIQUENESS = {
    "status": "400",
    "scimType": ScimErrorType.UNIQUENESS,
    "detail": "One or more of the attribute values are already in use or are reserved.",
}


MUTABILITY = {
    "status": "400",
    "scimType": ScimErrorType.MUTABILITY,
    "detail": (
        "The attempted modification is not compatible with the target attribute's mutability "
        "or current state."
    ),
}


INVALID_SYNTAX = {
    "status": "400",
    "scimType": ScimErrorType.INVALID_SYNTAX,
    "detail": (
        "The request body message structure was invalid or did not conform to the request schema."
    ),
}


INVALID_PATH = {
    "status": "400",
    "scimType": ScimErrorType.INVALID_PATH,
    "detail": "The 'path' attribute was invalid or malformed.",
}


NO_TARGET = {
    "status": "400",
    "scimType": ScimErrorType.NO_TARGET,
    "detail": (
        "The specified 'path' did not yield an attribute or attribute value "
        "that could be operated on."
    ),
}


INVALID_VALUE = {
    "status": "400",
    "scimType": ScimErrorType.INVALID_VALUE,
    "detail": (
        "A required value was missing, or the value specified was not compatible "
        "with the operation or attribute type, or resource schema."
    ),
}


INVALID_VERS = {
    "status": "400",
    "scimType": ScimErrorType.INVALID_VERS,
    "detail": "The specified SCIM protocol version is not supported.",
}


SENSITIVE = {
    "status": "400",
    "scimType": ScimErrorType.SENSITIVE,
    "detail": (
        "The specified request cannot be completed, "
        "due to the passing of sensitive information in a request URI."
    ),
}


class ValidationError:
    """
    Represents a validation error. Uniquely identified by the error code.

    Pre-formatted messages stored in `message_by_code` can be modified, as long as embedded
    string parameters stay the same.
    """

    message_by_code = {
        1: "bad value syntax",
        2: "bad type, expecting '{expected}'",
        3: "bad encoding, expecting '{expected}'",
        4: "bad value content",
        5: "missing",
        6: "must not be provided",
        7: "must not be returned",
        8: "must be equal to {value}",
        9: "must be one of: {expected_values}",
        10: "contains duplicates, which are not allowed",
        11: "can not be used together with {other!r}",
        12: "missing main schema",
        13: "missing schema extension {extension!r}",
        14: "unknown schema",
        15: "'primary' attribute set to 'True' MUST appear no more than once",
        16: "bad SCIM reference, allowed resources: {allowed_resources}",
        17: "bad attribute name {attribute!r}",
        18: "error status must be greater or equal to 300 and lesser than 600",
        19: "bad status code, expecting '{expected}'",
        20: "bad number of resources, {reason}",
        21: "does not match the filter",
        22: "resources are not sorted",
        23: "value must be resource type endpoint",
        24: "value must be resource object endpoint",
        25: "unknown bulk operation resource",
        26: "too many operations in bulk (max {max})",
        27: "too many errors in bulk (max {max})",
        28: "unknown modification target",
        29: "attribute can not be modified",
        30: "attribute can not be deleted",
        31: "value or operation not supported",
        # Error codes specific to filter validation
        100: "one of brackets is not opened / closed",
        101: "one of complex attribute brackets is not opened / closed",
        102: "sub-attribute {sub_attr!r} of {attr!r} can not be complex",
        103: "missing operand for operator '{operator}' in expression '{expression}'",
        104: "unknown operator '{operator}' in expression '{expression}'",
        105: "no expression or empty expression inside grouping operator",
        106: "unknown expression '{expression}'",
        107: "complex attribute group can not contain inner complex attributes or square brackets",
        108: "complex attribute group {attribute!r} has no expression",
        109: "bad operand {value!r}",
        110: "operand {value!r} is not compatible with {operator!r} operator",
    }

    def __init__(
        self,
        code: int,
        scim_error: Union[str, ScimErrorType],
        message: Optional[str] = None,
        **context: Any,
    ):
        """
        Args:
            code: The error code. Can be one of built-in error_codes (see `message_by_code`
                attribute) or custom. If custom, it must be greater than 1000.
            scim_error: SCIM error corresponding to the validation error.
            message: Error message. Can replace built-in message or be specified for custom
                validation error.
            **context: Parameters passed to pre-formatted messages.
        """
        if code not in self.message_by_code and code <= 1000:
            raise ValueError("error code for custom validation error must be greater than 1000")
        self.code = code
        if message is None:
            message = "" if code > 1000 else self.message_by_code[code].format(**context)
        self.message = message
        self.context = context
        self.scim_error = ScimErrorType(scim_error)

    @classmethod
    def bad_value_syntax(cls, scim_error: str = ScimErrorType.INVALID_SYNTAX):
        return cls(code=1, scim_error=scim_error)

    @classmethod
    def bad_type(cls, expected: str, scim_error: str = ScimErrorType.INVALID_VALUE):
        return cls(code=2, scim_error=scim_error, expected=expected)

    @classmethod
    def bad_encoding(cls, expected: str, scim_error: str = ScimErrorType.INVALID_VALUE):
        return cls(code=3, scim_error=scim_error, expected=expected)

    @classmethod
    def bad_value_content(cls, scim_error: str = ScimErrorType.INVALID_VALUE):
        return cls(code=4, scim_error=scim_error)

    @classmethod
    def missing(cls, scim_error: str = ScimErrorType.INVALID_VALUE):
        return cls(code=5, scim_error=scim_error)

    @classmethod
    def must_not_be_provided(cls, scim_error: str = ScimErrorType.INVALID_VALUE):
        return cls(code=6, scim_error=scim_error)

    @classmethod
    def must_not_be_returned(cls, scim_error: str = ScimErrorType.INVALID_VALUE):
        return cls(code=7, scim_error=scim_error)

    @classmethod
    def must_be_equal_to(cls, value: Any, scim_error: str = ScimErrorType.INVALID_VALUE):
        return cls(code=8, scim_error=scim_error, value=value)

    @classmethod
    def must_be_one_of(
        cls,
        expected_values: Collection[Any],
        scim_error: str = ScimErrorType.INVALID_VALUE,
    ):
        return cls(code=9, scim_error=scim_error, expected_values=expected_values)

    @classmethod
    def duplicated_values(cls, scim_error: str = ScimErrorType.INVALID_VALUE):
        return cls(code=10, scim_error=scim_error)

    @classmethod
    def can_not_be_used_together(cls, other: str, scim_error: str = ScimErrorType.INVALID_VALUE):
        return cls(code=11, scim_error=scim_error, other=other)

    @classmethod
    def missing_main_schema(cls, scim_error: str = ScimErrorType.INVALID_VALUE):
        return cls(code=12, scim_error=scim_error)

    @classmethod
    def missing_schema_extension(
        cls,
        extension: str,
        scim_error: str = ScimErrorType.INVALID_VALUE,
    ):
        return cls(code=13, scim_error=scim_error, extension=extension)

    @classmethod
    def unknown_schema(cls, scim_error: str = ScimErrorType.INVALID_VALUE):
        return cls(code=14, scim_error=scim_error)

    @classmethod
    def multiple_primary_values(cls, scim_error: str = ScimErrorType.INVALID_VALUE):
        return cls(code=15, scim_error=scim_error)

    @classmethod
    def bad_scim_reference(
        cls,
        allowed_resources: Collection[str],
        scim_error: str = ScimErrorType.INVALID_VALUE,
    ):
        return cls(code=16, scim_error=scim_error, allowed_resources=list(allowed_resources))

    @classmethod
    def bad_attribute_name(cls, attribute: str, scim_error: str = ScimErrorType.INVALID_VALUE):
        return cls(code=17, scim_error=scim_error, attribute=attribute)

    @classmethod
    def bad_status_code(cls, expected: int, scim_error: str = ScimErrorType.INVALID_VALUE):
        return cls(code=19, scim_error=scim_error, expected=expected)

    @classmethod
    def bad_number_of_resources(cls, reason: str, scim_error: str = ScimErrorType.INVALID_VALUE):
        return cls(code=20, scim_error=scim_error, reason=reason)

    @classmethod
    def resources_not_filtered(cls, scim_error: str = ScimErrorType.INVALID_VALUE):
        return cls(code=21, scim_error=scim_error)

    @classmethod
    def resources_not_sorted(cls, scim_error: str = ScimErrorType.INVALID_VALUE):
        return cls(code=22, scim_error=scim_error)

    @classmethod
    def unknown_operation_resource(cls, scim_error: str = ScimErrorType.INVALID_VALUE):
        return cls(code=25, scim_error=scim_error)

    @classmethod
    def too_many_bulk_operations(cls, max_: int, scim_error: str = ScimErrorType.INVALID_VALUE):
        return cls(code=26, scim_error=scim_error, max=max_)

    @classmethod
    def too_many_errors_in_bulk(cls, max_: int, scim_error: str = ScimErrorType.INVALID_VALUE):
        return cls(code=27, scim_error=scim_error, max=max_)

    @classmethod
    def unknown_modification_target(cls, scim_error: str = ScimErrorType.NO_TARGET):
        return cls(code=28, scim_error=scim_error)

    @classmethod
    def attribute_can_not_be_modified(cls, scim_error: str = ScimErrorType.MUTABILITY):
        return cls(code=29, scim_error=scim_error)

    @classmethod
    def attribute_can_not_be_deleted(cls, scim_error: str = ScimErrorType.MUTABILITY):
        return cls(code=30, scim_error=scim_error)

    @classmethod
    def not_supported(cls, scim_error: str = ScimErrorType.INVALID_VALUE):
        return cls(code=31, scim_error=scim_error)

    @classmethod
    def bracket_not_opened_or_closed(cls, scim_error: str = ScimErrorType.INVALID_FILTER):
        return cls(code=100, scim_error=scim_error)

    @classmethod
    def complex_attribute_bracket_not_opened_or_closed(
        cls, scim_error: str = ScimErrorType.INVALID_FILTER
    ):
        return cls(code=101, scim_error=scim_error)

    @classmethod
    def complex_sub_attribute(
        cls,
        attr: str,
        sub_attr: str,
        scim_error: str = ScimErrorType.INVALID_FILTER,
    ):
        return cls(code=102, scim_error=scim_error, attr=attr, sub_attr=sub_attr)

    @classmethod
    def missing_operand_for_operator(
        cls,
        operator: str,
        expression: str,
        scim_error: str = ScimErrorType.INVALID_FILTER,
    ):
        return cls(code=103, scim_error=scim_error, operator=operator, expression=expression)

    @classmethod
    def unknown_operator(
        cls, operator: str, expression: str, scim_error: str = ScimErrorType.INVALID_FILTER
    ):
        return cls(code=104, scim_error=scim_error, operator=operator, expression=expression)

    @classmethod
    def empty_filter_expression(cls, scim_error: str = ScimErrorType.INVALID_FILTER):
        return cls(code=105, scim_error=scim_error)

    @classmethod
    def unknown_expression(cls, expression: str, scim_error: str = ScimErrorType.INVALID_FILTER):
        return cls(code=106, scim_error=scim_error, expression=expression)

    @classmethod
    def inner_complex_attribute_or_square_bracket(
        cls, scim_error: str = ScimErrorType.INVALID_FILTER
    ):
        return cls(code=107, scim_error=scim_error)

    @classmethod
    def empty_complex_attribute_expression(
        cls, attribute: str, scim_error: str = ScimErrorType.INVALID_FILTER
    ):
        return cls(code=108, scim_error=scim_error, attribute=attribute)

    @classmethod
    def bad_operand(cls, value: Any, scim_error: str = ScimErrorType.INVALID_FILTER):
        return cls(code=109, scim_error=scim_error, value=value)

    @classmethod
    def non_compatible_operand(
        cls, value: Any, operator: str, scim_error: str = ScimErrorType.INVALID_FILTER
    ):
        return cls(code=110, scim_error=scim_error, value=value, operator=operator)

    def __eq__(self, other):
        if not isinstance(other, ValidationError):
            return False
        return self.code == other.code


class ValidationWarning:
    """
    Represents a validation warning. Uniquely identified by the error code.

    Pre-formatted messages stored in `message_by_code` can be modified, as long as embedded
    string parameters stay the same.
    """

    message_by_code = {
        1: "value should be one of: {expected_values}",
        2: (
            "multi-valued complex attribute should contain a given type-value pair "
            "no more than once"
        ),
        3: "unexpected content, {reason}",
        4: "missing",
        5: "should not equal to {value}",
    }

    def __init__(self, code: int, message: Optional[str] = None, **context: Any):
        """
        Args:
            code: The warning code. Can be one of built-in error_codes (see `message_by_code`
                attribute) or custom. If custom, it must be greater than 1000.
            message: Warning message. Can replace built-in message or be specified for custom
                validation warning.
            **context: Parameters passed to pre-formatted messages.
        """
        if code not in self.message_by_code and code <= 1000:
            raise ValueError("error code for custom validation error must be greater than 1000")
        self.code = code
        if message is None:
            message = "" if code > 1000 else self.message_by_code[code].format(**context)
        self.message = message
        self.context = context

    @classmethod
    def should_be_one_of(cls, expected_values: Collection[Any]):
        return cls(code=1, expected_values=expected_values)

    @classmethod
    def multiple_type_value_pairs(cls):
        return cls(code=2)

    @classmethod
    def unexpected_content(cls, reason: str):
        return cls(code=3, reason=reason)

    @classmethod
    def missing(cls):
        return cls(code=4)

    @classmethod
    def should_not_equal_to(cls, value: Any):
        return cls(code=5, value=value)

    def __eq__(self, other):
        if not isinstance(other, ValidationError):
            return False
        return self.code == other.code


class ValidationIssueDict(TypedDict):
    code: int
    error: NotRequired[str]
    context: NotRequired[dict]


class ValidationIssues:
    """
    Keeps track of validation errors and warnings.
    """

    def __init__(self) -> None:
        self._errors: dict[tuple, list[ValidationError]] = defaultdict(list)
        self._warnings: dict[tuple, list[ValidationWarning]] = defaultdict(list)
        self._stop_proceeding: dict[tuple, set[int]] = defaultdict(set)

    @property
    def errors(self) -> Iterator[tuple[tuple[str, ...], list[ValidationError]]]:
        """Validation errors by locations where they were added."""
        return iter(self._errors.items())

    @property
    def warnings(self) -> Iterator[tuple[tuple[str, ...], list[ValidationWarning]]]:
        """Validation warnings by locations where they were added."""
        return iter(self._warnings.items())

    def merge(
        self,
        issues: "ValidationIssues",
        location: Optional[Sequence[Union[str, int]]] = None,
    ) -> None:
        """
        Merges provided validation `issues` under specified `location`, if specified, in the
        top-level otherwise.
        """
        location = tuple(location or tuple())
        for other_location, errors in issues._errors.items():
            new_location = location + other_location
            self._errors[new_location].extend(errors)
            self._stop_proceeding[new_location].update(
                issues._stop_proceeding.get(other_location, {})
            )
        for other_location, warnings in issues._warnings.items():
            new_location = location + other_location
            self._warnings[new_location].extend(warnings)

    def add_error(
        self,
        issue: ValidationError,
        proceed: bool,
        location: Optional[Sequence[Union[str, int]]] = None,
    ) -> None:
        """
        Adds a validation error under specified `location`, if specified, in the top-level. The
        `proceed` flag is an indicator whether the specified `location` could continue to be
        validated against different conditions (`True`), or further validation should be terminated
        (`False`).
        """
        location = tuple(location or tuple())
        self._errors[location].append(issue)
        if not proceed:
            self._stop_proceeding[location].add(issue.code)

    def add_warning(
        self,
        issue: ValidationWarning,
        location: Optional[Sequence[Union[str, int]]] = None,
    ) -> None:
        """
        Adds a validation warning under specified `location`, if specified, in the top-level.
        """
        location = tuple(location or tuple())
        self._warnings[location].append(issue)

    def get(
        self,
        error_codes: Optional[Collection[int]] = None,
        warning_codes: Optional[Collection[int]] = None,
        location: Optional[Sequence[Union[str, int]]] = None,
    ) -> "ValidationIssues":
        """
        Retrieves validation issues for the specified `location`, or all of them if not specified.
        The returned issues can be filtered by `error_codes` and `warning_codes`.
        """
        copy = ValidationIssues()
        location = tuple(location or tuple())

        errors_copy = {}
        for location_, errors in self._errors.items():
            if location_[: len(location)] != location:
                continue
            errors = [error for error in errors if error_codes is None or error.code in error_codes]
            if errors:
                errors_copy[location_[len(location) :]] = errors
        copy._errors = errors_copy

        warnings_copy = {}
        for location_, warnings in self._warnings.items():
            if location_[: len(location)] != location:
                continue
            warnings = [
                warning
                for warning in warnings
                if warning_codes is None or warning.code in warning_codes
            ]
            if warnings:
                warnings_copy[location_[len(location) :]] = warnings
        copy._warnings = warnings_copy

        stop_proceeding_copy = {}
        for location_, codes in self._stop_proceeding.items():
            if location_[: len(location)] != location:
                continue
            codes = {code for code in codes if not error_codes or code in error_codes}
            if codes:
                stop_proceeding_copy[location_[len(location) :]] = codes
        copy._stop_proceeding = stop_proceeding_copy

        return copy

    def pop(
        self,
        error_codes: Optional[Collection[int]] = None,
        warning_codes: Optional[Collection[int]] = None,
        location: Optional[Sequence[Union[str, int]]] = None,
    ) -> "ValidationIssues":
        """
        Pops validation issues from the specified `location`, or all of them if not specified.
        Additionally, `error_codes` or `warning_codes` should be specified, otherwise nothing
        is popped.
        """
        location = tuple(location or tuple())

        if location not in self._errors:
            return ValidationIssues()

        popped = self.get(
            error_codes=error_codes or [],
            warning_codes=warning_codes or [],
            location=location,
        )

        for location_, errors in popped.errors:
            original_location = (*location, *location_)
            for error in errors:
                self._errors[original_location].remove(error)
                if error.code in self._stop_proceeding.get(original_location, set()):
                    self._stop_proceeding[original_location].remove(error.code)

            if not self._errors[original_location]:
                self._errors.pop(original_location)

            if not self._stop_proceeding.get(original_location, set()):
                self._stop_proceeding.pop(original_location, None)

        for location_, warnings in popped.warnings:
            original_location = (*location, *location_)
            for warning in warnings:
                self._warnings[original_location].remove(warning)

        return popped

    def can_proceed(self, *locations: Sequence[Union[str, int]]) -> bool:
        """
        Returns flag indicating whether validation could proceed given `locations`. If all
        the provided `locations` have no errors, or these errors have not been added with
        `proceed=True`, then `True` is returned.
        """
        if not locations:
            locations = (tuple(),)
        for location in locations:
            location = tuple(location)
            for i in range(len(location) + 1):
                if location[:i] in self._stop_proceeding:
                    return False
        return True

    def has_errors(self, *locations: Sequence[Union[str, int]]) -> bool:
        """
        Returns flag indicating whether any errors have been added under specified `locations`. If
        at least one of the `locations` have errors (regardless of type), `True` is returned.
        """
        if not locations:
            locations = (tuple(),)

        for location in locations:
            for issue_location in self._errors:
                if issue_location[: len(location)] == location:
                    return True

        return False

    def to_dict(self, msg: bool = False, ctx: bool = False) -> dict:
        """
        Converts `ValidationIssues` to a dictionary.
        """
        output: dict = {}
        self._to_dict("_errors", self._errors, output, msg=msg, ctx=ctx)
        self._to_dict("_warnings", self._warnings, output, msg=msg, ctx=ctx)
        return output

    @staticmethod
    def _to_dict(
        key: str, structure: dict, output: dict, msg: bool = False, ctx: bool = False
    ) -> dict:
        for location, errors in structure.items():
            if location:
                current_level = output
                for i, part in enumerate(location):
                    part = str(part)
                    if part not in current_level:
                        current_level[part] = {}
                    if i == len(location) - 1:
                        current_level[part][key] = []
                        for error in errors:
                            current_level[part][key].append(
                                ValidationIssues._issue_to_dict(error, msg=msg, ctx=ctx)
                            )
                    current_level = current_level[part]
            else:
                output[key] = []
                for error in errors:
                    output[key].append(ValidationIssues._issue_to_dict(error, msg=msg, ctx=ctx))

        return output

    @staticmethod
    def _issue_to_dict(
        issue: Union[ValidationError, ValidationWarning],
        msg: bool = False,
        ctx: bool = False,
    ) -> ValidationIssueDict:
        output: ValidationIssueDict = {"code": issue.code}
        if msg:
            output["error"] = issue.message
        if ctx:
            output["context"] = issue.context
        return output
