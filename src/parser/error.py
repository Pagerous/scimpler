from typing import Any, Collection, Dict, Optional, Type


class ValidationError:
    _message_for_code = {
        1: "attribute '{attr_name}' is required",
        2: "expected type for SCIM '{scim_type}' is '{expected_type}', got '{provided_type}' instead",
        3: "SCIM '{scim_type}' values are expected to be encoded in base 64",
        4: "SCIM '{scim_type}' should be encoded as a valid xsd:dateTime",
        5: (
            "SCIM '{scim_type}' can contain the values of these types only: {allowed_types}, "
            "but got '{provided_type}' instead"
        ),
        6: "multi-valued attribute should be of type 'list' or 'tuple', but got '{provided_type}' instead",
        7: "'{keyword}' is SCIM reserved keyword that MUST NOT occur in a attribute value",
        8: "'{value}' is not a valid URL",
        9: (
            "'primary' attribute, in multi-valued attribute item, set to 'True', "
            "MUST appear no more than once, but these items have it: {primary_entries}"
        ),
        10: "header '{header}' is required",
        11: "values of {value_1} and {value_2} must match",
        12: "error status should be greater or equal to 300 and lesser than 600, but provided {provided}",
        13: "HTTP response status ({response_status}) and error status in body ({body_status}) must match",
        14: "value must be one of: {expected_values}, but provided '{provided}'",
        15: "missing {missing}",
        16: "HTTP response status for method '{method}' must be '{expected}', but provided '{provided}'",
        17: "meta.resourceType must match configured type `{resource_type}`, but provided '{provided}'",
        18: "expected type '{expected_type}', got '{provided_type}' instead",
        19: "attribute '{attr_name}' should never be returned",
        20: "provided 'schemas' do not correspond to the resource {resource_type!r}",
        21: "too many results",
        22: "total results ({total_results}) do not match number of resources ({n_resources})",
        23: "too little results",
        24: (
            "response value of {response_key!r} ({response_value}) "
            "does not correspond to query parameter {query_param_name!r} ({query_param_value}): {reason}"
        ),

        100: "no closing bracket for the bracket at position {bracket_position}",
        101: "no opening bracket for the bracket at position {bracket_position}",
        102: "no closing complex attribute bracket for the bracket at position {bracket_position}",
        103: "no opening complex attribute bracket for the bracket at position {bracket_position}",
        104: "missing operand for operator '{operator}' in expression '{expression}'",
        105: "unknown {operator_type} operator '{operator}' in expression '{expression}'",
        106: "unknown expression '{expression}'",
        107: "no expression or empty expression inside precedence grouping operator",
        108: "complex attribute expression '{expression}' misses top-level attribute name",
        109: "complex attribute can not contain inner complex attributes or square brackets",
        110: "complex attribute {attribute!r} at position {expression_position} has no expression",
        111: "attribute {attribute!r} does not conform the rules",
        112: "bad comparison value {value!r}",
    }

    def __init__(self, code: int, **context):
        self._code = code
        self._message = self._message_for_code[code].format(**context)
        self._context = context
        self._location: Optional[str] = None

    @classmethod
    def missing_required_attribute(cls, attr_name):
        return cls(code=1, attr_name=attr_name)

    @classmethod
    def bad_scim_type(cls, scim_type: str, expected_type: Type, provided_type: Type):
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
    def bad_sub_attribute_type(cls, scim_type: str, allowed_types: Collection[Type], provided_type: Type):
        return cls(
            code=5,
            scim_type=scim_type,
            allowed_types=[type_.__name__ for type_ in allowed_types],
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
    def missing(cls, missing: Any):
        return cls(code=15, missing=missing)

    @classmethod
    def bad_status_code(cls, method: str, expected: int, provided: int):
        return cls(code=16, method=method, expected=expected, provided=provided)

    @classmethod
    def resource_type_mismatch(cls, resource_type: str, provided: str):
        return cls(code=17, resource_type=resource_type, provided=provided)

    @classmethod
    def bad_type(cls, expected_type: Type, provided_type: Type):
        return cls(code=18, expected_type=expected_type.__name__, provided_type=provided_type.__name__)

    @classmethod
    def returned_restricted_attribute(cls, attr_name: str):
        return cls(code=19, attr_name=attr_name)

    @classmethod
    def schemas_mismatch(cls, resource_type: str):
        return cls(code=20, resource_type=resource_type)

    @classmethod
    def too_many_results(cls):
        return cls(code=21)

    @classmethod
    def total_results_mismatch(cls, total_results: int, n_resources: int):
        return cls(code=22, total_results=total_results, n_resources=n_resources)

    @classmethod
    def too_little_results(cls):
        return cls(code=23)

    @classmethod
    def response_value_does_not_correspond_to_parameter(
        cls, response_key: str, response_value: Any, query_param_name: str, query_param_value: Any, reason: str
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
        return cls(code=105, operator_type=operator_type, operator=operator, expression=expression)

    @classmethod
    def unknown_expression(cls, expression: str):
        return cls(code=106, expression=expression)

    @classmethod
    def empty_expression(cls):
        return cls(code=107)

    @classmethod
    def complex_attribute_without_top_level_attribute(cls, expression: str):
        return cls(code=108, expression=expression)

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

    @property
    def context(self) -> Dict:
        return self._context

    @property
    def code(self) -> int:
        return self._code

    @property
    def location(self) -> Optional[str]:
        return self._location

    def with_location(self, *location: Any) -> 'ValidationError':
        location = ".".join([str(loc) for loc in location[::-1]])
        if self._location is None:
            self._location = location
        else:
            self._location = f"{location}.{self._location}"
        return self

    def __repr__(self) -> str:
        return str(self._message)

    def __eq__(self, o):
        return o == self._message
