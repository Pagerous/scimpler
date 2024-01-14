from typing import Any, Dict, Iterable, Optional, Tuple

from src.attributes.attributes import Attribute, AttributeName, AttributeReturn, extract
from src.error import ValidationError, ValidationIssues
from src.schemas import Schema


class AttributePresenceChecker:
    def __init__(
        self,
        attr_names: Optional[Iterable[AttributeName]] = None,
        include: Optional[bool] = None,
        ignore_required: Optional[Iterable[AttributeName]] = None,
    ):
        self._attr_names = list(attr_names or [])
        self._include = include
        self._ignore_required = list(ignore_required or [])

    @classmethod
    def parse(
        cls,
        attr_names: Iterable[str],
        include: Optional[bool] = None,
    ) -> Tuple[Optional["AttributePresenceChecker"], ValidationIssues]:
        issues = ValidationIssues()
        parsed_attr_names = []
        all_parsed = True
        for attr_name_ in attr_names:
            attr_name = AttributeName.parse(attr_name_)
            if attr_name:
                attr_location = (
                    (attr_name.attr, attr_name.sub_attr)
                    if attr_name.sub_attr
                    else (attr_name.attr,)
                )
            else:
                attr_location = (attr_name_,)
            if attr_name is None:
                issues.add(
                    issue=ValidationError.bad_attribute_name(attr_name_),
                    location=attr_location,
                    proceed=False,
                )

            if issues.can_proceed(attr_location):
                parsed_attr_names.append(attr_name)
            else:
                all_parsed = False

        if all_parsed:
            return AttributePresenceChecker(parsed_attr_names, include), issues
        return None, issues

    def __call__(self, data: Dict[str, Any], schema: Schema, direction: str) -> ValidationIssues:
        issues = ValidationIssues()

        for attr_name in schema.all_attr_names:
            attr = schema.get_attr(attr_name)
            top_attr_name = AttributeName(schema=attr_name.schema, attr=attr_name.attr)
            top_attr = schema.get_attr(top_attr_name)

            if attr_name.sub_attr and top_attr.multi_valued:
                value = extract(top_attr_name, data)
                if value is None:
                    issues.merge(
                        issues=self._check_presence(
                            value=None,
                            direction=direction,
                            attr=attr,
                            attr_name=attr_name,
                        ),
                        location=(attr_name.attr, attr_name.sub_attr),
                    )
                else:
                    for i, item in enumerate(value):
                        item_value = extract(AttributeName(attr=attr_name.sub_attr), item)
                        issues.merge(
                            issues=self._check_presence(
                                value=item_value,
                                direction=direction,
                                attr=attr,
                                attr_name=attr_name,
                            ),
                            location=(attr_name.attr, i, attr_name.sub_attr),
                        )
            else:
                attr_location = (
                    (attr_name.attr, attr_name.sub_attr)
                    if attr_name.sub_attr
                    else (attr_name.attr,)
                )
                issues.merge(
                    issues=self._check_presence(
                        value=extract(attr_name, data),
                        direction=direction,
                        attr=attr,
                        attr_name=attr_name,
                    ),
                    location=attr_location,
                )

        return issues

    def _check_presence(
        self,
        value: Any,
        direction: str,
        attr: Attribute,
        attr_name: AttributeName,
    ) -> ValidationIssues:
        issues = ValidationIssues()
        if value not in [None, "", []]:
            if direction != "RESPONSE":
                return issues

            if attr.returned == AttributeReturn.NEVER:
                issues.add(
                    issue=ValidationError.restricted_or_not_requested(),
                    proceed=True,
                )

            elif attr.returned != AttributeReturn.ALWAYS and (
                (attr_name in self._attr_names and self._include is False)
                or (
                    attr_name not in self._attr_names
                    and not self._sub_attr_or_top_attr_in_attr_names(attr_name)
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
                and attr_name not in self._ignore_required
                and (
                    self._include is not True
                    or (attr_name in self._attr_names and self._include is True)
                    or (direction == "RESPONSE" and attr.returned == AttributeReturn.ALWAYS)
                )
            ):
                issues.add(
                    issue=ValidationError.missing(),
                    proceed=False,
                )
        return issues

    def _sub_attr_or_top_attr_in_attr_names(self, attr_name: AttributeName) -> bool:
        for attr_name_ in self._attr_names:
            if (
                not attr_name.sub_attr and attr_name.top_level_equals(attr_name_)
                or (
                    attr_name.sub_attr
                    and not attr_name_.sub_attr
                    and attr_name.top_level_equals(attr_name_)
                )
            ):
                return True
        return False
