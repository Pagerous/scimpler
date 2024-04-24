from src.assets.schemas import User
from src.assets.schemas.schema import Schema, attributes
from src.data.container import SCIMDataContainer


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

    assert "caseExact" not in serialized[0].to_dict()


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

    assert "subAttributes" not in serialized[0].to_dict()


def test_resource_schema_representation_can_be_generated():
    output = Schema.get_repr(User)

    for attr in output["attributes"]:
        assert attr["name"] not in ["id", "meta", "externalId"]


def test_schema_extension_representation_can_be_generated():
    output = Schema.get_repr(User.get_extension("EnterpriseUser"))

    assert output
