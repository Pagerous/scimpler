

def test_body_is_ignored(validator):
    errors = validator.validate_request(http_method="GET", body={"schemas": 123, "userName": 123})

    assert errors == []
