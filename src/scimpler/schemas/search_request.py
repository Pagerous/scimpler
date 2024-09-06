from typing import Optional

from scimpler import registry
from scimpler.config import ServiceProviderConfig
from scimpler.data.attrs import Attribute, Integer, String
from scimpler.data.filter import Filter
from scimpler.data.identifiers import AttrName, AttrRep, AttrRepFactory
from scimpler.data.schemas import AttrFilter, BaseSchema
from scimpler.data.scim_data import Missing, ScimData
from scimpler.error import ValidationError, ValidationIssues


def validate_attr_reps(value: list[str]) -> ValidationIssues:
    issues = ValidationIssues()
    for i, item in enumerate(value):
        issues.merge(issues=AttrRepFactory.validate(item), location=(i,))
    return issues


def deserialize_attr_reps(value: list[str]) -> list[AttrRep]:
    return [AttrRepFactory.deserialize(item.strip()) for item in value]


def serialize_attr_reps(value: list[AttrRep]) -> list[str]:
    return [str(item) for item in value]


def process_start_index(value: int) -> int:
    if value < 1:
        value = 1
    return value


def process_count(value: int) -> int:
    if value < 0:
        value = 0
    return value


class SearchRequestSchema(BaseSchema):
    """
    SearchRequest schema, identified by `urn:ietf:params:scim:api:messages:2.0:SearchRequest` URI.

    Provides data validation and additionally checks if `attributes` and `excludedAttributes`
    are not passed together.

    During deserialization:

    - `attributes` or `excludedAttributes` are deserialized to `AttrRep` instances,
    - `startIndex` is set to 1 if value is lower than 1,
    - `count` is set to 0 if value is lower than 0.

    During serialization:

    - `attributes` or `excludedAttributes` are serialized from `AttrRep` to string values,
    - `startIndex` is set to 1 if value is lower than 1,
    - `count` is set to 0 if value is lower than 0.
    """

    schema = "urn:ietf:params:scim:api:messages:2.0:SearchRequest"
    base_attrs: list[Attribute] = [
        String(
            name="attributes",
            multi_valued=True,
            validators=[validate_attr_reps],
            deserializer=deserialize_attr_reps,
            serializer=serialize_attr_reps,
        ),
        String(
            name="excludedAttributes",
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
            serializer=process_start_index,
            deserializer=process_start_index,
        ),
        Integer(name="count", serializer=process_count, deserializer=process_count),
    ]

    def __init__(self, attr_filter: Optional[AttrFilter] = None):
        super().__init__(attr_filter=attr_filter)

    @classmethod
    def from_config(cls, config: Optional[ServiceProviderConfig] = None) -> "SearchRequestSchema":
        """
        Creates `SearchRequestSchema` from the `config`. If `config` is not provided, the
        registered configuration is used.
        """
        exclude = set()
        config = config or registry.service_provider_config
        if not config.filter.supported:
            exclude.add(AttrName("filter"))
        if not config.sort.supported:
            exclude.add(AttrName("sortBy"))
            exclude.add(AttrName("sortOrder"))
        return cls(attr_filter=AttrFilter(attr_names=exclude, include=False))

    def _validate(self, data: ScimData, **kwargs) -> ValidationIssues:
        issues = ValidationIssues()
        to_include = data.get("attributes")
        to_exclude = data.get("excludedAttributes")
        if to_include not in [None, Missing] and to_exclude not in [None, Missing]:
            issues.add_error(
                issue=ValidationError.can_not_be_used_together("attributes"),
                proceed=False,
                location=["attributes"],
            )
            issues.add_error(
                issue=ValidationError.can_not_be_used_together("excludedAttributes"),
                proceed=False,
                location=["excludedAttributes"],
            )
        return issues
