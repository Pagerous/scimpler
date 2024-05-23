from collections import defaultdict
from typing import Any, Collection, Optional, Sequence, Union


class ValidationError:
    _message_for_code = {
        1: "bad value syntax",
        2: "bad type, expecting '{expected}'",
        3: "bad encoding, expecting '{expected}'",
        4: "bad value content",
        5: "missing",
        6: "must not be provided",
        7: "must not be returned",
        8: "must be equal to {value!r}",
        9: "must be one of: {expected_values}",
        10: "contains duplicates, which are not allowed",
        11: "can not be used together with {other!r}",
        12: "missing main schema",
        13: "missing schema extension {extension!r}",
        14: "unknown schema",
        15: "'primary' attribute set to 'True' MUST appear no more than once",
        16: "bad SCIM reference, allowed resources: {allowed_resources}",
        17: "bad attribute name {attribute!r}",
        18: "error status must be greater or equal to 400 and lesser than 600",
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

    def __init__(self, code: int, **context):
        self._code = code
        self._message = self._message_for_code[code].format(**context)
        self._context = context

    @classmethod
    def bad_value_syntax(cls):
        return cls(code=1)

    @classmethod
    def bad_type(cls, expected: str):
        return cls(code=2, expected=expected)

    @classmethod
    def bad_encoding(cls, expected: str):
        return cls(code=3, expected=expected)

    @classmethod
    def bad_value_content(cls):
        return cls(code=4)

    @classmethod
    def missing(cls):
        return cls(code=5)

    @classmethod
    def must_not_be_provided(cls):
        return cls(code=6)

    @classmethod
    def must_not_be_returned(cls):
        return cls(code=7)

    @classmethod
    def must_be_equal_to(cls, value: Any):
        return cls(code=8, value=value)

    @classmethod
    def must_be_one_of(cls, expected_values: Collection[Any]):
        return cls(code=9, expected_values=expected_values)

    @classmethod
    def duplicated_values(cls):
        return cls(code=10)

    @classmethod
    def can_not_be_used_together(cls, other: str):
        return cls(code=11, other=other)

    @classmethod
    def missing_main_schema(cls):
        return cls(code=12)

    @classmethod
    def missing_schema_extension(cls, extension: str):
        return cls(code=13, extension=extension)

    @classmethod
    def unknown_schema(cls):
        return cls(code=14)

    @classmethod
    def multiple_primary_values(cls):
        return cls(code=15)

    @classmethod
    def bad_scim_reference(cls, allowed_resources: Collection[str]):
        return cls(code=16, allowed_resources=list(allowed_resources))

    @classmethod
    def bad_attribute_name(cls, attribute: str):
        return cls(code=17, attribute=attribute)

    @classmethod
    def bad_error_status(cls):
        return cls(code=18)

    @classmethod
    def bad_status_code(cls, expected: int):
        return cls(code=19, expected=expected)

    @classmethod
    def bad_number_of_resources(cls, reason: str):
        return cls(code=20, reason=reason)

    @classmethod
    def resources_not_filtered(cls):
        return cls(code=21)

    @classmethod
    def resources_not_sorted(cls):
        return cls(code=22)

    @classmethod
    def resource_type_endpoint_required(cls):
        return cls(code=23)

    @classmethod
    def resource_object_endpoint_required(cls):
        return cls(code=24)

    @classmethod
    def unknown_operation_resource(cls):
        return cls(code=25)

    @classmethod
    def too_many_bulk_operations(cls, max_: int):
        return cls(code=26, max=max_)

    @classmethod
    def too_many_errors_in_bulk(cls, max_: int):
        return cls(code=27, max=max_)

    @classmethod
    def unknown_modification_target(cls):
        return cls(code=28)

    @classmethod
    def attribute_can_not_be_modified(cls):
        return cls(code=29)

    @classmethod
    def attribute_can_not_be_deleted(cls):
        return cls(code=30)

    @classmethod
    def not_supported(cls):
        return cls(code=31)

    @classmethod
    def bracket_not_opened_or_closed(cls):
        return cls(code=100)

    @classmethod
    def complex_attribute_bracket_not_opened_or_closed(cls):
        return cls(code=101)

    @classmethod
    def complex_sub_attribute(cls, attr: str, sub_attr: str):
        return cls(code=102, attr=attr, sub_attr=sub_attr)

    @classmethod
    def missing_operand_for_operator(cls, operator: str, expression: str):
        return cls(code=103, operator=operator, expression=expression)

    @classmethod
    def unknown_operator(cls, operator: str, expression: str):
        return cls(code=104, operator=operator, expression=expression)

    @classmethod
    def empty_filter_expression(cls):
        return cls(code=105)

    @classmethod
    def unknown_expression(cls, expression: str):
        return cls(code=106, expression=expression)

    @classmethod
    def inner_complex_attribute_or_square_bracket(cls):
        return cls(code=107)

    @classmethod
    def empty_complex_attribute_expression(cls, attribute: str):
        return cls(code=108, attribute=attribute)

    @classmethod
    def bad_operand(cls, value: Any):
        return cls(code=109, value=value)

    @classmethod
    def non_compatible_operand(cls, value: Any, operator: str):
        return cls(code=110, value=value, operator=operator)

    @property
    def context(self) -> dict:
        return self._context

    @property
    def code(self) -> int:
        return self._code

    def __repr__(self) -> str:
        return str(self._message)

    def __eq__(self, o):
        return o == self._message


class ValidationWarning:
    _message_for_code = {
        1: "value should be one of: {expected_values}",
        2: (
            "multi-valued complex attribute should contain a given type-value pair "
            "no more than once"
        ),
        3: "unexpected content, {reason}",
        4: "missing",
        5: "should not equal to {value}",
    }

    def __init__(self, code: int, **context):
        self._code = code
        self._message = self._message_for_code[code].format(**context)
        self._context = context
        self._location: Optional[str] = None

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

    @property
    def context(self) -> dict:
        return self._context

    @property
    def code(self) -> int:
        return self._code

    def __repr__(self) -> str:
        return str(self._message)

    def __eq__(self, o):
        return o == self._message


class ValidationIssues:
    def __init__(self):
        self._errors: dict[tuple, list[ValidationError]] = defaultdict(list)
        self._warnings: dict[tuple, list[ValidationWarning]] = defaultdict(list)
        self._stop_proceeding: dict[tuple, set[int]] = defaultdict(set)

    def merge(
        self,
        issues: "ValidationIssues",
        location: Optional[Sequence[Union[str, int]]] = None,
    ):
        location = tuple(location or tuple())
        for other_location, location_issues in issues._errors.items():
            new_location = location + other_location
            self._errors[new_location].extend(location_issues)
            self._stop_proceeding[new_location].update(
                issues._stop_proceeding.get(other_location, {})
            )
        for other_location, location_issues in issues._warnings.items():
            new_location = location + other_location
            self._warnings[new_location].extend(location_issues)

    def add_error(
        self,
        issue: ValidationError,
        proceed: bool,
        location: Optional[Collection[Union[str, int]]] = None,
    ) -> None:
        location = tuple(location or tuple())
        self._errors[location].append(issue)
        if not proceed:
            self._stop_proceeding[location].add(issue.code)

    def add_warning(
        self,
        issue: ValidationWarning,
        location: Optional[Collection[Union[str, int]]] = None,
    ) -> None:
        location = tuple(location or tuple())
        self._warnings[location].append(issue)

    def get(
        self,
        error_codes: Optional[Collection[int]] = None,
        warning_codes: Optional[Collection[int]] = None,
        location: Optional[Sequence[Union[str, int]]] = None,
    ) -> "ValidationIssues":
        copy = ValidationIssues()
        location = tuple(location or tuple())

        errors_copy = {}
        for location_, errors in self._errors.items():
            if location_[: len(location)] != location:
                continue
            errors = [error for error in errors if not error_codes or error.code in error_codes]
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
                if not warning_codes or warning.code in warning_codes
            ]
            if warnings:
                warnings_copy[location_[len(location) :]] = warnings
        copy._warnings = warnings_copy

        stop_proceeding_copy = {}
        for location_, codes in self._stop_proceeding.items():
            if location_[: len(location)] != location:
                continue
            codes = [code for code in codes if not error_codes or code in error_codes]
            if codes:
                stop_proceeding_copy[location_[len(location) :]] = codes
        copy._stop_proceeding = stop_proceeding_copy

        return copy

    def pop_errors(
        self, codes: Collection[int], location: Optional[Sequence[Union[str, int]]] = None
    ) -> "ValidationIssues":
        location = tuple(location or tuple())

        if location not in self._errors:
            return ValidationIssues()

        popped = self.get(error_codes=codes, location=location)

        for issue in self._errors[location]:
            if issue.code in codes:
                self._errors[location].remove(issue)
                if issue.code in self._stop_proceeding.get(location, set()):
                    self._stop_proceeding[location].remove(issue.code)

        if len(self._errors[location]) == 0:
            self._errors.pop(location)

        if location in self._stop_proceeding and len(self._stop_proceeding[location]) == 0:
            self._stop_proceeding.pop(location)

        return popped

    def can_proceed(self, *locations: Collection[Union[str, int]]) -> bool:
        if not locations:
            locations = [tuple()]
        for location in locations:
            for i in range(len(location) + 1):
                if location[:i] in self._stop_proceeding:
                    return False
        return True

    def has_errors(self, *locations: Collection[Union[str, int]]) -> bool:
        if not locations:
            locations = [tuple()]

        for location in locations:
            for issue_location in self._errors:
                if issue_location[: len(location)] == location:
                    return True

        return False

    def to_dict(self, msg: bool = False, ctx: bool = False):
        output = {}
        self._to_dict("_errors", self._errors, output, msg=msg, ctx=ctx)
        self._to_dict("_warnings", self._warnings, output, msg=msg, ctx=ctx)
        return output

    @staticmethod
    def _to_dict(key: str, structure: dict, output: dict, msg: bool = False, ctx: bool = False):
        for location, errors in structure.items():
            if location:
                current_level = output
                for i, part in enumerate(location):
                    part = str(part)
                    if part not in current_level:
                        current_level[part] = {}  # noqa
                    if i == len(location) - 1:
                        if key not in current_level[part]:
                            current_level[part][key] = []  # noqa
                        for error in errors:
                            item = {"code": error.code}
                            if msg:
                                item["error"] = str(error)
                            if ctx:
                                item["context"] = error.context
                            current_level[part][key].append(
                                ValidationIssues._issue_to_dict(error, msg=msg, ctx=ctx)
                            )
                    current_level = current_level[part]
            else:
                if key not in output:
                    output[key] = []
                for error in errors:
                    output[key].append(ValidationIssues._issue_to_dict(error, msg=msg, ctx=ctx))

        return output

    def flatten(self, msg: bool = False, ctx: bool = False) -> dict:
        return {
            "errors": self._flatten(self._errors, msg=msg, ctx=ctx),
            "warnings": self._flatten(self._warnings, msg=msg, ctx=ctx),
        }

    @staticmethod
    def _flatten(structure: dict, msg: bool = False, ctx: bool = False):
        output = {}
        for location, issues in structure.items():
            if location:
                location_key = ".".join([str(part) for part in location])
                output[location_key] = [
                    ValidationIssues._issue_to_dict(issue, msg=msg, ctx=ctx) for issue in issues
                ]
            else:
                output[""] = [
                    ValidationIssues._issue_to_dict(issue, msg=msg, ctx=ctx) for issue in issues
                ]
        return output

    @staticmethod
    def _issue_to_dict(
        issue: Union[ValidationError, ValidationWarning],
        msg: bool = False,
        ctx: bool = False,
    ):
        output = {"code": issue.code}
        if msg:
            output["error"] = str(issue)
        if ctx:
            output["context"] = issue.context
        return output
