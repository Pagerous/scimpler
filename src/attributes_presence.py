from typing import Any, Dict, Iterable, List, Optional, Union

from src.data.attributes import Attribute, AttributeReturn, Attributes, Complex
from src.data.container import AttrRep, Invalid, Missing, SCIMDataContainer
from src.error import ValidationError, ValidationIssues


class AttributePresenceChecker:
    def __init__(
        self,
        attr_reps: Optional[Iterable[AttrRep]] = None,
        include: Optional[bool] = None,
        ignore_required: Optional[Iterable[AttrRep]] = None,
    ):
        self._attr_reps = list(attr_reps or [])
        self._include = include
        self._ignore_required = list(ignore_required or [])

    @property
    def attr_reps(self) -> List[AttrRep]:
        return self._attr_reps

    @property
    def include(self) -> Optional[bool]:
        return self._include

    @classmethod
    def validate(cls, attr_reps: Iterable[str]) -> ValidationIssues:
        issues = ValidationIssues()
        for attr_rep in attr_reps:
            try:
                AttrRep.deserialize(attr_rep)
            except ValueError:
                issues.add_error(
                    issue=ValidationError.bad_attribute_name(attr_rep),
                    location=(attr_rep,),
                    proceed=False,
                )
        return issues

    @classmethod
    def deserialize(
        cls, attr_reps: Iterable[str], include: Optional[bool] = None
    ) -> "AttributePresenceChecker":
        return AttributePresenceChecker(
            [AttrRep.deserialize(attr_rep) for attr_rep in attr_reps], include
        )

    def __call__(
        self,
        data: Union[Dict[str, Any], SCIMDataContainer],
        attrs: Attributes,
        direction: str,
    ) -> ValidationIssues:
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
                sub_attr_rep = AttrRep(attr.rep.schema, attr.rep.attr, sub_attr.rep.attr)
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
        attr_rep: AttrRep,
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

    def _sub_attr_or_top_attr_in_attr_reps(self, attr_rep: AttrRep) -> bool:
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
