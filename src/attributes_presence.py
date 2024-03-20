from typing import Any, Iterable, List, Optional, Tuple, Union

from src.data.attributes import Attribute, AttributeReturn, Attributes
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
    def parse(
        cls, attr_reps: Iterable[str], include: Optional[bool] = None
    ) -> Tuple[Union[Invalid, "AttributePresenceChecker"], ValidationIssues]:
        issues = ValidationIssues()
        parsed_attr_reps = []
        all_parsed = True
        for attr_rep_ in attr_reps:
            attr_rep = AttrRep.parse(attr_rep_)
            if attr_rep:
                attr_location = (
                    (attr_rep.attr, attr_rep.sub_attr) if attr_rep.sub_attr else (attr_rep.attr,)
                )
            else:
                attr_location = (attr_rep_,)
            if attr_rep is Invalid:
                issues.add(
                    issue=ValidationError.bad_attribute_name(attr_rep_),
                    location=attr_location,
                    proceed=False,
                )

            if issues.can_proceed(attr_location):
                parsed_attr_reps.append(attr_rep)
            else:
                all_parsed = False

        if all_parsed:
            return AttributePresenceChecker(parsed_attr_reps, include), issues
        return Invalid, issues

    def __call__(
        self,
        data: SCIMDataContainer,
        attrs: Attributes,
        direction: str,
    ) -> ValidationIssues:
        issues = ValidationIssues()

        for attr in attrs:
            top_attr_rep = AttrRep(schema=attr.rep.schema, attr=attr.rep.attr)
            top_attr = attrs.get(top_attr_rep)

            if attr.rep.sub_attr and top_attr.multi_valued:
                value = data[top_attr_rep]
                if value in [Invalid, Missing]:
                    continue

                if value in [None, Missing]:
                    issues.merge(
                        issues=self._check_presence(
                            value=value,
                            direction=direction,
                            attr=attr,
                            attr_rep=attr.rep,
                        ),
                        location=(attr.rep.attr, attr.rep.sub_attr),
                    )
                else:
                    for i, item in enumerate(value):
                        item_value = item[AttrRep(attr=attr.rep.sub_attr)]
                        if item_value is Invalid:
                            continue

                        issues.merge(
                            issues=self._check_presence(
                                value=item[AttrRep(attr=attr.rep.sub_attr)],
                                direction=direction,
                                attr=attr,
                                attr_rep=attr.rep,
                            ),
                            location=(attr.rep.attr, i, attr.rep.sub_attr),
                        )
            else:
                value = data[attr.rep]
                if value is Invalid:
                    continue

                attr_location = (
                    (attr.rep.attr, attr.rep.sub_attr) if attr.rep.sub_attr else (attr.rep.attr,)
                )
                issues.merge(
                    issues=self._check_presence(
                        value=data[attr.rep],
                        direction=direction,
                        attr=attr,
                        attr_rep=attr.rep,
                    ),
                    location=attr_location,
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
            if direction != "RESPONSE":
                return issues

            if attr.returned == AttributeReturn.NEVER:
                issues.add(
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
                issues.add(
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
                issues.add(
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
