from scimpler.data.attr_value_presence import AttrValuePresenceConfig


def test_bad_preferred_langauge_is_validated(user_data_client, user_schema):
    user_data_client["preferredLanguage"] = "wrong-lang"
    expected_issues = {"preferredLanguage": {"_errors": [{"code": 1}]}}

    issues = user_schema.validate(user_data_client, AttrValuePresenceConfig("REQUEST"))

    assert issues.to_dict() == expected_issues


def test_bulk_id_existence_in_id_is_validated(user_data_client, user_schema):
    user_data_client["id"] = "something-bulkId-whatever"
    expected_issues = {"id": {"_errors": [{"code": 4}]}}

    issues = user_schema.validate(user_data_client, AttrValuePresenceConfig("REQUEST"))

    assert issues.to_dict() == expected_issues


def test_correct_preferred_langauge_is_validated(user_data_client, user_schema):
    user_data_client["preferredLanguage"] = "en-US"

    issues = user_schema.validate(user_data_client, AttrValuePresenceConfig("REQUEST"))

    assert issues.to_dict(msg=True) == {}


def test_bad_locale_is_validated(user_data_client, user_schema):
    user_data_client["locale"] = "pl-OT-ka"
    expected_issues = {"locale": {"_errors": [{"code": 1}]}}

    issues = user_schema.validate(user_data_client, AttrValuePresenceConfig("REQUEST"))

    assert issues.to_dict() == expected_issues


def test_correct_locale_is_validated(user_data_client, user_schema):
    user_data_client["locale"] = "en-US"

    issues = user_schema.validate(user_data_client, AttrValuePresenceConfig("REQUEST"))

    assert issues.to_dict(msg=True) == {}


def test_bad_timezone_is_validated(user_data_client, user_schema):
    user_data_client["timezone"] = "non/Existing"
    expected_issues = {"timezone": {"_errors": [{"code": 4}]}}

    issues = user_schema.validate(user_data_client, AttrValuePresenceConfig("REQUEST"))

    assert issues.to_dict() == expected_issues


def test_correct_timezone_is_validated(user_data_client, user_schema):
    user_data_client["timezone"] = "Europe/Warsaw"

    issues = user_schema.validate(user_data_client, AttrValuePresenceConfig("REQUEST"))

    assert issues.to_dict(msg=True) == {}


def test_bad_email_is_validated(user_data_client, user_schema):
    user_data_client["emails"][0]["value"] = "bad-email"
    expected_issues = {"emails": {"0": {"value": {"_errors": [{"code": 1}]}}}}

    issues = user_schema.validate(user_data_client, AttrValuePresenceConfig("REQUEST"))

    assert issues.to_dict() == expected_issues


def test_correct_email_is_validated(user_data_client, user_schema):
    user_data_client["emails"][0]["value"] = "correct@email.com"

    issues = user_schema.validate(user_data_client, AttrValuePresenceConfig("REQUEST"))

    assert issues.to_dict(msg=True) == {}


def test_bad_phone_number_is_validated(user_data_client, user_schema):
    user_data_client["phoneNumbers"][0]["value"] = "bad-phone-number"
    expected_issues = {
        "phoneNumbers": {
            "0": {
                "value": {
                    "_warnings": [{"code": 3, "context": {"reason": "not a valid phone number"}}]
                }
            }
        }
    }

    issues = user_schema.validate(user_data_client, AttrValuePresenceConfig("REQUEST"))

    assert issues.to_dict(ctx=True) == expected_issues


def test_correct_phone_number_is_validated(user_data_client, user_schema):
    user_data_client["phoneNumbers"][0]["value"] = "+48666999666"

    issues = user_schema.validate(user_data_client, AttrValuePresenceConfig("REQUEST"))

    assert issues.to_dict(msg=True) == {}


def test_bad_country_is_validated(user_data_client, user_schema):
    user_data_client["addresses"][0]["country"] = "bad-country"
    expected_issues = {"addresses": {"0": {"country": {"_errors": [{"code": 4}]}}}}

    issues = user_schema.validate(user_data_client, AttrValuePresenceConfig("REQUEST"))

    assert issues.to_dict() == expected_issues


def test_correct_country_is_validated(user_data_client, user_schema):
    user_data_client["addresses"][0]["country"] = "PL"

    issues = user_schema.validate(user_data_client, AttrValuePresenceConfig("REQUEST"))

    assert issues.to_dict(msg=True) == {}


def test_country_is_not_validated_if_not_specified_validated(user_data_client, user_schema):
    user_data_client["addresses"][0].pop("country")

    issues = user_schema.validate(user_data_client, AttrValuePresenceConfig("REQUEST"))

    assert issues.to_dict(msg=True) == {}


def test_ims_value_is_canonicalized(user_data_client, user_schema):
    user_data_client["ims"][0]["value"] = "Gadu Gadu"

    data = user_schema.deserialize(user_data_client)

    assert data.get("ims")[0].get("value") == "gadugadu"


def test_resource_schema_constant_attrs_can_be_attached_to_provided_data_with_extension(
    user_schema,
):
    data = {"urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {"employeeNumber": "42"}}
    expected = {
        "schemas": [
            "urn:ietf:params:scim:schemas:core:2.0:User",
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
        ],
        "meta": {
            "resourceType": "User",
        },
        **data,
    }

    user_schema.include_schema_data(data)

    assert data == expected


def test_resource_schema_constant_attrs_can_be_attached_to_provided_data_without_extension(
    user_schema,
):
    data = {"meta": {}}
    expected = {
        "schemas": [
            "urn:ietf:params:scim:schemas:core:2.0:User",
        ],
        "meta": {
            "resourceType": "User",
        },
    }

    user_schema.include_schema_data(data)

    assert data == expected
