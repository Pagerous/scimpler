from collections import defaultdict
from typing import Any, Collection, Dict, List, Optional, Tuple, Type


class ValidationError:
    _message_for_code = {
        1: "attribute '{attr_name}' is required",
        2: (
            "expected type for parsing SCIM '{scim_type}' is '{expected_type}', "
            "got '{provided_type}' instead"
        ),
        3: "SCIM '{scim_type}' values are expected to be encoded in base 64",
        4: "SCIM '{scim_type}' should be encoded as a valid xsd:dateTime",
        5: (
            "SCIM '{scim_type}' can contain the values of these types only when parsing: "
            "{allowed_types}, but got '{provided_type}' instead"
        ),
        6: (
            "multi-valued attribute should be of type 'list' or 'tuple', "
            "but got '{provided_type}' instead"
        ),
        7: "'{keyword}' is SCIM reserved keyword that MUST NOT occur in a attribute value",
        8: "'{value}' is not a valid URL",
        9: (
            "'primary' attribute, in multi-valued attribute item, set to 'True', "
            "MUST appear no more than once, but these items have it: {primary_entries}"
        ),
        10: "header '{header}' is required",
        11: "values of {value_1} and {value_2} must match",
        12: (
            "error status should be greater or equal to 300 and lesser than 600, "
            "but provided {provided}"
        ),
        13: (
            "HTTP response status ({response_status}) and error status in body "
            "({body_status}) must match"
        ),
        14: "value must be one of: {expected_values}, but provided '{provided}'",
        15: "missing",
        16: (
            "HTTP response status for method '{method}' must be '{expected}', "
            "but provided '{provided}'"
        ),
        17: (
            "meta.resourceType must match configured type `{resource_type}`, "
            "but provided '{provided}'"
        ),
        18: "expected type '{expected_type}', got '{provided_type}' instead",
        19: "should never be returned",
        20: "provided 'schemas' do not correspond to the resource {resource_type!r}",
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
        31: (  # TODO: change code to 3
            "expected type for dumping SCIM '{scim_type}' is '{expected_type}', "
            "got '{provided_type}' instead"
        ),
        32: (  # TODO: change code to 6
            "SCIM '{scim_type}' can contain the values of these types only when dumping: "
            "{allowed_types}, but got '{provided_type}' instead"
        ),
        33: "complex sub-attribute {sub_attr!r} of {attr!r} can not be complex",
        100: "no closing bracket for the bracket at position {bracket_position}",
        101: "no opening bracket for the bracket at position {bracket_position}",
        102: "no closing complex attribute bracket for the bracket at position {bracket_position}",
        103: "no opening complex attribute bracket for the bracket at position {bracket_position}",
        104: "missing operand for operator '{operator}' in expression '{expression}'",
        105: "unknown {operator_type} operator '{operator}' in expression '{expression}'",
        106: "unknown expression '{expression}'",
        107: "no expression or empty expression inside precedence grouping operator",
        109: "complex attribute can not contain inner complex attributes or square brackets",
        110: "complex attribute {attribute!r} at position {expression_position} has no expression",
        111: "attribute {attribute!r} does not conform the rules",
        112: "bad comparison value {value!r}",
        113: "comparison value {value!r} is not compatible with {operator!r} operator",
        200: "attribute {attribute!r} is not defined in {schema!r} schema",
        201: "complex attribute {attribute!r} is not multivalued",
        202: "complex attribute {attribute!r} does not contain 'primary' or 'value' sub-attribute",
        300: "bad operation path",
        301: "only 'eq' operator is allowed",
        302: "bad multivalued attribute filter",
    }

    def __init__(self, code: int, **context):
        self._code = code
        self._message = self._message_for_code[code].format(**context)
        self._context = context
        self._location: Optional[str] = None

    @classmethod
    def missing_required_attribute(cls, attr_name):  # TODO: remove it
        return cls(code=1, attr_name=attr_name)

    @classmethod
    def bad_scim_parse_type(cls, scim_type: str, expected_type: Type, provided_type: Type):
        return cls(
            code=2,
            scim_type=scim_type,
            expected_type=expected_type.__name__,
            provided_type=provided_type.__name__,
        )

    @classmethod
    def base_64_encoding_required(cls, scim_type: str):
        return cls(code=3, scim_type=scim_type)

    @classmethod
    def xsd_datetime_format_required(cls, scim_type: str):
        return cls(code=4, scim_type=scim_type)

    @classmethod
    def bad_sub_attribute_parse_type(
        cls, scim_type: str, allowed_types: Collection[Type], provided_type: Type
    ):
        return cls(
            code=5,
            scim_type=scim_type,
            allowed_types=sorted({type_.__name__ for type_ in allowed_types}),
            provided_type=provided_type.__name__,
        )

    @classmethod
    def bad_multivalued_attribute_type(cls, provided_type: Type):
        return cls(code=6, provided_type=provided_type.__name__)

    @classmethod
    def reserved_keyword(cls, keyword: str):
        return cls(code=7, keyword=keyword)

    @classmethod
    def bad_url(cls, value: str):
        return cls(code=8, value=value)

    @classmethod
    def multiple_primary_values(cls, primary_entry_numbers: Collection[int]):
        return cls(code=9, primary_entries=", ".join([str(x) for x in primary_entry_numbers]))

    @classmethod
    def missing_required_header(cls, header: str):
        return cls(code=10, header=header)

    @classmethod
    def values_must_match(cls, value_1: Any, value_2: Any):
        return cls(code=11, value_1=value_1, value_2=value_2)

    @classmethod
    def bad_error_status(cls, provided: int):
        return cls(code=12, provided=provided)

    @classmethod
    def error_status_mismatch(cls, response_status: str, body_status: str):
        return cls(code=13, response_status=response_status, body_status=body_status)

    @classmethod
    def must_be_one_of(cls, expected_values: Collection[Any], provided: Any):
        return cls(code=14, expected_values=expected_values, provided=provided)

    @classmethod
    def missing(cls):
        return cls(code=15)

    @classmethod
    def bad_status_code(cls, method: str, expected: int, provided: int):
        return cls(code=16, method=method, expected=expected, provided=provided)

    @classmethod
    def resource_type_mismatch(cls, resource_type: str, provided: str):
        return cls(code=17, resource_type=resource_type, provided=provided)

    @classmethod
    def bad_type(cls, expected_type: Type, provided_type: Type):
        return cls(
            code=18,
            expected_type=expected_type.__name__,
            provided_type=provided_type.__name__,
        )

    @classmethod
    def restricted_or_not_requested(cls):
        return cls(code=19)

    @classmethod
    def bad_schema(cls, resource_type: str):  # TODO: remove it
        return cls(code=20, resource_type=resource_type)

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
    def bad_scim_dump_type(cls, scim_type: str, expected_type: Type, provided_type: Type):
        return cls(
            code=31,
            scim_type=scim_type,
            expected_type=expected_type.__name__,
            provided_type=provided_type.__name__,
        )

    @classmethod
    def bad_sub_attribute_dump_type(
        cls, scim_type: str, allowed_types: Collection[Type], provided_type: Type
    ):
        return cls(
            code=32,
            scim_type=scim_type,
            allowed_types=sorted({type_.__name__ for type_ in allowed_types}),
            provided_type=provided_type.__name__,
        )

    @classmethod
    def complex_sub_attribute(cls, attr: str, sub_attr: str):
        return cls(code=33, attr=attr, sub_attr=sub_attr)

    @classmethod
    def no_closing_bracket(cls, bracket_position: int):
        return cls(code=100, bracket_position=bracket_position)

    @classmethod
    def no_opening_bracket(cls, bracket_position: int):
        return cls(code=101, bracket_position=bracket_position)

    @classmethod
    def no_closing_complex_attribute_bracket(cls, bracket_position: int):
        return cls(code=102, bracket_position=bracket_position)

    @classmethod
    def no_opening_complex_attribute_bracket(cls, bracket_position: int):
        return cls(code=103, bracket_position=bracket_position)

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
    def empty_complex_attribute_expression(cls, attribute: str, expression_position: int):
        return cls(code=110, attribute=attribute, expression_position=expression_position)

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
    def attr_not_in_schema(cls, attribute: str, schema: str):
        return cls(code=200, attribute=attribute, schema=schema)

    @classmethod
    def complex_attr_is_not_multivalued(cls, attribute: str):
        return cls(code=201, attribute=attribute)

    @classmethod
    def complex_attr_does_not_contain_primary_sub_attr(cls, attribute: str):
        return cls(code=202, attribute=attribute)

    @classmethod
    def bad_operation_path(cls):
        return cls(code=300)

    @classmethod
    def eq_operator_allowed_only(cls):
        return cls(code=301)

    @classmethod
    def bad_multivalued_attribute_filter(cls):
        return cls(code=302)

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
        self._issues: Dict[Tuple, List[ValidationError]] = defaultdict(list)
        self._stop_proceeding = set()

    @property
    def issues(self) -> Dict[Tuple, List[ValidationError]]:
        return self._issues

    def merge(self, issues: "ValidationIssues", location: Optional[Tuple] = None):
        location = location or tuple()
        for other_location, location_issues in issues.issues.items():
            new_location = location + other_location
            self._issues[new_location].extend(location_issues)
            if not issues.can_proceed(other_location):
                self._stop_proceeding.add(new_location)

    def add(
        self,
        issue: ValidationError,
        proceed: bool,
        location: Optional[Collection[str]] = None,
    ) -> None:
        location = location or tuple()
        location = tuple(location)
        self._issues[location].append(issue)
        if not proceed:
            self._stop_proceeding.add(location)

    def can_proceed(self, *locations: Collection[str]) -> bool:
        if not locations:
            locations = [tuple()]
        for location in locations:
            for i in range(1, len(location) + 1):
                if location[:i] in self._stop_proceeding:
                    return False
            if location in self._stop_proceeding:
                return False
        return True

    def has_issues(self, *locations: Collection[str]) -> bool:
        if not locations:
            locations = [tuple()]

        for location in locations:
            for issue_location in self._issues:
                if issue_location[: len(location)] == location:
                    return True

        return False

    def to_dict(self, msg: bool = False, ctx: bool = False):
        output = {}
        for location, errors in self._issues.items():
            if not location:
                if "_errors" not in output:
                    output["_errors"] = []
                for error in errors:
                    item = {"code": error.code}
                    if msg:
                        item["error"] = str(error)
                    if ctx:
                        item["context"] = error.context
                    output["_errors"].append(item)
            else:
                current_level = output
                for i, part in enumerate(location):
                    part = str(part)
                    if part not in current_level:
                        current_level[part] = {}  # noqa
                    if i == len(location) - 1:
                        if "_errors" not in current_level[part]:
                            current_level[part]["_errors"] = []  # noqa
                        for error in errors:
                            item = {"code": error.code}
                            if msg:
                                item["error"] = str(error)
                            if ctx:
                                item["context"] = error.context
                            current_level[part]["_errors"].append(item)  # noqa
                    current_level = current_level[part]
        return output

    def __bool__(self) -> bool:
        return bool(len(self._issues))
