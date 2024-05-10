from src.assets.schemas import User


def test_bad_preferred_langauge_is_validated(user_data_client):
    user_data_client["preferredLanguage"] = "wrong-lang"
    expected_issues = {"preferredLanguage": {"_errors": [{"code": 1}]}}

    issues = User.validate(user_data_client)

    assert issues.to_dict() == expected_issues


def test_correct_preferred_langauge_is_validated(user_data_client):
    user_data_client["preferredLanguage"] = "en-US"

    issues = User.validate(user_data_client)

    assert issues.to_dict(msg=True) == {}


def test_bad_locale_is_validated(user_data_client):
    user_data_client["locale"] = "pl-OT-ka"
    expected_issues = {"locale": {"_errors": [{"code": 1}]}}

    issues = User.validate(user_data_client)

    assert issues.to_dict() == expected_issues


def test_correct_locale_is_validated(user_data_client):
    user_data_client["locale"] = "en-US"

    issues = User.validate(user_data_client)

    assert issues.to_dict(msg=True) == {}


def test_bad_timezone_is_validated(user_data_client):
    user_data_client["timezone"] = "non/Existing"
    expected_issues = {"timezone": {"_errors": [{"code": 4}]}}

    issues = User.validate(user_data_client)

    assert issues.to_dict() == expected_issues


def test_correct_timezone_is_validated(user_data_client):
    user_data_client["timezone"] = "Europe/Warsaw"

    issues = User.validate(user_data_client)

    assert issues.to_dict(msg=True) == {}


def test_bad_email_is_validated(user_data_client):
    user_data_client["emails"][0]["value"] = "bad-email"
    expected_issues = {"emails": {"0": {"value": {"_errors": [{"code": 1}]}}}}

    issues = User.validate(user_data_client)

    assert issues.to_dict() == expected_issues


def test_correct_email_is_validated(user_data_client):
    user_data_client["emails"][0]["value"] = "correct@email.com"

    issues = User.validate(user_data_client)

    assert issues.to_dict(msg=True) == {}


def test_bad_phone_number_is_validated(user_data_client):
    user_data_client["phoneNumbers"][0]["value"] = "bad-email"
    expected_issues = {"phoneNumbers": {"0": {"value": {"_warnings": [{"code": 3}]}}}}

    issues = User.validate(user_data_client)

    assert issues.to_dict() == expected_issues


def test_correct_phone_number_is_validated(user_data_client):
    user_data_client["phoneNumbers"][0]["value"] = "+48666999666"

    issues = User.validate(user_data_client)

    assert issues.to_dict(msg=True) == {}


def test_bad_country_is_validated(user_data_client):
    user_data_client["addresses"][0]["country"] = "bad-country"
    expected_issues = {"addresses": {"0": {"country": {"_errors": [{"code": 4}]}}}}

    issues = User.validate(user_data_client)

    assert issues.to_dict() == expected_issues


def test_correct_country_is_validated(user_data_client):
    user_data_client["addresses"][0]["country"] = "PL"

    issues = User.validate(user_data_client)

    assert issues.to_dict(msg=True) == {}


def test_country_is_not_validated_if_not_specified_validated(user_data_client):
    user_data_client["addresses"][0].pop("country")

    issues = User.validate(user_data_client)

    assert issues.to_dict(msg=True) == {}


def test_warning_is_raised_if_nickname_equals_username(user_data_client):
    user_data_client["nickName"] = user_data_client["userName"]
    expected_issues = {"nickName": {"_warnings": [{"code": 5}]}}

    issues = User.validate(user_data_client)

    assert issues.to_dict() == expected_issues


def test_ims_value_is_canonicalized(user_data_client):
    user_data_client["ims"][0]["value"] = "Gadu Gadu"

    data = User.deserialize(user_data_client)

    assert data.get("ims")[0].get("value") == "gadugadu"
