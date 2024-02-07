from typing import Any, Dict, List, Optional, Tuple

from src.attributes_presence import AttributePresenceChecker
from src.data import type as type_
from src.data.attributes import Attribute
from src.data.container import AttrRep
from src.error import ValidationError, ValidationIssues
from src.filter.filter import Filter
from src.schemas import BaseSchema
from src.sorter import Sorter


def parse_attr_rep(value: str) -> Tuple[Optional[AttrRep], ValidationIssues]:
    issues = ValidationIssues()
    parsed = AttrRep.parse(value)
    if parsed is None:
        issues.add(
            issue=ValidationError.bad_attribute_name(str(value)),
            proceed=False,
        )
    return parsed, issues


def parse_attr_rep_multi(
    value: List[str],
) -> Tuple[List[Optional[AttrRep]], ValidationIssues]:
    issues = ValidationIssues()
    parsed = []
    for i, item in enumerate(value):
        parsed_item, issues_ = parse_attr_rep(item)
        issues.merge(issues=issues_, location=(i,))
        parsed.append(parsed_item)
    return parsed, issues


attributes = Attribute(
    name="attributes",
    type_=type_.String,
    required=False,
    case_exact=False,
    multi_valued=True,
    parsers=[parse_attr_rep_multi],
)


exclude_attributes = Attribute(
    name="excludeAttributes",
    type_=type_.String,
    required=False,
    case_exact=False,
    multi_valued=True,
    parsers=[parse_attr_rep_multi],
)


filter_ = Attribute(
    name="filter",
    type_=type_.String,
    required=False,
    parsers=[Filter.parse],
)


sort_by = Attribute(
    name="sortBy",
    type_=type_.String,
    required=False,
    parsers=[parse_attr_rep],
)


sort_order = Attribute(
    name="sortOrder",
    type_=type_.String,
    required=False,
    case_exact=False,
    canonical_values=["ascending", "descending"],
)


start_index = Attribute(
    name="startIndex",
    type_=type_.Integer,
    required=False,
)


count = Attribute(
    name="count",
    type_=type_.Integer,
    required=False,
)


class SearchRequest(BaseSchema):
    def __init__(self):
        super().__init__(
            schema="urn:ietf:params:scim:api:messages:2.0:SearchRequest",
            attrs=[
                attributes,
                exclude_attributes,
                filter_,
                sort_by,
                sort_order,
                start_index,
                count,
            ],
        )

    def __repr__(self) -> str:
        return "SearchRequest"

    def parse(self, data: Any) -> Tuple[Optional[Dict[str, Any]], ValidationIssues]:
        data, issues = super().parse(data)
        if not issues.can_proceed():
            return data, issues

        if issues.can_proceed((attributes.rep.attr,), (exclude_attributes.rep.attr,)):
            to_include = data[attributes.rep]
            to_exclude = data[exclude_attributes.rep]
            if to_include and to_exclude:
                issues.add(
                    issue=ValidationError.can_not_be_used_together(exclude_attributes.rep.attr),
                    proceed=False,
                    location=(attributes.rep.attr,),
                )
                issues.add(
                    issue=ValidationError.can_not_be_used_together(attributes.rep.attr),
                    proceed=False,
                    location=(exclude_attributes.rep.attr,),
                )
            if to_include or to_include:
                data[AttrRep(attr="presence_checker")] = AttributePresenceChecker(
                    attr_reps=to_include or to_exclude, include=bool(to_include)
                )

        if issues.can_proceed((sort_by.rep.attr,)):
            sort_by_ = data[sort_by.rep]
            if sort_by_:
                data[AttrRep(attr="sorter")] = Sorter(
                    attr_rep=sort_by_, asc=data[sort_by.rep] == "ascending"
                )

        return data, issues
