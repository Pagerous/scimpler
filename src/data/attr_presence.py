from collections.abc import MutableMapping
from enum import Enum
from typing import Any, Collection, Literal, Optional, Union

from src.container import AttrRep, AttrRepFactory, BoundedAttrRep, Missing
from src.data.attrs import Attribute, AttributeIssuer, AttributeReturn
from src.error import ValidationError, ValidationIssues


class DataDirection(str, Enum):
    REQUEST = "REQUEST"
    RESPONSE = "RESPONSE"


class DataInclusivity(str, Enum):
    INCLUDE = "INCLUDE"
    EXCLUDE = "EXCLUDE"


_AttrRep = Union[str, AttrRep, BoundedAttrRep]
_DataDirectionLiteral = Literal["REQUEST", "RESPONSE"]
_DataInclusivityLiteral = Literal["INCLUDE", "EXCLUDE"]


class AttrPresenceConfig:
    def __init__(
        self,
        direction: Union[_DataDirectionLiteral, DataDirection],
        attr_reps: Optional[Collection[_AttrRep]] = None,
        include: Optional[bool] = None,
        ignore_issuer: Optional[Collection[_AttrRep]] = None,
    ):
        """
        Checks attributes presence according to the data flow direction,
        attribute properties, and specified inclusion / exclusion.

        :param attr_reps: specifies which attributes should be included or excluded from the data.
        :param include: if set to True, it means the attributes should be included.
            Excluded otherwise.
        :param ignore_issuer: specifies for which attributes the attribute issuer configuration
            should be ignored when making presence checks.
        """
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
        to_exclude = data.get("excludeAttributes")
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
    direction: Union[_DataDirectionLiteral, DataDirection],
    ignore_issuer: bool = False,
    inclusivity: Optional[Union[_DataInclusivityLiteral, DataInclusivity]] = None,
    required_by_schema: bool = True,
) -> ValidationIssues:
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
