from typing import Any, List, Tuple, Union

from src.attributes_presence import AttributePresenceChecker
from src.data import type as type_
from src.data.attributes import Attribute
from src.data.container import AttrRep, Invalid, Missing, SCIMDataContainer
from src.data.schemas import BaseSchema
from src.error import ValidationError, ValidationIssues
from src.filter import Filter
from src.sorter import Sorter


def parse_attr_rep(value: str) -> Tuple[Union[Invalid, AttrRep], ValidationIssues]:
    issues = ValidationIssues()
    parsed = AttrRep.parse(value)
    if parsed is Invalid:
        issues.add(
            issue=ValidationError.bad_attribute_name(str(value)),
            proceed=False,
        )
    return parsed, issues


def validate_attr_reps(value: List[str]) -> ValidationIssues:
    issues = ValidationIssues()
    for i, item in enumerate(value):
        issues.merge(issues=AttrRep.validate(item), location=(i,))
    return issues


def parse_attr_reps(value: List[str]) -> List[AttrRep]:
    return [AttrRep.parse(item) for item in value]


attributes = Attribute(
    name="attributes",
    type_=type_.String,
    required=False,
    case_exact=False,
    multi_valued=True,
    validators=[validate_attr_reps],
    parser=parse_attr_reps,
)


exclude_attributes = Attribute(
    name="excludeAttributes",
    type_=type_.String,
    required=False,
    case_exact=False,
    multi_valued=True,
    validators=[validate_attr_reps],
    parser=parse_attr_reps,
)


filter_ = Attribute(
    name="filter",
    type_=type_.String,
    required=False,
    validators=[Filter.validate],
    parser=Filter.parse,
)


sort_by = Attribute(
    name="sortBy",
    type_=type_.String,
    required=False,
    validators=[AttrRep.validate],
    parser=AttrRep.parse,
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

    def parse(self, data: Any) -> SCIMDataContainer:
        data = super().parse(data)
        to_include = data.pop(self.attrs.attributes.rep)
        to_exclude = data.pop(self.attrs.excludeattributes.rep)
        if to_include or to_exclude:
            data["presence_checker"] = AttributePresenceChecker(
                attr_reps=to_include or to_exclude, include=bool(to_include)
            )
        if sort_by_ := data.pop(self.attrs.sortby.rep):
            data["sorter"] = Sorter(
                attr_rep=sort_by_,
                asc=data.pop(self.attrs.sortorder.rep) == "ascending",
            )
        return data

    def _validate(self, data: SCIMDataContainer) -> ValidationIssues:
        issues = ValidationIssues()
        to_include = data[self.attrs.attributes.rep]
        to_exclude = data[self.attrs.excludeattributes.rep]
        if to_include not in [None, Missing] and to_exclude not in [None, Missing]:
            issues.add(
                issue=ValidationError.can_not_be_used_together(
                    self.attrs.excludeattributes.rep.attr
                ),
                proceed=False,
                location=(self.attrs.attributes.rep.attr,),
            )
            issues.add(
                issue=ValidationError.can_not_be_used_together(self.attrs.attributes.rep.attr),
                proceed=False,
                location=(self.attrs.excludeattributes.rep.attr,),
            )
        return issues
