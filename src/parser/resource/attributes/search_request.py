from typing import List, Optional, Tuple

from src.parser.attributes import type as at
from src.parser.attributes.attributes import Attribute, AttributeName
from src.parser.error import ValidationError, ValidationIssues
from src.parser.filter.filter import Filter


def parse_attr_name(value: str) -> Tuple[Optional[AttributeName], ValidationIssues]:
    issues = ValidationIssues()
    parsed = AttributeName.parse(value)
    if parsed is None:
        issues.add(
            issue=ValidationError.bad_attribute_name(str(value)),
            proceed=False,
        )
    return parsed, issues


def parse_attr_name_multi(
    value: List[str],
) -> Tuple[List[Optional[AttributeName]], ValidationIssues]:
    issues = ValidationIssues()
    parsed = []
    for i, item in enumerate(value):
        parsed_item, issues_ = parse_attr_name(item)
        issues.merge(issues=issues_, location=(i,))
        parsed.append(parsed_item)
    return parsed, issues


attributes = Attribute(
    name="attributes",
    type_=at.String,
    required=False,
    case_exact=False,
    multi_valued=True,
    parsers=[parse_attr_name_multi],
)


exclude_attributes = Attribute(
    name="excludeAttributes",
    type_=at.String,
    required=False,
    case_exact=False,
    multi_valued=True,
    parsers=[parse_attr_name_multi],
)


def parse_filter(value: str) -> Tuple[Optional[Filter], ValidationIssues]:
    return Filter.parse(value)


filter_ = Attribute(
    name="filter",
    type_=at.String,
    required=False,
    parsers=[parse_filter],
)


sort_by = Attribute(
    name="sortBy",
    type_=at.String,
    required=False,
    parsers=[parse_attr_name],
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
