from collections import defaultdict
from typing import Any, Collection, Dict, List, Optional, Set, Tuple, Union


class ValidationError:
    _message_for_code = {
        1: "bad value syntax",
        2: "expected type '{expected}', got '{provided}' instead",
        3: "SCIM '{scim_type}' values are expected to be encoded in base 64",
        7: "'{keyword}' is SCIM reserved keyword that MUST NOT occur in a attribute value",
        8: "'{value}' is not a valid URL",
        9: (
            "'primary' attribute set to 'True', in multi-valued complex attribute, "
            "MUST appear no more than once"
        ),
        10: "header '{header}' is required",
        11: "must be equal to {value!r}",
        12: "error status must be greater or equal to 300 and lesser than 600",
        13: (
            "HTTP response status ({response_status}) and error status in body "
            "({body_status}) must match"
        ),
        14: "value must be one of: {expected_values}",
        15: "missing",
        16: "bad status code, expecting '{expected}', but provided '{provided}'",
        17: (
            "meta.resourceType must match configured type `{resource_type}`, "
            "but provided '{provided}'"
        ),
        19: "should not be returned",
        21: "too many results, must {must}",
        22: "total results ({total_results}) do not match number of resources ({n_resources})",
        23: "too little results, must {must}",
        24: (
            "response value of {response_key!r} ({response_value}) "
            "does not correspond to query parameter {query_param_name!r} ({query_param_value}): "
            "{reason}"
        ),
        25: "resource included in the result, but does not match the filter",
        26: "resources are not sorted",
        27: "unknown schema",
        28: "main schema not included",
        29: "extension {extension!r} is missing",
        30: "can not be used together with {other!r}",
        33: "complex sub-attribute {sub_attr!r} of {attr!r} can not be complex",
        34: "resource type endpoint is required",
        35: "resource object endpoint is required",
        36: "unknown resource",
        37: "too many operations (max {max})",
        38: "too many errors (max {max})",
        39: "value or operation not supported",
        40: "bad SCIM reference, allowed resources: {allowed_resources}",
        100: "one of brackets is not opened / closed",
        102: "one of complex attribute brackets is not opened / closed",
        104: "missing operand for operator '{operator}' in expression '{expression}'",
        105: "unknown {operator_type} operator '{operator}' in expression '{expression}'",
        106: "unknown expression '{expression}'",
        107: "no expression or empty expression inside grouping operator",
        109: "complex attribute can not contain inner complex attributes or square brackets",
        110: "complex attribute {attribute!r} has no expression",
        111: "attribute {attribute!r} does not conform the rules",
        112: "bad comparison value {value!r}",
        113: "comparison value {value!r} is not compatible with {operator!r} operator",
        300: "bad operation path",
        303: "unknown operation target",
        304: "attribute can not be modified",
        305: "can not use complex filter without sub-attribute specified for 'add' operation",
        306: "attribute can not be deleted",
    }

    def __init__(self, code: int, **context):
        self._code = code
        self._message = self._message_for_code[code].format(**context)
        self._context = context
        self._location: Optional[str] = None

    @classmethod
    def bad_value_syntax(cls):
        return cls(code=1)

    @classmethod
    def bad_type(cls, expected: str, provided: str):
        return cls(code=2, expected=expected, provided=provided)

    @classmethod
    def base_64_encoding_required(cls, scim_type: str):
        return cls(code=3, scim_type=scim_type)

    @classmethod
    def reserved_keyword(cls, keyword: str):
        return cls(code=7, keyword=keyword)

    @classmethod
    def bad_url(cls, value: str):
        return cls(code=8, value=value)

    @classmethod
    def multiple_primary_values(cls):
        return cls(code=9)

    @classmethod
    def missing_required_header(cls, header: str):
        return cls(code=10, header=header)

    @classmethod
    def must_be_equal_to(cls, value: Any):
        return cls(code=11, value=value)

    @classmethod
    def bad_error_status(cls):
        return cls(code=12)

    @classmethod
    def error_status_mismatch(cls, response_status: str, body_status: str):
        return cls(code=13, response_status=response_status, body_status=body_status)

    @classmethod
    def must_be_one_of(cls, expected_values: Collection[Any]):
        return cls(code=14, expected_values=expected_values)

    @classmethod
    def missing(cls):
        return cls(code=15)

    @classmethod
    def bad_status_code(cls, expected: int, provided: int):
        return cls(code=16, expected=expected, provided=provided)

    @classmethod
    def resource_type_mismatch(cls, resource_type: str, provided: str):
        return cls(code=17, resource_type=resource_type, provided=provided)

    @classmethod
    def restricted_or_not_requested(cls):
        return cls(code=19)

    @classmethod
    def too_many_results(cls, must: str):
        return cls(code=21, must=must)

    @classmethod
    def total_results_mismatch(cls, total_results: int, n_resources: int):
        return cls(code=22, total_results=total_results, n_resources=n_resources)

    @classmethod
    def too_little_results(cls, must: str):
        return cls(code=23, must=must)

    @classmethod
    def response_value_does_not_correspond_to_parameter(
        cls,
        response_key: str,
        response_value: Any,
        query_param_name: str,
        query_param_value: Any,
        reason: str,
    ):
        return cls(
            code=24,
            response_key=response_key,
            response_value=response_value,
            query_param_name=query_param_name,
            query_param_value=query_param_value,
            reason=reason,
        )

    @classmethod
    def included_resource_does_not_match_filter(cls):
        return cls(code=25)

    @classmethod
    def resources_not_sorted(cls):
        return cls(code=26)

    @classmethod
    def unknown_schema(cls):
        return cls(code=27)

    @classmethod
    def missing_main_schema(cls):
        return cls(code=28)

    @classmethod
    def missing_schema_extension(cls, extension: str):
        return cls(code=29, extension=extension)

    @classmethod
    def can_not_be_used_together(cls, other: str):
        return cls(code=30, other=other)

    @classmethod
    def complex_sub_attribute(cls, attr: str, sub_attr: str):
        return cls(code=33, attr=attr, sub_attr=sub_attr)

    @classmethod
    def resource_type_endpoint_required(cls):
        return cls(code=34)

    @classmethod
    def resource_object_endpoint_required(cls):
        return cls(code=35)

    @classmethod
    def unknown_resource(cls):
        return cls(code=36)

    @classmethod
    def too_many_operations(cls, max_: int):
        return cls(code=37, max=max_)

    @classmethod
    def too_many_errors(cls, max_: int):
        return cls(code=38, max=max_)

    @classmethod
    def not_supported(cls):
        return cls(code=39)

    @classmethod
    def bad_scim_reference(cls, allowed_resources: Collection[str]):
        return cls(code=40, allowed_resources=list(allowed_resources))

    @classmethod
    def bracket_not_opened_or_closed(cls):
        return cls(code=100)

    @classmethod
    def complex_attribute_bracket_not_opened_or_closed(cls):
        return cls(code=102)

    @classmethod
    def missing_operand_for_operator(cls, operator: str, expression: str):
        return cls(code=104, operator=operator, expression=expression)

    @classmethod
    def unknown_operator(cls, operator_type: str, operator: str, expression: str):
        return cls(
            code=105,
            operator_type=operator_type,
            operator=operator,
            expression=expression,
        )

    @classmethod
    def unknown_expression(cls, expression: str):
        return cls(code=106, expression=expression)

    @classmethod
    def empty_filter_expression(cls):
        return cls(code=107)

    @classmethod
    def inner_complex_attribute_or_square_bracket(cls):
        return cls(code=109)

    @classmethod
    def empty_complex_attribute_expression(cls, attribute: str):
        return cls(code=110, attribute=attribute)

    @classmethod
    def bad_attribute_name(cls, attribute: str):
        return cls(code=111, attribute=attribute)

    @classmethod
    def bad_comparison_value(cls, value: Any):
        return cls(code=112, value=value)

    @classmethod
    def non_compatible_comparison_value(cls, value: Any, operator: str):
        return cls(code=113, value=value, operator=operator)

    @classmethod
    def bad_operation_path(cls):
        return cls(code=300)

    @classmethod
    def unknown_operation_target(cls):
        return cls(code=303)

    @classmethod
    def attribute_can_not_be_modified(cls):
        return cls(code=304)

    @classmethod
    def complex_filter_without_sub_attr_for_add_op(cls):
        return cls(code=305)

    @classmethod
    def attribute_can_not_be_deleted(cls):
        return cls(code=306)

    @property
    def context(self) -> Dict:
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
        2: "multi-valued complex attribute should contain no more than once type-value pair",
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

    @property
    def context(self) -> Dict:
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
        self._errors: Dict[Tuple, List[ValidationError]] = defaultdict(list)
        self._warnings: Dict[Tuple, List[ValidationWarning]] = defaultdict(list)
        self._stop_proceeding: Dict[Tuple, Set[int]] = defaultdict(set)

    def merge(self, issues: "ValidationIssues", location: Optional[Tuple] = None):
        location = location or tuple()
        for other_location, location_issues in issues._errors.items():
            new_location = location + other_location
            self._errors[new_location].extend(location_issues)
            self._stop_proceeding[new_location].update(issues._stop_proceeding[other_location])
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

    def get(self, location: Collection[Union[str, int]]) -> "ValidationIssues":
        copy = ValidationIssues()
        copy._errors = {
            location_[len(location) :]: errors
            for location_, errors in self._errors.items()
            if location_[: len(location)] == location
        }
        copy._warnings = {
            location_[len(location) :]: warnings
            for location_, warnings in self._warnings.items()
            if location_[: len(location)] == location
        }
        copy._stop_proceeding = {
            location_[len(location) :]: codes
            for location_, codes in self._stop_proceeding.items()
            if location_[: len(location)] == location
        }
        return copy

    def pop_error(self, location: Collection[Union[str, int]], code: int) -> "ValidationIssues":
        location = tuple(location)

        if location not in self._errors:
            return ValidationIssues()

        popped = self.get(location)

        for issue in self._errors[location]:
            if issue.code == code:
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
    def _to_dict(key: str, structure: Dict, output: Dict, msg: bool = False, ctx: bool = False):
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
                            current_level[part][key].append(item)  # noqa
                    current_level = current_level[part]
            else:
                if key not in output:
                    output[key] = []
                for error in errors:
                    item = {"code": error.code}
                    if msg:
                        item["error"] = str(error)
                    if ctx:
                        item["context"] = error.context
                    output[key].append(item)

        return output
