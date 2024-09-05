from collections.abc import MutableMapping
from enum import Enum
from typing import Any, Collection, Optional, Union

from scimpler.container import Missing
from scimpler.data.attrs import Attribute, AttributeIssuer, AttributeReturn
from scimpler.error import ValidationError, ValidationIssues
from scimpler.identifiers import AttrRep, AttrRepFactory, BoundedAttrRep


class DataDirection(str, Enum):
    REQUEST = "REQUEST"
    RESPONSE = "RESPONSE"


class DataInclusivity(str, Enum):
    INCLUDE = "INCLUDE"
    EXCLUDE = "EXCLUDE"


class AttrPresenceConfig:
    """
    Configuration for attribute presence, according to the data flow direction,
    attribute properties, and specified inclusion / exclusion.

    Args:
        direction: The direction of the data flow, can be either "REQUEST" or "RESPONSE"
        attr_reps: Specifies which attributes should be included or excluded from the data. The
            `include` parameter must be specified together.
        include: If set to True, it means the attributes should be included. Excluded otherwise.
            Has no effect if `attr_reps` is not provided.
        ignore_issuer: Specifies for which attributes the attribute issuer  should be ignored
            when making presence checks
    """

    def __init__(
        self,
        direction: Union[str, DataDirection],
        attr_reps: Optional[Collection[Union[str, AttrRep, BoundedAttrRep]]] = None,
        include: Optional[bool] = None,
        ignore_issuer: Optional[Collection[Union[str, AttrRep, BoundedAttrRep]]] = None,
    ):
        self._direction = DataDirection(direction)
        self._attr_reps = [
            AttrRepFactory.deserialize(attr_rep) if isinstance(attr_rep, str) else attr_rep
            for attr_rep in (attr_reps or [])
        ]
        self._include = include

        if self._attr_reps and self._include is None:
            raise ValueError("'include' must be specified if 'attr_reps' is specified")

        self._ignore_issuer = [
            AttrRepFactory.deserialize(attr_rep) if isinstance(attr_rep, str) else attr_rep
            for attr_rep in (ignore_issuer or [])
        ]

    @property
    def direction(self) -> DataDirection:
        return self._direction

    @property
    def attr_reps(self) -> list[AttrRep]:
        return self._attr_reps

    @property
    def include(self) -> Optional[bool]:
        return self._include

    @property
    def ignore_issuer(self) -> list[AttrRep]:
        return self._ignore_issuer

    @classmethod
    def from_data(cls, data: MutableMapping) -> Optional["AttrPresenceConfig"]:
        to_include = data.get("attributes")
        to_exclude = data.get("excludedAttributes")
        if to_include or to_exclude:
            return AttrPresenceConfig(
                direction="RESPONSE",
                attr_reps=to_include or to_exclude,
                include=bool(to_include),
            )
        return None


def validate_presence(
    attr: Attribute,
    value: Any,
    direction: Union[str, DataDirection],
    ignore_issuer: bool = False,
    inclusivity: Optional[Union[str, DataInclusivity]] = None,
    required_by_schema: bool = True,
) -> ValidationIssues:
    if inclusivity:
        inclusivity = DataInclusivity(inclusivity)
    direction = DataDirection(direction)
    issues = ValidationIssues()
    if value not in [None, "", [], Missing]:
        if direction == DataDirection.REQUEST:
            if attr.issuer == AttributeIssuer.SERVER and not ignore_issuer:
                issues.add_error(
                    issue=ValidationError.must_not_be_provided(),
                    proceed=True,
                )
            return issues

        if attr.returned == AttributeReturn.NEVER:
            issues.add_error(
                issue=ValidationError.must_not_be_returned(),
                proceed=True,
            )

        elif attr.returned != AttributeReturn.ALWAYS and inclusivity == DataInclusivity.EXCLUDE:
            issues.add_error(
                issue=ValidationError.must_not_be_returned(),
                proceed=True,
            )
        return issues

    if (
        attr.required
        # issued by the server, so skipping for data from client
        and not (
            direction == DataDirection.REQUEST
            and attr.issuer == AttributeIssuer.SERVER
            and not ignore_issuer
        )
        and (
            inclusivity == DataInclusivity.INCLUDE
            or (direction == DataDirection.RESPONSE and attr.returned == AttributeReturn.ALWAYS)
        )
    ) and required_by_schema:
        issues.add_error(
            issue=ValidationError.missing(),
            proceed=False,
        )
    return issues
