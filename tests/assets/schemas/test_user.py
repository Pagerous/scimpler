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
