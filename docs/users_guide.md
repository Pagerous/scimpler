from scimpler.data import ResourceSchema`scimpler` provides functionalities that can be used both on Service Provider
and Provisioning client sides. It is agnostic to any existing web frameworks,
so it probably will not work out of the box in your case. However, most of the hard work has already been
done for you. **SCIM 2.0** protocol exactly specifies how the entities may, should, and
must behave (depending on the case). `scimpler` maps all _possible_ requirements and makes them
ready to use.

`scimpler`, among many features, enables SCIM schema definition and _stateless_ validation. This means
that any requirement specified by the protocol that requires _state_ is not checked by the library.

Check below topics to learn more about `scimpler`.

[Schema definition](users_guide.md#schema-definition)<br>
[Data validation](users_guide.md#data-validation)


## Schema definition

`scimpler` provides all schemas specified by the standard, and some of them can be adjusted for a
particular needs.

**Resource schemas and extensions**

- urn:ietf:params:scim:schemas:core:2.0:User
- urn:ietf:params:scim:schemas:extension:Enterprise:2.0:User
- urn:ietf:params:scim:schemas:core:2.0:Group
- urn:ietf:params:scim:schemas:core:2.0:ResourceType
- urn:ietf:params:scim:schemas:core:2.0:Schema
- urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig

**API message schemas**

- urn:ietf:params:scim:api:messages:2.0:Error
- urn:ietf:params:scim:api:messages:2.0:ListResponse
- urn:ietf:params:scim:api:messages:2.0:SearchRequest
- urn:ietf:params:scim:api:messages:2.0:PatchOp
- urn:ietf:params:scim:api:messages:2.0:BulkRequest
- urn:ietf:params:scim:api:messages:2.0:BulkResponse

Schemas are stateless and thread-safe. All pre-defined schemas can be imported from
`scimpler.schemas`. Every of them contains all attributes specified by the protocol. Since
some of the attributes are not required, and may not be supported by Service Provider, they can
be excluded from the schema, so for example, they do not appear in the schema representation.

```python
from scimpler.schemas import UserSchema, EnterpriseUserSchemaExtension
from scimpler.data import AttrFilter

user_schema = UserSchema(
    AttrFilter(
        attr_reps=["name.formatted", "x509Certificates"],
        include=False,
    )
)
enterprise_extension = EnterpriseUserSchemaExtension(
    AttrFilter(
        attr_reps=["manager"],
        include=True,
    )
)
user_schema.extend(enterprise_extension, required=True)
```

!!! info
    
    Required attributes and sub-attributes (like `id` or `schemas` in resources) are included regardless the filter.

To define custom schema or schema extension, one must inherit from `scimpler.data.ResourceSchema`
or `scimpler.data.SchemaExtension`, respectively.

```python
from scimpler.data import String, Integer, ResourceSchema, SchemaExtension


class VehicleSchema(ResourceSchema):
    schema = "my:schema:uri:1.0:Vehicle"
    name = "Vehicle"
    plural_name = "Vehicles"
    endpoint = "/Vehicles"
    base_attrs = [
        String("model", required=True, case_exact=True),
        Integer("capacity", required=True),
    ]


class VehicleExtension(SchemaExtension):
    schema = "my:extension:schema:uri:1.0:VehicleExtension"
    name = "VehicleExtension"
    base_attrs = [Integer("wheels")]


vehicle_schema = VehicleSchema()
vehicle_extension = VehicleExtension()
vehicle_schema.extend(vehicle_extension)
```

`User` and `Group` resource schemas can differ more than just attribute selection in your case.
You can ignore included resource schema definitions and redefine them on your own, e.g. to make
some attribute required, even if it is optional as per RFC-7643.

```python
from scimpler.data import Attribute, ResourceSchema

class UserSchema(ResourceSchema):
    schema = "urn:ietf:params:scim:schemas:core:2.0:User"
    name = "User"
    plural_name = "Users"
    description = "User Account"
    endpoint = "/Users"
    base_attrs: list[Attribute] = [...]
```

!!! warning
    Redefining built-in resource schema removes all validations, pre-, and post-processing, 
    associated with the resource type.

!!! info
    All provided validators for `User` attributes can be imported from `scimpler.schemas.user`.


Every schema provides three main functionalities: data **validation**, **deserialization**, and **serialization**.


## Data validation

All built-in schemas incorporate validation rules described in [RFC-7643](https://www.rfc-editor.org/rfc/rfc7643).
Check [SCIM compliance](compliance.md) for details.

Below example presents schema-level data validation.

```python
from scimpler.schemas import UserSchema

user = UserSchema()
data = {
    "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
    "username": "Pagerous",
    "id": 42,
}

issues = user.validate(data)
```

`validate` returns `scimpler.error.ValidationIssues` always. It contains validation
errors and validation warnings. Call `ValidationIssues.to_dict`, to have nice overview of the issues.

```python
>>> print(issues.to_dict())
{"id": {"_errors": [{"code": 2}]}}
```


Every validation error and warning has [code](issue-codes.md). To see a message, pass `message` argument.

```python
>>> print(issues.to_dict(message=True))
{"id": {"_errors": [{"code": 2, "message": "bad type, expecting 'string'"}]}}
```

It is also possible to validate data for every API message schema.

```python
from scimpler.schemas import ListResponseSchema, UserSchema, GroupSchema

list_response = ListResponseSchema(
    resource_schemas=[UserSchema(), GroupSchema()]
)
data = {
    "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
    "totalResults": 2,
    "startIndex": 1,
    "itemsPerPage": 2,
    "Resources": [
        {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "username": "Pagerous",
            "id": 42,
        },
        {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"],
            "displayName": "scimplerUsers",
            "members": [
                {
                    "value": 42,
                    "type": "GitHubUser",
                }
            ]
        }
    ],
}

issues = list_response.validate(data)
```

```python
>>> print(issues.to_dict(message=True))
{
  "Resources": {
    "0": {
      "id": {
        "_errors": [
          {
            "code": 2,
            "message": "bad type, expecting 'string'"
          }
        ]
      }
    },
    "1": {
      "id": {
        "_errors": [
          {
            "code": 5,
            "message": 'missing'
          }
        ]
      },
      "members": {
        "0": {
          "value": {
            "_errors": [
              {
                "code": 2,
                "message": "bad type, expecting 'string'"
              }
            ]
          },
          "type": {
            "_errors": [
              {
                "code": 9,
                "message": "must be one of: ['user', 'group']"
              }
            ]
          }
        }
      }
    }
  }
}
```

!!! info
    By default, schema-level validation is performed out of SCIM request / response context, and some
    rules are not checked. To enable request-specific or response-specific validation, pass
    **presence_config** parameter to `validate` method.

    ```python
    from scimpler.data import AttrValuePresenceConfig
    from scimpler.schemas import UserSchema
    

    user = UserSchema()
    data = {...}
    issues = user.validate(data, presence_config=AttrValuePresenceConfig("RESPONSE"))
    ```

## Data deserialization and serialization

## Working with data

## Filtering

## Sorting

## Request and response validation

## Integrations
### marshmallow