import base64
from datetime import datetime

import pytest

from src.assets.schemas import User
from src.container import (
    AttrName,
    AttrRep,
    AttrRepFactory,
    BoundedAttrRep,
    SCIMDataContainer,
)
from src.data.attrs import (
    AttributeUniqueness,
    Binary,
    Boolean,
    Complex,
    DateTime,
    Decimal,
    ExternalReference,
    Integer,
    SCIMReference,
    String,
    URIReference,
)
from src.error import ValidationError, ValidationIssues


def test_validation_is_skipped_if_value_not_provided():
    attr = String(name="some_attr", required=True)

    issues = attr.validate(value=None)

    assert issues.to_dict(msg=True) == {}


def test_multi_valued_attribute_validation_fails_if_not_provided_list():
    attr = String(name="some_attr", multi_valued=True)

    issues = attr.validate("non-list")

    assert issues.to_dict() == {"_errors": [{"code": 2}]}


def test_multi_valued_attribute_validation_succeeds_if_provided_list_or_tuple():
    attr = String(name="some_attr", multi_valued=True)

    issues = attr.validate(["a", "b", "c"])

    assert issues.to_dict(msg=True) == {}


def test_multi_valued_attribute_values_are_validate_separately():
    attr = String(name="some_attr", multi_valued=True)

    issues = attr.validate(["a", 123])

    assert issues.to_dict() == {"1": {"_errors": [{"code": 2}]}}


def test_complex_attribute_sub_attributes_are_validated_separately():
    attr = Complex(
        sub_attributes=[
            Integer(name="sub_attr_1", required=True),
            Integer(name="sub_attr_2"),
        ],
        name="complex_attr",
    )
    expected_issues = {
        "sub_attr_1": {
            "_errors": [
                {
                    "code": 2,
                }
            ]
        },
        "sub_attr_2": {
            "_errors": [
                {
                    "code": 2,
                }
            ]
        },
    }

    issues = attr.validate(SCIMDataContainer({"sub_attr_1": "123", "sub_attr_2": "123"}))

    assert issues.to_dict() == expected_issues


def test_multivalued_complex_attribute_sub_attributes_are_validated_separately():
    attr = Complex(
        sub_attributes=[
            String("sub_attr_1", required=True),
            Integer("sub_attr_2"),
        ],
        multi_valued=True,
        name="complex_attr",
    )
    expected_issues = {
        "0": {
            "sub_attr_1": {
                "_errors": [
                    {
                        "code": 2,
                    }
                ]
            },
            "sub_attr_2": {
                "_errors": [
                    {
                        "code": 2,
                    }
                ]
            },
        },
        "1": {
            "sub_attr_1": {
                "_errors": [
                    {
                        "code": 2,
                    }
                ]
            },
        },
    }

    issues = attr.validate(
        value=[
            SCIMDataContainer({"sub_attr_1": 123, "sub_attr_2": "123"}),
            SCIMDataContainer({"sub_attr_1": 123, "sub_attr_2": 123}),
        ],
    )

    assert issues.to_dict() == expected_issues


@pytest.mark.parametrize(
    (
        "input_",
        "attr_rep_type",
        "expected_schema",
        "expected_attr",
        "expected_sub_attr",
    ),
    (
        ("userName", AttrRep, "", "userName", None),
        ("name.firstName", AttrRep, "", "name", "firstName"),
        (
            "urn:ietf:params:scim:schemas:core:2.0:User:userName",
            BoundedAttrRep,
            "urn:ietf:params:scim:schemas:core:2.0:User",
            "userName",
            None,
        ),
        (
            "urn:ietf:params:scim:schemas:core:2.0:User:name.firstName",
            BoundedAttrRep,
            "urn:ietf:params:scim:schemas:core:2.0:User",
            "name",
            "firstName",
        ),
        ("weirdo-$", AttrRep, "", "weirdo-$", None),
        ("attr.weirdo-$", AttrRep, "", "attr", "weirdo-$"),
    ),
)
def test_attribute_identifier_is_deserialized(
    input_, attr_rep_type, expected_schema, expected_attr, expected_sub_attr
):
    issues = AttrRepFactory.validate(input_)
    assert issues.to_dict(msg=True) == {}

    attr_rep = AttrRepFactory.deserialize(input_)
    assert isinstance(attr_rep, attr_rep_type)
    if isinstance(attr_rep, AttrName):
        assert expected_attr == attr_rep
    else:
        assert attr_rep.attr == expected_attr
        assert attr_rep.sub_attr == expected_sub_attr
        if isinstance(attr_rep, BoundedAttrRep):
            assert attr_rep.schema == expected_schema


@pytest.mark.parametrize(
    "input_",
    (
        "attr_1.sub_attr_1.sub_attr_2",
        "",
        "attr with spaces",
        'emails[type eq "work"]',
        "(attr_with_parenthesis)",
        "urn:ietf:params:scim:schemas:core:2.0:User:name.firstName.blahblah",
        "non:existing:schema:blahblah",
    ),
)
def test_attribute_identifier_is_not_deserialized_when_bad_input(input_):
    issues = AttrRepFactory.validate(input_)
    assert issues.to_dict() == {"_errors": [{"code": 17}]}

    with pytest.raises(ValueError):
        AttrRepFactory.deserialize(input_)


def test_validation_fails_in_not_one_of_canonical_values():
    attr = String(
        name="attr",
        canonical_values=["A", "B", "C"],
        restrict_canonical_values=True,
    )
    expected_issues = {"_errors": [{"code": 9}]}

    assert attr.validate("D").to_dict() == expected_issues


def test_validation_fails_in_not_one_of_canonical_values__multivalued():
    attr = String(
        name="attr",
        canonical_values=["A", "B", "C"],
        restrict_canonical_values=True,
        multi_valued=True,
    )
    expected_issues = {"1": {"_errors": [{"code": 9}]}}

    assert attr.validate(["A", "D", "C"]).to_dict() == expected_issues


def test_validation_returns_warning_in_not_one_of_canonical_values():
    attr = String(
        name="attr",
        canonical_values=["A", "B", "C"],
        restrict_canonical_values=False,
    )
    expected_issues = {"_warnings": [{"code": 1}]}

    assert attr.validate("D").to_dict() == expected_issues


def test_validation_returns_warning_in_not_one_of_canonical_values__multivalued():
    attr = String(
        name="attr",
        canonical_values=["A", "B", "C"],
        restrict_canonical_values=False,
        multi_valued=True,
    )
    expected_issues = {"1": {"_warnings": [{"code": 1}]}}

    assert attr.validate(["A", "D", "C"]).to_dict() == expected_issues


@pytest.mark.parametrize(
    ("input_value", "attr", "expected_issues"),
    (
        (
            1.0,
            Integer("int"),
            {
                "_errors": [
                    {
                        "code": 2,
                        "context": {"expected": "integer"},
                    }
                ]
            },
        ),
        (
            123,
            String("str"),
            {
                "_errors": [
                    {
                        "code": 2,
                        "context": {"expected": "string"},
                    }
                ]
            },
        ),
        (
            "123",
            Integer("int"),
            {
                "_errors": [
                    {
                        "code": 2,
                        "context": {"expected": "integer"},
                    }
                ]
            },
        ),
        (
            1.2,
            Integer("int"),
            {
                "_errors": [
                    {
                        "code": 2,
                        "context": {"expected": "integer"},
                    }
                ]
            },
        ),
        (
            "123",
            Decimal("decimal"),
            {
                "_errors": [
                    {
                        "code": 2,
                        "context": {"expected": "decimal"},
                    }
                ]
            },
        ),
        (
            "Bad",
            Boolean("bool"),
            {
                "_errors": [
                    {
                        "code": 2,
                        "context": {"expected": "boolean"},
                    }
                ]
            },
        ),
        (
            123,
            URIReference("uri"),
            {
                "_errors": [
                    {
                        "code": 2,
                        "context": {"expected": "reference"},
                    }
                ]
            },
        ),
        (
            123,
            SCIMReference("scim", reference_types=["Users"]),
            {
                "_errors": [
                    {
                        "code": 2,
                        "context": {"expected": "reference"},
                    }
                ]
            },
        ),
        (
            "/Groups/123",
            SCIMReference("scim", reference_types=["User"]),
            {
                "_errors": [
                    {
                        "code": 16,
                        "context": {
                            "allowed_resources": ["User"],
                        },
                    }
                ]
            },
        ),
        (
            123,
            ExternalReference("external"),
            {
                "_errors": [
                    {
                        "code": 2,
                        "context": {"expected": "reference"},
                    }
                ]
            },
        ),
        (
            "/not/absolute/url",
            ExternalReference("external"),
            {"_errors": [{"code": 1, "context": {}}]},
        ),
        (
            123,
            Binary("binary"),
            {
                "_errors": [
                    {
                        "code": 2,
                        "context": {"expected": "binary"},
                    }
                ]
            },
        ),
        (
            "abcd=abc",
            Binary("binary"),
            {"_errors": [{"code": 3, "context": {"expected": "base64"}}]},
        ),
        ("abc", Binary("binary"), {"_errors": [{"code": 3, "context": {"expected": "base64"}}]}),
        (
            123,
            DateTime("datetime"),
            {
                "_errors": [
                    {
                        "code": 2,
                        "context": {"expected": "dateTime"},
                    }
                ]
            },
        ),
        (
            "2022/05/05 12:34:56",
            DateTime("datetime"),
            {"_errors": [{"code": 1, "context": {}}]},
        ),
        (
            123,
            Complex("complex", sub_attributes=[]),
            {
                "_errors": [
                    {
                        "code": 2,
                        "context": {"expected": "complex"},
                    }
                ]
            },
        ),
    ),
)
def test_validate_bad_type(input_value, attr, expected_issues):
    issues = attr.validate(input_value)

    assert issues.to_dict(ctx=True) == expected_issues


@pytest.mark.parametrize(
    ("input_value", "attr"),
    (
        (
            "123",
            String("str"),
        ),
        (
            123,
            Integer("int"),
        ),
        (
            1,
            Decimal("decimal"),
        ),
        (
            1.2,
            Decimal("decimal"),
        ),
        (
            True,
            Boolean("bool"),
        ),
        (
            "any:unique:resource:identifier",
            URIReference("uri"),
        ),
        (
            "/Users/123",
            SCIMReference("scim", reference_types=["User"]),
        ),
        (
            "https://www.example.com/absolute/url",
            ExternalReference("external"),
        ),
        (
            base64.b64encode("blahblah".encode()).decode("utf-8"),
            Binary("binary"),
        ),
        (
            "2024-01-06T00:00:00",
            DateTime("datetime"),
        ),
        (
            SCIMDataContainer({"sub_attr_1": 1, "sub_attr_2": "2"}),
            Complex("complex", sub_attributes=[]),
        ),
    ),
)
def test_validate_correct_type(input_value, attr):
    issues = attr.validate(input_value)

    assert issues.to_dict(msg=True) == {}


def test_complex_mv_attr_fails_if_multiple_primary_items():
    attr = Complex("complex", multi_valued=True)
    expected_issues = {"_errors": [{"code": 15}]}

    issues = attr.validate(
        [
            SCIMDataContainer({"value": 1, "primary": True}),
            SCIMDataContainer({"value": "abc", "primary": True}),
        ]
    )

    assert issues.to_dict() == expected_issues


def test_warning_is_returned_if_multiple_type_value_pairs():
    attr = Complex("complex", multi_valued=True)
    expected_issues = {"_warnings": [{"code": 2}]}

    issues = attr.validate(
        [
            SCIMDataContainer({"value": 1, "type": "work"}),
            SCIMDataContainer({"value": 1, "type": "work"}),
        ]
    )

    assert issues.to_dict() == expected_issues


def test_invalid_items_dont_count_in_type_value_pairs():
    attr = Complex("complex", multi_valued=True)
    expected_issues = {"0": {"_errors": [{"code": 2}]}}

    issues = attr.validate(
        [
            2,
            SCIMDataContainer({"value": 1, "type": "work"}),
        ]
    )

    assert issues.to_dict() == expected_issues


def test_attribute_repr():
    attr = String("attr")

    assert repr(attr) == "String(attr)"


def test_string_attributes_can_be_compared():
    str_1 = String(
        name="str1",
        required=True,
        canonical_values=["a", "b", "c"],
        multi_valued=False,
        uniqueness=AttributeUniqueness.SERVER,
        case_exact=True,
    )
    str_2 = String(
        name="str1",
        required=True,
        canonical_values=["a", "b", "c"],
        multi_valued=False,
        uniqueness=AttributeUniqueness.SERVER,
        case_exact=True,
    )
    str_3 = String(
        name="str2",
        required=True,
        canonical_values=["a", "b", "c"],
        multi_valued=False,
        uniqueness=AttributeUniqueness.SERVER,
        case_exact=True,
    )

    assert str_1 == str_2
    assert str_1 != str_3
    assert str_1 != "str1"


def test_reference_attributes_can_be_compared():
    str_1 = SCIMReference(
        name="ref",
        required=True,
        multi_valued=False,
        case_exact=True,
        reference_types=["User"],
    )
    str_2 = SCIMReference(
        name="ref",
        required=True,
        multi_valued=False,
        case_exact=True,
        reference_types=["User"],
    )
    str_3 = SCIMReference(
        name="ref2",
        required=True,
        multi_valued=False,
        case_exact=True,
        reference_types=["User"],
    )

    assert str_1 == str_2
    assert str_1 != str_3
    assert str_1 != "ref"


def test_validators_are_not_run_further_if_one_of_them_forces_proceeding_to_stop():
    def validator_1(value: str) -> ValidationIssues():
        issues = ValidationIssues()
        if value != "abc":
            issues.add_error(issue=ValidationError.bad_value_syntax(), proceed=False)
        return issues

    def validator_2(value: str) -> ValidationIssues():
        issues = ValidationIssues()
        if value != "cba":
            issues.add_error(issue=ValidationError.bad_value_content(), proceed=False)
        return issues

    attr = String(name="attr", required=False, validators=[validator_1, validator_2])

    assert attr.validate("cba").to_dict() == {"_errors": [{"code": 1}]}
    assert attr.validate("abc").to_dict() == {"_errors": [{"code": 4}]}


def test_complex_sub_attributes_data_can_be_filtered():
    data = [{"value": "10", "displayName": "John Doe"}, {"value": "20", "displayName": "Karen"}]
    expected = [{"displayName": "John Doe"}, {"displayName": "Karen"}]

    actual = User.attrs.get("manager").filter(data, lambda a: a.mutability == "readOnly")

    assert actual == expected


def test_type_error_is_raised_if_accessing_sub_attr_of_non_complex_attr():
    with pytest.raises(AttributeError, match=r"attribute 'username\.formatted' does not exist"):
        print(User.attrs.username__formatted)


def test_attribute_error_is_raised_if_accessing_non_existent_sub_attr_of_complex_attr():
    with pytest.raises(AttributeError, match="attribute 'name.official' does not exist"):
        print(User.attrs.name__official)


def test_attribute_global_deserializer_can_be_registered_and_used():
    DateTime.set_deserializer(datetime.fromisoformat)
    attr = Complex(
        "complex",
        multi_valued=True,
        sub_attributes=[DateTime("timestamps", multi_valued=True)],
    )
    value = datetime.now()

    deserialized = attr.deserialize([{"timestamps": [value.isoformat()]}])

    assert isinstance(deserialized[0].get("timestamps")[0], datetime)
    assert deserialized[0].get("timestamps")[0] == value

    DateTime.set_deserializer(str)


def test_attribute_global_deserializer_is_not_used_if_attr_deserializer_defined():
    DateTime.set_deserializer(datetime.fromisoformat)
    attr = Complex(
        "complex",
        multi_valued=True,
        sub_attributes=[
            DateTime(
                "timestamps",
                multi_valued=True,
                deserializer=lambda val: sum([hash(item) for item in val]),
            )
        ],
    )

    deserialized = attr.deserialize([{"timestamps": [datetime.now().isoformat()]}])

    assert isinstance(deserialized[0].get("timestamps"), int)

    DateTime.set_deserializer(str)


def test_attribute_global_serializer_can_be_registered_and_used():
    Integer.set_serializer(str)
    attr = Complex(
        "complex",
        multi_valued=True,
        sub_attributes=[Integer("values", multi_valued=True)],
    )

    deserialized = attr.serialize([{"values": [1, 2, 3]}])

    assert deserialized[0]["values"] == ["1", "2", "3"]

    Integer.set_serializer(int)


def test_attribute_global_serializer_is_not_used_if_attr_serializer_changed_type():
    Integer.set_serializer(str)
    attr = Complex(
        "complex",
        multi_valued=True,
        sub_attributes=[
            Integer(
                "values",
                multi_valued=True,
                serializer=lambda val: "".join(str(item) for item in val),
            )
        ],
    )

    deserialized = attr.serialize([{"values": [1, 2, 3]}])

    assert deserialized[0]["values"] == "123"

    Integer.set_serializer(int)


@pytest.mark.parametrize(
    ("input_", "expected"),
    (
        (
            "id",
            BoundedAttrRep(
                schema="urn:ietf:params:scim:schemas:core:2.0:User",
                attr="id",
            ),
        ),
        (
            "name__formatted",
            BoundedAttrRep(
                schema="urn:ietf:params:scim:schemas:core:2.0:User",
                attr="name",
                sub_attr="formatted",
            ),
        ),
        (
            "emails__type",
            BoundedAttrRep(
                schema="urn:ietf:params:scim:schemas:core:2.0:User",
                attr="emails",
                sub_attr="type",
            ),
        ),
        (
            "manager",
            BoundedAttrRep(
                schema="urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
                attr="manager",
            ),
        ),
        (
            "manager__displayName",
            BoundedAttrRep(
                schema="urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
                attr="manager",
                sub_attr="displayName",
            ),
        ),
    ),
)
def test_attr_rep_can_be_retrieved_from_bounded_attr_reps(input_, expected):
    assert getattr(User.attrs, input_, None) == expected


@pytest.mark.parametrize(
    "input_",
    (
        "id",
        "urn:ietf:params:scim:schemas:core:2.0:User:id",
        "name",
        "urn:ietf:params:scim:schemas:core:2.0:User:name",
        "name.formatted",
        "urn:ietf:params:scim:schemas:core:2.0:User:name.formatted",
        "emails",
        "urn:ietf:params:scim:schemas:core:2.0:User:emails",
        "emails.type",
        "urn:ietf:params:scim:schemas:core:2.0:User:emails.type",
        "manager",
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:manager",
        "manager.displayName",
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:manager.displayName",
    ),
)
def test_attr_can_be_retrieved_from_bounded_attr_reps(input_):
    assert User.attrs.get(input_) is not None


@pytest.mark.parametrize(
    "input_",
    (
        "non_existing",
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:id",
        "userName.nonExisting",
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:nonExisting",
        "urn:ietf:params:scim:schemas:core:2.0:User:manager",
    ),
)
def test_attr_is_not_retrieved_if_bad_input(input_):
    assert User.attrs.get(input_) is None


def test_attr_rep_is_hashable():
    assert hash(AttrRep(attr="attr", sub_attr="sub_attr")) is not None


def test_bounded_attr_rep_is_hashable():
    assert (
        hash(
            BoundedAttrRep(
                schema="urn:ietf:params:scim:schemas:core:2.0:User",
                attr="name",
                sub_attr="formatted",
            )
        )
        is not None
    )
