from typing import Any, Dict, Generic, Iterable, List, Optional, TypeVar, Union

from src.data.attributes import (
    Attribute,
    AttributeReturn,
    Attributes,
    BoundedAttributes,
    Complex,
)
from src.data.container import (
    AttrRep,
    BoundedAttrRep,
    Invalid,
    Missing,
    SCIMDataContainer,
)
from src.error import ValidationError, ValidationIssues

TAttrRep = TypeVar("TAttrRep", bound=Union[AttrRep, BoundedAttrRep])
TAttrs = TypeVar("TAttrs", bound=Union[Attributes, BoundedAttributes])


class AttributePresenceChecker(Generic[TAttrRep]):
    def __init__(
        self,
        attr_reps: Optional[Iterable[TAttrRep]] = None,
        include: Optional[bool] = None,
        ignore_required: Optional[Iterable[TAttrRep]] = None,
    ):
        self._attr_reps = list(attr_reps or [])
        self._include = include
        self._ignore_required = list(ignore_required or [])

    @property
    def attr_reps(self) -> List[TAttrRep]:
        return self._attr_reps

    @property
    def include(self) -> Optional[bool]:
        return self._include

    def __call__(
        self,
        data: Union[Dict[str, Any], SCIMDataContainer],
        attrs: TAttrs,
        direction: str,
    ) -> ValidationIssues:
        attr_rep_ = next(iter(self._attr_reps), None)
        attr_rep_ignore = next(iter(self._ignore_required), None)

        if isinstance(attrs, Attributes) and (
            isinstance(attr_rep_, BoundedAttrRep) or isinstance(attr_rep_ignore, BoundedAttrRep)
        ):
            raise TypeError("incompatible attributes, use BoundedAttributes class")
        elif isinstance(attrs, BoundedAttributes) and (
            isinstance(attr_rep_, AttrRep) or isinstance(attr_rep_ignore, AttrRep)
        ):
            raise TypeError("incompatible attributes, use Attributes class")

        issues = ValidationIssues()
        data = SCIMDataContainer(data)
        for attr in attrs:
            attr_value = data.get(attr.rep)
            issues.merge(
                issues=self._check_presence(
                    value=attr_value,
                    direction=direction,
                    attr=attr,
                    attr_rep=attr.rep,
                ),
                location=(attr.rep.attr,),
            )

            if not isinstance(attr, Complex) or attr_value in [Invalid, Missing]:
                continue

            for sub_attr in attr.attrs:
                sub_attr_rep = BoundedAttrRep(attr.rep.schema, attr.rep.attr, sub_attr.rep.attr)
                if not attr.multi_valued:
                    issues.merge(
                        issues=self._check_presence(
                            value=attr_value.get(sub_attr.rep),
                            direction=direction,
                            attr=attr,
                            attr_rep=sub_attr_rep,
                        ),
                        location=(attr.rep.attr, sub_attr.rep.attr),
                    )
                    continue

                if attr_value is None:
                    issues.merge(
                        issues=self._check_presence(
                            value=None,
                            direction=direction,
                            attr=sub_attr,
                            attr_rep=sub_attr_rep,
                        ),
                        location=(attr.rep.attr, sub_attr.rep.attr),
                    )
                    continue

                for i, item in enumerate(attr_value):
                    item_value = item.get(sub_attr.rep)
                    if item_value is Invalid:
                        continue
                    issues.merge(
                        issues=self._check_presence(
                            value=item_value,
                            direction=direction,
                            attr=sub_attr,
                            attr_rep=sub_attr_rep,
                        ),
                        location=(attr.rep.attr, i, sub_attr.rep.attr),
                    )
        return issues

    def _check_presence(
        self,
        value: Any,
        direction: str,
        attr: Attribute,
        attr_rep: TAttrRep,
    ) -> ValidationIssues:
        issues = ValidationIssues()
        if value not in [None, "", [], Missing]:
            if direction == "REQUEST":
                return issues

            if attr.returned == AttributeReturn.NEVER:
                issues.add_error(
                    issue=ValidationError.restricted_or_not_requested(),
                    proceed=True,
                )

            elif attr.returned != AttributeReturn.ALWAYS and (
                (attr_rep in self._attr_reps and self._include is False)
                or (
                    attr_rep not in self._attr_reps
                    and not self._sub_attr_or_top_attr_in_attr_reps(attr_rep)
                    and self._include is True
                )
            ):
                issues.add_error(
                    issue=ValidationError.restricted_or_not_requested(),
                    proceed=True,
                )
        else:
            if (
                attr.required
                and attr_rep not in self._ignore_required
                and (
                    self._include is not True
                    or (attr_rep in self._attr_reps and self._include is True)
                    or (direction == "RESPONSE" and attr.returned == AttributeReturn.ALWAYS)
                )
            ):
                issues.add_error(
                    issue=ValidationError.missing(),
                    proceed=False,
                )
        return issues

    def _sub_attr_or_top_attr_in_attr_reps(self, attr_rep: TAttrRep) -> bool:
        if isinstance(attr_rep, AttrRep):
            return False

        for attr_rep_ in self._attr_reps:
            if (
                # sub-attr in attr names check
                not attr_rep.sub_attr
                and attr_rep.top_level_equals(attr_rep_)
                # top-attr in attr names check
                or (
                    attr_rep.sub_attr
                    and not attr_rep_.sub_attr
                    and attr_rep.top_level_equals(attr_rep_)
                )
            ):
                return True
        return False
