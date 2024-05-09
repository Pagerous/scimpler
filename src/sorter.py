import functools
from typing import Any, List, Optional, Sequence, Union

from src.attributes import Attribute, AttributeWithCaseExact, Complex, String
from src.container import BoundedAttrRep, Missing, SCIMDataContainer
from src.schemas import BaseSchema, ResourceSchema


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

        value = self._value
        other_value = other._value

        if not isinstance(value, str) or not isinstance(other_value, str):
            return value < other_value

        if isinstance(self._attr, String):
            value = self._attr.precis.enforce(value)
        if isinstance(other._attr, String):
            other_value = other._attr.precis.enforce(other_value)

        if (
            isinstance(self._attr, AttributeWithCaseExact)
            and self._attr.case_exact
            or isinstance(other._attr, AttributeWithCaseExact)
            and other._attr.case_exact
        ):
            return value < other_value

        return value.lower() < other_value.lower()


class Sorter:
    def __init__(self, attr_rep: BoundedAttrRep, asc: bool = True):
        self._attr_rep = attr_rep
        self._asc = asc
        self._default_value = AlwaysLastKey()

    @property
    def attr_rep(self) -> BoundedAttrRep:
        return self._attr_rep

    @property
    def asc(self) -> bool:
        return self._asc

    def __call__(
        self,
        data: List[SCIMDataContainer],
        schema: Union[ResourceSchema, Sequence[ResourceSchema]],
    ) -> List[SCIMDataContainer]:
        if not any(item.get(self._attr_rep) for item in data):
            return data

        if not isinstance(schema, ResourceSchema) and len(set(schema)) == 1:
            schema = schema[0]

        if isinstance(schema, ResourceSchema):
            key = functools.partial(self._attr_key, schema=schema)
        else:
            key = self._attr_key_many_schemas(data, schema)

        return sorted(data, key=key, reverse=not self._asc)

    def _get_key(self, value: Any, attr: Optional[Attribute]):
        if not value or attr is None:
            return self._default_value

        if not isinstance(value, str):
            return value

        if attr.BASE_TYPE != str:
            return self._default_value

        return StringKey(value, attr)

    def _attr_key_many_schemas(self, data: List[SCIMDataContainer], schemas: Sequence[BaseSchema]):
        def attr_key(item):
            schema = schemas[data.index(item)]
            return self._attr_key(item, schema)

        return attr_key

    def _attr_key(self, item: SCIMDataContainer, schema: BaseSchema):
        attr = schema.attrs.get(self._attr_rep)
        value = None
        if attr is not None:
            item_value = item.get(self._attr_rep)
            if item_value is not Missing and attr.multi_valued:
                if isinstance(attr, Complex):
                    for v in item_value:
                        primary = v.get("primary")
                        if primary is True:
                            for sub_attr in attr.attrs:
                                if sub_attr.rep.attr.lower() == "value":
                                    attr = sub_attr
                                    value = v.get("value")
                                    break
                            else:
                                attr = None
                                value = None
                            break
                else:
                    value = item_value[0]
            else:
                value = item_value
        return self._get_key(value, attr)
