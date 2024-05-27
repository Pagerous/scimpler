import pytest

from src.assets.schemas.user import User
from src.container import AttrRep, BoundedAttrRep, SCIMDataContainer
from src.data.attributes import Boolean, Complex, Integer, String
from src.data.attributes_presence import AttributePresenceValidator
from src.data.schemas import ResourceSchema, SchemaExtension


def test_presence_validator_fails_if_returned_attribute_that_never_should_be_returned(
    user_data_server,
):
    validator = AttributePresenceValidator()
    user_data_server["password"] = "1234"
    expected = {
        "password": {
            "_errors": [
                {
                    "code": 7,
                }
            ]
        }
    }

    issues = validator(SCIMDataContainer(user_data_server), User, "RESPONSE")

    assert issues.to_dict() == expected


def test_restricted_attributes_can_be_sent_with_request(user_data_client):
    validator = AttributePresenceValidator()
    user_data_client["password"] = "1234"

    issues = validator(SCIMDataContainer(user_data_client), User, "REQUEST")

    assert issues.to_dict(msg=True) == {}


def test_presence_validator_fails_on_attr_not_requested_by_exclusion():
    validator = AttributePresenceValidator([BoundedAttrRep(attr="name")], include=False)
    data = SCIMDataContainer(
        {
            "id": "1",
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "userName": "Pagerous",
            "name": {"givenName": "Arkadiusz", "familyName": "Pajor"},
        }
    )

    expected = {"name": {"_errors": [{"code": 7}]}}

    issues = validator(data, User, "RESPONSE")

    assert issues.to_dict() == expected


def test_presence_validator_fails_on_attr_not_requested_by_inclusion():
    validator = AttributePresenceValidator([BoundedAttrRep(attr="name")], include=True)
    data = SCIMDataContainer(
        {
            "id": "1",
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "name": {"givenName": "Arkadiusz", "familyName": "Pajor"},
            "meta": {
                "resourceType": "User",
                "created": "2011-05-13T04:42:34Z",
                "lastModified": "2011-05-13T04:42:34Z",
                "location": "https://example.com/v2/Users/2819c223-7f76-453a-919d-413861904646",
                "version": r"W\/\"f250dd84f0671c3\"",
            },
        }
    )
    expected = {
        "meta": {
            "_errors": [{"code": 7}],
            "resourceType": {"_errors": [{"code": 7}]},
            "created": {"_errors": [{"code": 7}]},
            "lastModified": {"_errors": [{"code": 7}]},
            "location": {"_errors": [{"code": 7}]},
            "version": {"_errors": [{"code": 7}]},
        }
    }

    issues = validator(data, User, "RESPONSE")

    assert issues.to_dict() == expected


def test_presence_validator_fails_on_sub_attr_not_requested_by_exclusion():
    validator = AttributePresenceValidator(
        [BoundedAttrRep(attr="name", sub_attr="familyName")], include=False
    )
    data = SCIMDataContainer(
        {
            "id": "1",
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "userName": "Pagerous",
            "name": {"givenName": "Arkadiusz", "familyName": "Pajor"},
        }
    )

    expected = {
        "name": {
            "familyName": {
                "_errors": [
                    {
                        "code": 7,
                    }
                ]
            }
        }
    }

    issues = validator(data, User, "RESPONSE")

    assert issues.to_dict() == expected


def test_presence_validator_fails_on_sub_attr_not_requested_by_inclusion():
    validator = AttributePresenceValidator(
        [BoundedAttrRep(attr="name", sub_attr="familyName")], include=True
    )
    data = SCIMDataContainer(
        {
            "id": "1",
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "name": {"familyName": "Pajor", "givenName": "Arkadiusz"},
        }
    )

    expected = {
        "name": {
            "givenName": {
                "_errors": [
                    {
                        "code": 7,
                    }
                ]
            }
        }
    }

    issues = validator(data, User, "RESPONSE")

    assert issues.to_dict() == expected


def test_presence_validator_fails_if_not_provided_attribute_that_always_should_be_returned():
    validator = AttributePresenceValidator()

    expected = {
        "id": {
            "_errors": [
                {
                    "code": 5,
                }
            ]
        },
        "schemas": {
            "_errors": [
                {
                    "code": 5,
                }
            ]
        },
        "userName": {
            "_errors": [
                {
                    "code": 5,
                }
            ]
        },
    }

    issues = validator(SCIMDataContainer(), User, "RESPONSE")

    assert issues.to_dict() == expected


def test_presence_validator_fails_if_not_provided_requested_required_attribute():
    validator = AttributePresenceValidator([BoundedAttrRep(attr="username")], include=True)
    data = SCIMDataContainer(
        {
            "id": "1",
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        }
    )
    expected = {
        "userName": {
            "_errors": [
                {
                    "code": 5,
                }
            ]
        },
    }

    issues = validator(data, User, "RESPONSE")

    assert issues.to_dict() == expected


def test_presence_validator_passes_if_not_provided_requested_optional_attribute():
    validator = AttributePresenceValidator(
        [BoundedAttrRep(attr="name", sub_attr="familyname")], include=True
    )
    data = SCIMDataContainer(
        {
            "id": "1",
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        }
    )

    issues = validator(data, User, "RESPONSE")

    assert issues.to_dict(msg=True) == {}


def test_presence_validator_fails_on_multivalued_complex_attr_not_requested_by_exclusion():
    validator = AttributePresenceValidator(
        [BoundedAttrRep(attr="emails", sub_attr="display")], include=False
    )
    data = SCIMDataContainer(
        {
            "id": "1",
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "userName": "Pagerous",
            "emails": [
                {"type": "work", "primary": True, "display": "example@example.com"},
                {"type": "home", "primary": False},
                {"type": "school", "primary": False, "display": "example@example.com"},
            ],
        }
    )

    expected = {
        "emails": {
            "0": {"display": {"_errors": [{"code": 7}]}},
            "2": {"display": {"_errors": [{"code": 7}]}},
        }
    }

    issues = validator(data, User, "RESPONSE")

    assert issues.to_dict() == expected


def test_presence_validator_fails_on_multivalued_complex_attr_not_requested_by_inclusion():
    validator = AttributePresenceValidator(
        [BoundedAttrRep(attr="emails", sub_attr="display")], include=True
    )
    data = SCIMDataContainer(
        {
            "id": "1",
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "emails": [
                {"type": "work", "primary": True, "display": "example@example.com"},
                {"display": "example@example.com"},
                {"type": "school", "primary": False, "display": "example@example.com"},
            ],
        }
    )

    expected = {
        "emails": {
            "0": {"type": {"_errors": [{"code": 7}]}, "primary": {"_errors": [{"code": 7}]}},
            "2": {"type": {"_errors": [{"code": 7}]}, "primary": {"_errors": [{"code": 7}]}},
        }
    }

    issues = validator(data, User, "RESPONSE")

    assert issues.to_dict() == expected


def test_specifying_attribute_issued_by_service_provider_causes_validation_failure(
    user_data_client,
):
    validator = AttributePresenceValidator()
    user_data_client["id"] = "should-not-be-provided"
    expected_issues = {"id": {"_errors": [{"code": 6}]}}

    issues = validator(SCIMDataContainer(user_data_client), User, "REQUEST")

    assert issues.to_dict() == expected_issues


def test_presence_validation_fails_if_missing_required_field_from_required_extension():
    schema = ResourceSchema(schema="my:schema", name="MyResource")
    extension = SchemaExtension(
        schema="my:schema:extension", name="MyExtension", attrs=[Integer("age", required=True)]
    )
    schema.extend(extension, required=True)
    validator = AttributePresenceValidator()
    expected_issues = {"age": {"_errors": [{"code": 5}]}}

    issues = validator(SCIMDataContainer({"id": "1", "schemas": ["my:schema"]}), schema, "RESPONSE")

    assert issues.to_dict() == expected_issues


def test_presence_validation_succeeds_if_missing_required_field_from_non_required_extension():
    schema = ResourceSchema(schema="my:schema", name="MyResource")
    extension = SchemaExtension(
        schema="my:schema:extension", name="MyExtension", attrs=[Integer("age", required=True)]
    )
    schema.extend(extension, required=False)
    validator = AttributePresenceValidator()

    issues = validator(SCIMDataContainer({"id": "1", "schemas": ["my:schema"]}), schema, "RESPONSE")

    assert issues.to_dict(msg=True) == {}


def test_creating_presence_validator_with_attr_reps_and_no_inclusiveness_specified_fails():
    with pytest.raises(ValueError, match="'include' must be specified if 'attr_reps' is specified"):
        AttributePresenceValidator(attr_reps=[AttrRep(attr="attr")])


def test_presence_check_fails_if_passed_schema_where_complex_is_required():
    validator = AttributePresenceValidator(attr_reps=[AttrRep(attr="formatted")], include=True)

    with pytest.raises(
        TypeError,
        match="provided schema, but complex attribute is required for non-bounded attributes",
    ):
        validator({"name": {"formatted": "John Doe"}}, User, "RESPONSE")


def test_presence_check_fails_if_passed_complex_where_schema_is_required():
    validator = AttributePresenceValidator(attr_reps=[BoundedAttrRep(attr="name")], include=True)

    with pytest.raises(
        TypeError, match="provided complex attribute, but schema is required for bounded attributes"
    ):
        validator({"formatted": "John Doe"}, User.attrs.name, "RESPONSE")


def test_sub_attributes_presence_is_validated_if_multivalued_root_attribute_has_value_none():
    my_resource = ResourceSchema(
        schema="my:schema",
        name="MyResource",
        attrs=[
            Complex(
                name="super_complex",
                multi_valued=True,
                sub_attributes=[
                    String("str_required", required=True),
                    Integer("int_required", required=True),
                    Boolean("bool_required", required=True),
                ],
            )
        ],
    )
    validator = AttributePresenceValidator(
        attr_reps=[
            BoundedAttrRep(attr="super_complex", sub_attr="str_required"),
            BoundedAttrRep(attr="super_complex", sub_attr="int_required"),
            BoundedAttrRep(attr="super_complex", sub_attr="bool_required"),
        ],
        include=True,
    )
    data = SCIMDataContainer(
        {
            "schemas": ["my:schema"],
            "super_complex": None,
        }
    )
    expected_issues = {
        "super_complex": {
            "str_required": {"_errors": [{"code": 5}]},
            "int_required": {"_errors": [{"code": 5}]},
            "bool_required": {"_errors": [{"code": 5}]},
        }
    }

    issues = validator(data, my_resource, "REQUEST")

    assert issues.to_dict() == expected_issues


def test_attr_presence_can_be_checked_for_complex_attribute():
    attr = Complex(
        name="super_complex",
        multi_valued=True,
        sub_attributes=[
            String("str"),
            Integer("int"),
            Boolean("bool"),
        ],
    )
    validator = AttributePresenceValidator(
        attr_reps=[AttrRep(attr="str"), AttrRep(attr="bool")],
        include=False,
    )
    data = SCIMDataContainer({"str": "abc", "int": 1, "bool": True})
    expected_issues = {
        "str": {"_errors": [{"code": 7}]},
        "bool": {"_errors": [{"code": 7}]},
    }

    issues = validator(data, attr, "RESPONSE")

    assert issues.to_dict() == expected_issues
