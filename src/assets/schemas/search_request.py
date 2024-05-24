from typing import Any

from src.assets.config import ServiceProviderConfig
from src.container import BoundedAttrRep, Missing, SCIMDataContainer
from src.data.attributes import Integer, String
from src.data.attributes_presence import AttributePresenceChecker
from src.data.filter import Filter
from src.data.schemas import BaseSchema
from src.data.sorter import Sorter
from src.error import ValidationError, ValidationIssues


def validate_attr_reps(value: list[str]) -> ValidationIssues:
    issues = ValidationIssues()
    for i, item in enumerate(value):
        issues.merge(issues=BoundedAttrRep.validate(item), location=(i,))
    return issues


def deserialize_attr_reps(value: list[str]) -> list[BoundedAttrRep]:
    return [BoundedAttrRep.deserialize(item) for item in value]


def _process_start_index(value: int) -> int:
    if value < 1:
        value = 1
    return value


def _process_count(value: int) -> int:
    if value < 0:
        value = 0
    return value


class SearchRequest(BaseSchema):
    def __init__(self):
        super().__init__(
            schema="urn:ietf:params:scim:api:messages:2.0:SearchRequest",
            attrs=[
                String(
                    name="attributes",
                    multi_valued=True,
                    validators=[validate_attr_reps],
                    deserializer=deserialize_attr_reps,
                ),
                String(
                    name="excludeAttributes",
                    multi_valued=True,
                    validators=[validate_attr_reps],
                    deserializer=deserialize_attr_reps,
                ),
                String(
                    name="filter",
                    validators=[Filter.validate],
                    deserializer=Filter.deserialize,
                ),
                String(
                    name="sortBy",
                    validators=[BoundedAttrRep.validate],
                    deserializer=BoundedAttrRep.deserialize,
                ),
                String(
                    name="sortOrder",
                    canonical_values=["ascending", "descending"],
                ),
                Integer(
                    name="startIndex",
                    serializer=_process_start_index,
                    deserializer=_process_start_index,
                ),
                Integer(name="count", serializer=_process_count, deserializer=_process_count),
            ],
        )

    def deserialize(self, data: Any) -> SCIMDataContainer:
        data = super().deserialize(data)
        to_include = data.pop(self.attrs.attributes.rep)
        to_exclude = data.pop(self.attrs.excludeattributes.rep)
        if to_include or to_exclude:
            data.set(
                "presence_checker",
                AttributePresenceChecker(
                    attr_reps=to_include or to_exclude, include=bool(to_include)
                ),
            )
        if sort_by_ := data.pop(self.attrs.sortby.rep):
            data.set(
                "sorter",
                Sorter(
                    attr_rep=sort_by_,
                    asc=data.pop(self.attrs.sortorder.rep) == "ascending",
                ),
            )
        return data

    def _validate(self, data: SCIMDataContainer) -> ValidationIssues:
        issues = ValidationIssues()
        to_include = data.get(self.attrs.attributes.rep)
        to_exclude = data.get(self.attrs.excludeattributes.rep)
        if to_include not in [None, Missing] and to_exclude not in [None, Missing]:
            issues.add_error(
                issue=ValidationError.can_not_be_used_together(
                    self.attrs.excludeattributes.rep.attr
                ),
                proceed=False,
                location=(self.attrs.attributes.rep.attr,),
            )
            issues.add_error(
                issue=ValidationError.can_not_be_used_together(self.attrs.attributes.rep.attr),
                proceed=False,
                location=(self.attrs.excludeattributes.rep.attr,),
            )
        return issues


def create_search_request_schema(config: ServiceProviderConfig) -> SearchRequest:
    exclude = set()
    if not config.filter.supported:
        exclude.add("filter")
    if not config.sort.supported:
        exclude.add("sortBy")
        exclude.add("sortOrder")
    return SearchRequest().clone(lambda attr: attr.rep.attr not in exclude)
