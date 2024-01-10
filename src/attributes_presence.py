from typing import Any, Dict, Iterable, Optional, Tuple

from src.attributes.attributes import AttributeName, AttributeReturn, extract
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
            value = extract(attr_name, data)
            attr = schema.get_attr(attr_name)
            attr_location = (
                (attr_name.attr, attr_name.sub_attr) if attr_name.sub_attr else (attr_name.attr,)
            )
            if value:
                if direction == "RESPONSE" and (
                    attr.returned == AttributeReturn.NEVER
                    or (
                        attr.returned != AttributeReturn.ALWAYS
                        and attr_name in self._attr_names
                        and self._include is False
                    )
                ):
                    issues.add(
                        issue=ValidationError.restricted_or_not_requested(),
                        proceed=True,
                        location=attr_location,
                    )
            else:
                if attr.required and (
                    (attr_name in self._attr_names and self._include is True)
                    or (direction == "RESPONSE" and attr.returned == AttributeReturn.ALWAYS)
                    or attr_name not in self._ignore_required
                ):
                    issues.add(
                        issue=ValidationError.missing(),
                        proceed=False,
                        location=attr_location,
                    )
        return issues
