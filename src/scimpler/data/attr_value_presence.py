from enum import Enum
from typing import Any, Collection, Optional, Union

from scimpler.data.attrs import Attribute, AttributeIssuer, AttributeReturn
from scimpler.data.identifiers import AttrRep, AttrRepFactory, BoundedAttrRep
from scimpler.data.scim_data import Missing
from scimpler.error import ValidationError, ValidationIssues


class DataDirection(str, Enum):
    REQUEST = "REQUEST"
    RESPONSE = "RESPONSE"


class DataInclusivity(str, Enum):
    INCLUDE = "INCLUDE"
    EXCLUDE = "EXCLUDE"


class AttrValuePresenceConfig:
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

    def allowed(self, attr_rep: AttrRep) -> bool:
        """
        Returns boolean indicating whether the `attr_rep` is allowed to exist whenever the
        presence configuration is applied, according to its `attr_reps` and `include` configuration.
        It considers the value existence only, without any of its possible characteristics.

        Examples:
            >>> from scimpler.data import AttrRep
            >>>
            >>> presence_config = AttrValuePresenceConfig(
            >>>     "RESPONSE", attr_reps=[AttrRep(attr="name")], include=True
            >>> )
            >>> presence_config.allowed(AttrRep(attr="name", sub_attr="formatted"))
            True
            >>> presence_config.allowed(AttrRep(attr="userName"))
            False
        """
        if self._include is None:
            return True

        is_contained = self._is_contained(attr_rep)
        if is_contained:
            return self._include

        is_sibling_contained = self._is_sibling_contained(attr_rep)
        is_parent_contained = self._is_parent_contained(attr_rep)
        if is_sibling_contained and not is_parent_contained and self._include:
            return False

        if is_parent_contained:
            return self._include

        is_child_contained = self._is_child_contained(attr_rep)
        if is_child_contained and self._include:
            return True

        return not self._include

    def _is_contained(self, attr_rep: AttrRep) -> bool:
        return attr_rep in self._attr_reps

    def _is_parent_contained(self, attr_rep: AttrRep) -> bool:
        return bool(
            attr_rep.is_sub_attr
            and (
                (
                    BoundedAttrRep(schema=attr_rep.schema, attr=attr_rep.attr)
                    if isinstance(attr_rep, BoundedAttrRep)
                    else AttrRep(attr=attr_rep.attr)
                )
                in self._attr_reps
            )
        )

    def _is_child_contained(self, attr_rep: AttrRep) -> bool:
        for rep in self._attr_reps:
            if not rep.is_sub_attr:
                continue

            if isinstance(attr_rep, BoundedAttrRep) and isinstance(rep, BoundedAttrRep):
                if attr_rep.schema == rep.schema and attr_rep.attr == rep.attr:
                    return True
                continue
            elif attr_rep.attr == rep.attr:
                return True

        return False

    def _is_sibling_contained(self, attr_rep: AttrRep) -> bool:
        if not attr_rep.is_sub_attr:
            return False

        for rep in self._attr_reps:
            if not rep.is_sub_attr:
                continue

            if (
                isinstance(rep, BoundedAttrRep)
                and isinstance(attr_rep, BoundedAttrRep)
                and rep.schema != attr_rep.schema
            ):
                continue

            if attr_rep.attr == rep.attr and attr_rep.sub_attr != rep.sub_attr:
                return True

        return False


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
    if value not in [None, "", [], Missing]:
        return _validate_if_can_be_present(
            attr=attr,
            direction=direction,
            ignore_issuer=ignore_issuer,
            inclusivity=inclusivity,
        )
    return _validate_if_can_be_omitted(
        attr=attr,
        direction=direction,
        ignore_issuer=ignore_issuer,
        inclusivity=inclusivity,
        required_by_schema=required_by_schema,
    )


def _validate_if_can_be_omitted(
    attr: Attribute,
    direction: Union[str, DataDirection],
    ignore_issuer: bool = False,
    inclusivity: Optional[Union[str, DataInclusivity]] = None,
    required_by_schema: bool = True,
) -> ValidationIssues:
    issues = ValidationIssues()
    if (
        attr.required
        # issued by the server, so skipping for data from client
        and not (
            direction == DataDirection.REQUEST
            and attr.issuer == AttributeIssuer.SERVICE_PROVIDER
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


def _validate_if_can_be_present(
    attr: Attribute,
    direction: Union[str, DataDirection],
    ignore_issuer: bool = False,
    inclusivity: Optional[Union[str, DataInclusivity]] = None,
) -> ValidationIssues:
    issues = ValidationIssues()
    if direction == DataDirection.REQUEST:
        if attr.issuer == AttributeIssuer.SERVICE_PROVIDER and not ignore_issuer:
            issues.add_error(
                issue=ValidationError.must_not_be_provided(),
                proceed=True,
            )
        return issues

    if attr.returned == AttributeReturn.NEVER or (
        attr.returned != AttributeReturn.ALWAYS and inclusivity == DataInclusivity.EXCLUDE
    ):
        issues.add_error(
            issue=ValidationError.must_not_be_returned(),
            proceed=True,
        )
    return issues
