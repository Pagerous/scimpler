from src.assets.schemas import User
from src.assets.schemas.schema import Schema, attributes
from src.container import SCIMDataContainer


def test_validation_attributes_field_fails_for_bad_sub_attributes():
    expected_issues = {
        "0": {
            "subAttributes": {
                "0": {"caseExact": {"_errors": [{"code": 2}]}, "type": {"_warnings": [{"code": 1}]}}
            }
        }
    }

    issues = attributes.validate(
        value=[
            SCIMDataContainer(
                {
                    "name": "emails",
                    "type": "complex",
                    "multiValued": True,
                    "required": False,
                    "subAttributes": [
                        {
                            "name": "value",
                            "type": "unknown",
                            "multiValued": False,
                            "required": False,
                            "caseExact": 123,
                            "mutability": "readWrite",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                        {
                            "name": "display",
                            "type": "string",
                            "multiValued": False,
                            "required": False,
                            "caseExact": False,
                            "mutability": "readWrite",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                        {
                            "name": "type",
                            "type": "string",
                            "multiValued": False,
                            "required": False,
                            "caseExact": False,
                            "canonicalValues": ["work", "home", "other"],
                            "mutability": "readWrite",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                        {
                            "name": "primary",
                            "type": "boolean",
                            "multiValued": False,
                            "required": False,
                            "mutability": "readWrite",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                    ],
                }
            )
        ]
    )

    assert issues.to_dict() == expected_issues


def test_case_exact_is_removed_from_non_string_attrs_while_serializing_attributes():
    serialized = attributes.serialize(
        value=[
            SCIMDataContainer(
                {
                    "name": "value",
                    "type": "integer",
                    "multiValued": True,
                    "caseExact": True,
                    "required": False,
                }
            )
        ]
    )

    assert "caseExact" not in serialized[0]


def test_sub_attributes_are_removed_from_non_complex_attrs_while_serializing_attributes():
    serialized = attributes.serialize(
        value=[
            SCIMDataContainer(
                {
                    "name": "value",
                    "type": "integer",
                    "multiValued": True,
                    "subAttributes": [],
                    "required": False,
                }
            )
        ]
    )

    assert "subAttributes" not in serialized[0]


def test_warning_is_returned_if_missing_sub_attrs_for_complex_attr():
    expected_issues = {"0": {"subAttributes": {"_warnings": [{"code": 4}]}}}

    issues = attributes.validate(
        value=[
            SCIMDataContainer(
                {
                    "name": "value",
                    "type": "complex",
                }
            )
        ]
    )

    assert issues.to_dict() == expected_issues


def test_validation_fails_if_missing_case_exact_for_string_attr():
    expected_issues = {"0": {"caseExact": {"_errors": [{"code": 5}]}}}

    issues = attributes.validate(
        value=[
            SCIMDataContainer(
                {
                    "name": "value",
                    "type": "string",
                }
            )
        ]
    )

    assert issues.to_dict() == expected_issues


def test_resource_schema_representation_can_be_generated():
    output = Schema.get_repr(User)

    for attr in output["attributes"]:
        assert attr["name"] not in ["id", "meta", "externalId"]


def test_schema_extension_representation_can_be_generated():
    output = Schema.get_repr(User.get_extension("EnterpriseUser"))

    assert output


def test_schema_data_can_be_serialized():
    data = Schema.get_repr(User)

    serialized = Schema.serialize(data)

    assert serialized == data
