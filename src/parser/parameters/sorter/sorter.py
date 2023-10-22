from typing import Any, Dict, List, Optional, Tuple

from src.parser.attributes.attributes import AttributeName, ComplexAttribute
from src.parser.attributes import type as at
from src.parser.error import ValidationError, ValidationIssues
from src.parser.resource.schemas import Schema


class AlwaysLastKey:
    def __lt__(self, _):
        return False

    def __gt__(self, _):
        return True


class NonStrictStringKey:
    def __init__(self, value: str):
        self._value = value

    def __lt__(self, other):
        if isinstance(other, NonStrictStringKey):
            other = other._value

        if self._value < other and self._value.lower() < other.lower():
            return True
        return False

    def __gt__(self, other):
        if isinstance(other, NonStrictStringKey):
            other = other._value

        if self._value > other and self._value.lower() > other.lower():
            return True
        return False


class Sorter:
    def __init__(
        self,
        attr_name: AttributeName,
        schema: Optional[Schema],
        asc: bool = True,
        strict: bool = True,
    ):
        attr = None
        if schema is not None:
            attr = schema.get_attr(attr_name)
            if attr is None:
                raise ValueError(f"attribute {attr!r} not specified in schema {schema!r}")
            if isinstance(attr, ComplexAttribute):
                if not attr.multi_valued:
                    raise TypeError(f"complex attribute {attr!r} must be multivalued")
                if "primary" not in attr.sub_attributes or "value" not in attr.sub_attributes:
                    raise TypeError(
                        f"complex attribute must contain 'primary' and 'value'"
                        f"sub-attributes for sorting"
                    )
        self._attr_name = attr_name
        self._attr = attr
        self._schema = schema
        self._asc = asc
        self._default_value = AlwaysLastKey()
        self._strict = strict

    @property
    def attr_name(self) -> AttributeName:
        return self._attr_name

    @classmethod
    def parse(
        cls,
        by: str,
        asc: bool = True,
        schema: Optional[Schema] = None,
        strict: bool = True,
    ) -> Tuple[Optional["Sorter"], ValidationIssues]:
        issues = ValidationIssues()
        attr_name = AttributeName.parse(by)
        if attr_name is None:
            issues.add(
                issue=ValidationError.bad_attribute_name(by),
                proceed=False,
            )

        if not issues.can_proceed():
            return None, issues

        if schema is not None:
            attr = schema.get_attr(attr_name)
            if attr is None:
                issues.add(
                    issue=ValidationError.unknown_sort_by_attr(str(attr_name)),
                    proceed=False,
                )
            if not issues.can_proceed():
                return None, issues

            if isinstance(attr, ComplexAttribute):
                if not attr.multi_valued:
                    issues.add(
                        issue=ValidationError.complex_attr_is_not_multivalued(by),
                        proceed=False,
                    )
                if "primary" not in attr.sub_attributes or "value" not in attr.sub_attributes:
                    issues.add(
                        issue=ValidationError.complex_attr_does_not_contain_primary_sub_attr(by),
                        proceed=False,
                    )
                if not issues.can_proceed():
                    return None, issues

        return Sorter(attr_name=attr_name, schema=schema, asc=asc, strict=strict), issues

    def __call__(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not any(self._get_value(item) for item in data):
            return data
        key = self._attr_key if self._schema else self._attr_key_no_schema
        return sorted(data, key=key, reverse=not self._asc)

    def _get_value(self, item: Dict[str, Any]) -> Optional[Any]:
        value = (  # TODO: improve attribute case-insensitivity handling
            item.get(self._attr_name.full_attr)
            or item.get(self._attr_name.full_attr.lower())
            or item.get(self._attr_name.attr)
            or item.get(self._attr_name.attr.lower())
        )
        if value is None:
            return None
        if self._attr_name.sub_attr:
            if not isinstance(value, Dict):
                return None
            value = (
                value.get(self._attr_name.sub_attr)
                or value.get(self._attr_name.sub_attr.lower())
            )
        return value

    def _get_key(self, value):
        if not value:
            return self._default_value

        if not isinstance(value, str):
            return value

        if self._attr is not None and self._attr.type == at.String and not self._attr.case_exact:
            return value.lower()

        return value if self._strict else NonStrictStringKey(value)

    def _attr_key(self, item):
        value = None
        item_value = self._get_value(item)
        if item_value and self._attr.multi_valued:
            if isinstance(self._attr, ComplexAttribute):
                for v in item_value:
                    if v.get("primary"):
                        value = v.get("value")
                        break
            else:
                value = item_value[0]
        else:
            value = item_value
        return self._get_key(value)

    def _attr_key_no_schema(self, item):
        value = None
        item_value = self._get_value(item)
        if isinstance(item_value, List):
            for v in item_value:
                if isinstance(v, Dict):
                    if v.get("primary") and v.get("value"):
                        value = v.get("value")
                        break
                else:
                    value = self._get_key(v)
                    break
        else:
            value = item_value
        return self._get_key(value)
