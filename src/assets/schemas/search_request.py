from typing import Optional

from src.config import ServiceProviderConfig
from src.container import AttrName, AttrRep, AttrRepFactory, Missing, SCIMData
from src.data.attr_presence import AttrPresenceConfig
from src.data.attrs import Integer, String
from src.data.filter import Filter
from src.data.schemas import BaseSchema
from src.data.sorter import Sorter
from src.error import ValidationError, ValidationIssues


def validate_attr_reps(value: list[str]) -> ValidationIssues:
    issues = ValidationIssues()
    for i, item in enumerate(value):
        issues.merge(issues=AttrRepFactory.validate(item), location=(i,))
    return issues


def deserialize_attr_reps(value: list[str]) -> list[AttrRep]:
    return [AttrRepFactory.deserialize(item.strip()) for item in value]


def serialize_attr_reps(value: list[AttrRep]) -> list[str]:
    return [str(item) for item in value]


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
                    serializer=serialize_attr_reps,
                ),
                String(
                    name="excludeAttributes",
                    multi_valued=True,
                    validators=[validate_attr_reps],
                    deserializer=deserialize_attr_reps,
                    serializer=serialize_attr_reps,
                ),
                String(
                    name="filter",
                    validators=[Filter.validate],
                    deserializer=Filter.deserialize,
                    serializer=lambda f: f.serialize(),
                ),
                String(
                    name="sortBy",
                    validators=[AttrRepFactory.validate],
                    deserializer=AttrRepFactory.deserialize,
                    serializer=lambda value: str(value),
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

    def _validate(self, data: SCIMData, **kwargs) -> ValidationIssues:
        issues = ValidationIssues()
        to_include = data.get("attributes")
        to_exclude = data.get("excludeAttributes")
        if to_include not in [None, Missing] and to_exclude not in [None, Missing]:
            issues.add_error(
                issue=ValidationError.can_not_be_used_together("attributes"),
                proceed=False,
                location=["attributes"],
            )
            issues.add_error(
                issue=ValidationError.can_not_be_used_together("excludeAttributes"),
                proceed=False,
                location=["excludeAttributes"],
            )
        return issues


def get_sorter(data: SCIMData) -> Optional[Sorter]:
    if sort_by_ := data.get("sortBy"):
        return Sorter(
            attr_rep=sort_by_,
            asc=data.get("sortOrder") == "ascending",
        )
    return None


def get_presence_config(data: SCIMData) -> Optional[AttrPresenceConfig]:
    to_include = data.get("attributes")
    to_exclude = data.get("excludeAttributes")
    if to_include or to_exclude:
        return AttrPresenceConfig(
            direction="RESPONSE",
            attr_reps=to_include or to_exclude,
            include=bool(to_include),
        )
    return None


def create_search_request_schema(config: ServiceProviderConfig) -> SearchRequest:
    exclude = set()
    if not config.filter.supported:
        exclude.add(AttrName("filter"))
    if not config.sort.supported:
        exclude.add(AttrName("sortBy"))
        exclude.add(AttrName("sortOrder"))
    return SearchRequest().clone(lambda attr: attr.name not in exclude)
