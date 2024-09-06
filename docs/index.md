# scimpler: makes SCIM integrations simpler


The `scimpler` library makes it easier to ensure both Service Provider and Provisioning Client ends
integrate with **SCIM 2.0** protocol flawlessly. It implements definitions, validation rules, and
operations, as defined in [RFC-7643](https://www.rfc-editor.org/rfc/rfc7643) 
and [RFC-7644](https://www.rfc-editor.org/rfc/rfc7644).

# Features
- All schemas defined in SCIM protocol ready to use
- Custom resource schemas and extensions
- Extending built-in resource schemas
- SCIM requests and responses validation
- Filter deserialization and filtering
- Support for data sorting and pagination
- Stateless data validation
- Optional integration with [marshmallow](https://marshmallow.readthedocs.io/en/stable/) schemas

# Installation

Use **pip** to install `scimpler`.

```
pip install scimpler
```

If you want to integrate with marshmallow, install `scimpler` with optional dependencies.

```
pip install "scimpler[marshmallow]"
```

# Examples
## User resource POST request validation

```python
from scimpler.schemas import UserSchema
from scimpler.validator import ResourcesPost

validator = ResourcesPost(resource_schema=UserSchema())

validation_issues = validator.validate_request(
    body={
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        "name": "Foo",
    }
).to_dict(msg=True)

print(validation_issues)
```

Output
```json
{
  "body": {
    "userName": {"_errors": [{"code": 5, "error": "missing"}]},
    "name": {"_errors": [{"code": 2, "error": "bad type, expecting 'complex'"}]}
  }
}
```

## Filter deserialization

```python
from scimpler.data import Filter

filter_ = Filter.deserialize(
    "emails[type eq 'work' and value co '@example.com'] "
    "or ims[type eq 'xmpp' and value co '@foo.com']"
).to_dict()
```

Output

```json
{
    "op": "or",
    "sub_ops": [
        {
            "attr": "emails",
            "op": "complex",
            "sub_op": {
                "op": "and",
                "sub_ops": [
                    {
                        "attr": "type",
                        "op": "eq",
                        "value": "work"
                    },
                    {
                        "attr": "value",
                        "op": "co",
                        "value": "@example.com"
                    }
                ]
            }
        },
        {
            "attr": "ims",
            "op": "complex",
            "sub_op": {
                "op": "and",
                "sub_ops": [
                    {
                        "attr": "type",
                        "op": "eq",
                        "value": "xmpp"
                    },
                    {
                        "attr": "value",
                        "op": "co",
                        "value": "@foo.com"
                    }
                ]
            }
        }
    ]
}
```

See [User's Guide](users_guide.md) for detailed features description. Want to know more? Check API Reference. 