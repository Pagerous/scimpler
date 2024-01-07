import functools
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from src.parser.attributes import type as at
from src.parser.attributes.attributes import (
    Attribute,
    AttributeName,
    ComplexAttribute,
    extract,
)
from src.parser.error import ValidationError, ValidationIssues
from src.parser.schemas import Schema


class AlwaysLastKey:
    def __lt__(self, _):
        return False

    def __gt__(self, _):
        return True


class StringKey:
    def __init__(self, value: str, attr: Attribute):
        self._value = value
        self._attr = attr

    def __lt__(self, other):
        if not isinstance(other, StringKey):
            if isinstance(other, AlwaysLastKey):
                return True
            raise TypeError(
                f"'<' not supported between instances of 'StringKey' and '{type(other).__name__}'"
            )

        if self._attr.case_exact or other._attr.case_exact:
            return self._value < other._value

        return self._value.lower() < other._value.lower()


class Sorter:
    def __init__(self, attr_name: AttributeName, asc: bool = True):
        self._attr_name = attr_name
        self._asc = asc
        self._default_value = AlwaysLastKey()

    @property
    def attr_name(self) -> AttributeName:
        return self._attr_name

    @classmethod
    def parse(cls, by: str, asc: bool = True) -> Tuple[Optional["Sorter"], ValidationIssues]:
        issues = ValidationIssues()
        attr_name = AttributeName.parse(by)
        if attr_name is None:
            issues.add(
                issue=ValidationError.bad_attribute_name(by),
                proceed=False,
            )

        if not issues.can_proceed():
            return None, issues

        return (
            Sorter(attr_name=attr_name, asc=asc),
            issues,
        )

    def __call__(
        self,
        data: List[Dict[str, Any]],
        schema: Union[Schema, Sequence[Schema]],
    ) -> List[Dict[str, Any]]:
        if not any(extract(self._attr_name, item) for item in data):
            return data

        if isinstance(schema, Schema):
            key = functools.partial(self._attr_key, schema=schema)
        else:
            key = self._attr_key_many_schemas(data, schema)

        return sorted(data, key=key, reverse=not self._asc)

    def _get_key(self, value: Any, attr: Optional[Attribute]):
        if not value or attr is None:
            return self._default_value

        if not isinstance(value, str):
            return value

        if attr.type is not at.String:
            return self._default_value

        return StringKey(value, attr)

    def _attr_key_many_schemas(self, data: List[Dict[str, Any]], schemas: Sequence[Schema]):
        def attr_key(item):
            schema = schemas[data.index(item)]
            return self._attr_key(item, schema)

        return attr_key

    def _attr_key(self, item: Dict[str, Any], schema: Schema):
        attr = schema.get_attr(self._attr_name)
        value = None
        if attr is not None:
            item_value = extract(self._attr_name, item)
            if item_value and attr.multi_valued:
                if isinstance(attr, ComplexAttribute):
                    for v in item_value:
                        if v.get("primary"):
                            attr = attr.sub_attributes.get("value")
                            value = v.get("value")
                            break
                else:
                    value = item_value[0]
            else:
                value = item_value
        return self._get_key(value, attr)
