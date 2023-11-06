from src.parser.attributes import type as at
from src.parser.attributes.attributes import Attribute, AttributeName
from src.parser.error import ValidationError, ValidationIssues
from src.parser.filter.filter import Filter


def validate_attr_name(value: str) -> ValidationIssues:
    issues = ValidationIssues()
    if AttributeName.parse(value) is None:
        issues.add(
            issue=ValidationError.bad_attribute_name(str(value)),
            proceed=False,
        )
    return issues


attributes = Attribute(
    name="attributes",
    type_=at.String,
    required=False,
    case_exact=False,
    multi_valued=True,
    validators=[validate_attr_name],
)


exclude_attributes = Attribute(
    name="excludeAttributes",
    type_=at.String,
    required=False,
    case_exact=False,
    multi_valued=True,
    validators=[validate_attr_name],
)


def validate_filter(value: str):
    return Filter.parse(value)[1]


filter_ = Attribute(
    name="filter",
    type_=at.String,
    required=False,
    validators=[validate_filter],
)


sort_by = Attribute(
    name="sortBy",
    type_=at.String,
    required=False,
    validators=[validate_attr_name],
)


sort_order = Attribute(
    name="sortOrder",
    type_=at.String,
    required=False,
    case_exact=False,
    canonical_values=["ascending", "descending"],
)


start_index = Attribute(
    name="startIndex",
    type_=at.Integer,
    required=False,
)


count = Attribute(
    name="count",
    type_=at.Integer,
    required=False,
)
