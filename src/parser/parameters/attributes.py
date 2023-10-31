from typing import Any, Dict, Iterable, Optional, Tuple

from src.parser.attributes.attributes import AttributeName, AttributeReturn
from src.parser.error import ValidationError, ValidationIssues
from src.parser.resource.schemas import Schema


class AttributePresenceChecker:
    def __init__(
        self, attr_names: Iterable[AttributeName], include: bool, schema: Optional[Schema] = None
    ):
        if schema is not None:
            for attr_name in attr_names:
                if schema.get_attr(attr_name) is None:
                    raise ValueError(f"no attribute {attr_name!r} in schema {schema!r}")
        self._attr_names = attr_names
        self._include = include
        self._schema = schema

    @classmethod
    def parse(
        cls,
        attrs: Iterable[str],
        include: bool,
        schema: Optional[Schema] = None,
    ) -> Tuple[Optional["AttributePresenceChecker"], ValidationIssues]:
        issues = ValidationIssues()
        parsed_attr_names = []
        all_parsed = True
        for attr_name_ in attrs:
            attr_name = AttributeName.parse(attr_name_)
            if attr_name is None:
                issues.add(
                    issue=ValidationError.bad_attribute_name(attr_name_),
                    location=(attr_name_,),
                    proceed=False,
                )
                continue

            if schema is not None:
                attr = schema.get_attr(attr_name)
                if attr is None:
                    issues.add(
                        issue=ValidationError.attr_not_in_schema(str(attr_name), str(schema)),
                        location=(attr_name_,),
                        proceed=False,
                    )
                else:
                    if attr.returned == AttributeReturn.ALWAYS and not include:
                        pass  # TODO: add warning here

            if issues.can_proceed((attr_name_,)):
                parsed_attr_names.append(attr_name)
            else:
                all_parsed = False

        if all_parsed:
            return AttributePresenceChecker(parsed_attr_names, include, schema), issues
        return None, issues

    def __call__(self, data: Dict[str, Any]) -> ValidationIssues:
        pass
