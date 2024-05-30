from typing import Any, Collection, Generic, Optional, TypeVar, Union, overload

from src.container import AttrRep, BoundedAttrRep, Invalid, Missing, SCIMDataContainer
from src.data.attributes import Attribute, AttributeIssuer, AttributeReturn, Complex
from src.data.schemas import BaseSchema
from src.error import ValidationError, ValidationIssues

TAttrRep = TypeVar("TAttrRep", bound=Union[AttrRep, BoundedAttrRep])


class AttributePresenceValidator(Generic[TAttrRep]):
    @overload
    def __init__(
        self,
        attr_reps: Collection[TAttrRep],
        include: bool,
        ignore_issuer: Optional[Collection[TAttrRep]] = None,
    ):
        """
        Checks attributes presence according to the data flow direction,
        attribute properties, and specified inclusion / exclusion.

        :param attr_reps: specifies which attributes should be included or excluded from the data.
        :param include: if set to True, it means the attributes should be included.
            Excluded otherwise.
        :param ignore_issuer: specifies for which attributes the attribute issuer configuration
            should be ignored when making presence checks.
        """

    @overload
    def __init__(self, ignore_issuer: Optional[Collection[TAttrRep]] = None):
        """
        Checks attributes presence according to the data flow direction and attribute properties.

        :param ignore_issuer: specifies for which attributes the attribute issuer configuration
            should be ignored when making presence checks.
        """

    def __init__(
        self,
        attr_reps: Optional[Collection[TAttrRep]] = None,
        include: Optional[bool] = None,
        ignore_issuer: Optional[Collection[TAttrRep]] = None,
    ):
        self._attr_reps = list(attr_reps or [])
        self._include = include

        if self._attr_reps and self._include is None:
            raise ValueError("'include' must be specified if 'attr_reps' is specified")

        self._ignore_issuer = list(ignore_issuer or [])

    @property
    def attr_reps(self) -> list[TAttrRep]:
        return self._attr_reps

    @property
    def include(self) -> Optional[bool]:
        return self._include

    def _ensure_valid_obj(self, schema_or_complex: Union[BaseSchema, Complex]):
        attr_rep_ = next(iter(self._attr_reps), None)
        ignore = next(iter(self._ignore_issuer), None)

        if isinstance(schema_or_complex, Complex) and (
            isinstance(attr_rep_, BoundedAttrRep) or isinstance(ignore, BoundedAttrRep)
        ):
            raise TypeError(
                "provided complex attribute, but schema is required for bounded attributes"
            )
        elif isinstance(schema_or_complex, BaseSchema) and (
            isinstance(attr_rep_, AttrRep) or isinstance(ignore, AttrRep)
        ):
            raise TypeError(
                "provided schema, but complex attribute is required for non-bounded attributes"
            )

    def __call__(
        self,
        data: Union[dict[str, Any], SCIMDataContainer],
        schema_or_complex: Union[BaseSchema, Complex],
        direction: str,
    ) -> ValidationIssues:
        issues = ValidationIssues()
        self._ensure_valid_obj(schema_or_complex)
        data = SCIMDataContainer(data)
        for attr in schema_or_complex.attrs:
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
                            value=attr_value.get(sub_attr.rep) if attr_value else None,
                            direction=direction,
                            attr=attr,
                            attr_rep=sub_attr_rep,
                        ),
                        location=(attr.rep.attr, sub_attr.rep.attr),
                    )
                    continue

                if not attr_value:
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
                if attr.issuer == AttributeIssuer.SERVER and attr not in self._ignore_issuer:
                    issues.add_error(
                        issue=ValidationError.must_not_be_provided(),
                        proceed=True,
                    )
                return issues

            if attr.returned == AttributeReturn.NEVER:
                issues.add_error(
                    issue=ValidationError.must_not_be_returned(),
                    proceed=True,
                )

            elif attr.returned != AttributeReturn.ALWAYS and (
                (attr_rep in self._attr_reps and not self._include)
                or (
                    attr_rep not in self._attr_reps
                    and not self._sub_attr_or_top_attr_in_attr_reps(attr_rep)
                    and self._include
                )
            ):
                issues.add_error(
                    issue=ValidationError.must_not_be_returned(),
                    proceed=True,
                )
        else:
            if (
                attr.required
                and not (
                    isinstance(attr_rep, BoundedAttrRep)
                    and attr_rep.extension
                    and not attr_rep.extension_required
                )
                and not (
                    direction == "REQUEST"
                    and attr.issuer == AttributeIssuer.SERVER
                    and attr not in self._ignore_issuer
                )
                and (
                    not self._attr_reps
                    or (attr_rep in self._attr_reps and self._include)
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
                and attr_rep.parent_equals(attr_rep_)
                # top-attr in attr names check
                or (
                    attr_rep.sub_attr
                    and not attr_rep_.sub_attr
                    and attr_rep.parent_equals(attr_rep_)
                )
            ):
                return True
        return False