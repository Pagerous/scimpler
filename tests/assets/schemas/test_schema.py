from src.assets.schemas.schema import attributes
from src.data.container import SCIMDataContainer


def test_validation_attributes_field_fails_for_bad_sub_attributes():
    expected_issues = {
        "0": {
            "subAttributes": {
                "0": {"type": {"_errors": [{"code": 14}]}, "caseExact": {"_errors": [{"code": 2}]}}
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


def test_case_exact_is_removed_from_non_string_attrs_while_dumping_attributes():
    dumped = attributes.dump(
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

    assert "caseExact" not in dumped[0].to_dict()


def test_sub_attributes_are_removed_from_non_complex_attrs_while_dumping_attributes():
    dumped = attributes.dump(
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

    assert "subAttributes" not in dumped[0].to_dict()
