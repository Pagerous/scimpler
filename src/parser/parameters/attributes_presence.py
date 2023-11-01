from typing import Any, Dict, Iterable, Optional, Tuple

from src.parser.attributes.attributes import AttributeName, AttributeReturn, extract
from src.parser.error import ValidationError, ValidationIssues
from src.parser.resource.schemas import Schema


class AttributePresenceChecker:
    def __init__(
        self,
        attr_names: Optional[Iterable[AttributeName]] = None,
        include: Optional[bool] = None,
        schema: Optional[Schema] = None,
    ):
        attr_names = list(attr_names or [])
        if schema is not None:
            for attr_name in attr_names:
                if attr_name not in schema.all_attr_names:
                    raise ValueError(f"no attribute {attr_name!r} in schema {schema!r}")

        self._attr_names = attr_names
        self._include = include
        self._schema = schema

    def with_schema(self, schema: Schema):
        for attr_name in self._attr_names:
            if attr_name not in schema.all_attr_names:
                break
        else:
            self._schema = schema

    @classmethod
    def parse(
        cls,
        attr_names: Iterable[str],
        include: Optional[bool] = None,
        schema: Optional[Schema] = None,
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

            if schema is not None and attr_name not in schema.all_attr_names:
                issues.add(
                    issue=ValidationError.attr_not_in_schema(str(attr_name), str(schema)),
                    location=attr_location,
                    proceed=False,
                )

            if issues.can_proceed(attr_location):
                parsed_attr_names.append(attr_name)
            else:
                all_parsed = False

        if all_parsed:
            return AttributePresenceChecker(parsed_attr_names, include, schema), issues
        return None, issues

    def __call__(self, data: Dict[str, Any], direction: str) -> ValidationIssues:
        issues = ValidationIssues()
        if self._schema is None:
            raise ValueError("schema is required to check attribute presence")

        for attr_name in self._schema.all_attr_names:
            value = extract(attr_name, data)
            attr = self._schema.get_attr(attr_name)
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
                ):
                    issues.add(
                        issue=ValidationError.missing(),
                        proceed=False,
                        location=attr_location,
                    )
        return issues
