from scimpler.data import ScimDatafrom scimpler.data import ResourceSchema`scimpler` provides functionalities that can be used both on Service Provider
and Provisioning client sides. It is agnostic to any existing web frameworks,
so it probably will not work out of the box in your case. However, most of the hard work has already been
done for you. **SCIM 2.0** protocol exactly specifies how the entities may, should, and
must behave (depending on the case). `scimpler` maps all _possible_ requirements and makes them
ready to use.

`scimpler`, among many features, enables SCIM schema definition and _stateless_ validation. This means
that any requirement specified by the protocol that requires _state_ is not checked by the library.

Check below topics to learn more about `scimpler`.

[Schema definition](users_guide.md#schema-definition)<br>
[Data validation](users_guide.md#data-validation)<br>
[Data deserialization and serialization](users_guide.md#data-deserialization-and-serialization)<br>
[Working with data](users_guide.md#working-with-data)<br>
[Filtering](users_guide.md#filtering)<br>
[Sorting](users_guide.md#sorting)<br>
[Request and response validation](users_guide.md#request-and-response-validation)<br>
[Integrations](users_guide.md#integrations)


## Schema definition

`scimpler` provides all schemas specified by the standard, and some of them can be adjusted for a
particular needs.

**Resource schemas and extensions**

- [urn:ietf:params:scim:schemas:core:2.0:User](api_reference/scimpler_schemas/user_schema.md)
- [urn:ietf:params:scim:schemas:extension:Enterprise:2.0:User](api_reference/scimpler_schemas/enterprise_user_schema_extension.md)
- [urn:ietf:params:scim:schemas:core:2.0:Group](api_reference/scimpler_schemas/group_schema.md)
- [urn:ietf:params:scim:schemas:core:2.0:ResourceType](api_reference/scimpler_schemas/resource_type_schema.md)
- [urn:ietf:params:scim:schemas:core:2.0:Schema](api_reference/scimpler_schemas/schema_definition_schema.md)
- [urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig](api_reference/scimpler_schemas/service_provider_config_schema.md)

**API message schemas**

- [urn:ietf:params:scim:api:messages:2.0:Error](api_reference/scimpler_schemas/error_schema.md)
- [urn:ietf:params:scim:api:messages:2.0:ListResponse](api_reference/scimpler_schemas/list_response_schema.md)
- [urn:ietf:params:scim:api:messages:2.0:SearchRequest](api_reference/scimpler_schemas/search_request_schema.md)
- [urn:ietf:params:scim:api:messages:2.0:PatchOp](api_reference/scimpler_schemas/patch_op_schema.md)
- [urn:ietf:params:scim:api:messages:2.0:BulkRequest](api_reference/scimpler_schemas/bulk_request_schema.md)
- [urn:ietf:params:scim:api:messages:2.0:BulkResponse](api_reference/scimpler_schemas/bulk_response_schema.md)

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

`validate` returns [`scimpler.error.ValidationIssues`](api_reference/scimpler_error/validation_issues.md) always. 
It contains validation errors and validation warnings. Call `ValidationIssues.to_dict` to get nice
representation of all validation errors and warnings that happened during the validation.


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
print(issues.to_dict(message=True))
```

Output
```
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

To deserialize the data, call `deserialize` method on selected schema.

```python
from scimpler.schemas import UserSchema

data = {
    "schemas": [
        "urn:ietf:params:scim:schemas:core:2.0:User",
    ],
    "externalId": "1",
    "userName": "Pagerous",
    "name": {
        "formatted": "Arkadiusz Pajor",
        "familyName": "Pajor",
        "givenName": "Arkadiusz"
    },
    "profileUrl": "https://www.linkedin.com/in/arkadiusz-pajor/",
    "emails": [
        {
            "value": "arkadiuszpajor97@gmail.com",
            "type": "work",
            "primary": True
        }
    ],
}
user = UserSchema()

deserialized = user.deserialize(data)
```

!!! warning
    The data is not validated during serialization and deserialization. You need to call
    `validate` method before.


By default, there is no additional deserialization logic, and values come out as they are passed in.
SCIM-compatible data types come from JSON and do not require additional processing.

It is possible to configure custom deserialization. First way, is to call `set_deserializer`
on [`Attribute`](api_reference/scimpler_data/attribute.md) class, so all instances of the given 
type are deserialized in the same way.

```python
from datetime import datetime
from scimpler.data import DateTime


DateTime.set_deserializer(datetime.fromisoformat)
```

The other way to define custom deserialization logic is to provide `deserializer` parameter
when defining the schema.

```python
from scimpler.data import ResourceSchema, String


def convert_to_lower(value: str) -> str:
    return value.lower()


class MyOwnResource(ResourceSchema):
    name = "MyOwnResource"
    endpoint = "/MyOwnResources"
    base_attrs = [
        String("myString", deserializer=convert_to_lower)
    ]
```

Serialization process and its configuration is analogous.

!!! warning
    You are responsible for making sure the object returned from a deserializer is compatible with
    a serializer.

The data must be validated _**before**_ the deserialization and _**after**_ the serialization.
Otherwise, the validation is likely to fail due to bad value types.

## Working with data

`scimpler` makes use of [`ScimData`](api_reference/scimpler_data/scim_data.md), when working with
data internally, but it is also returned from `deserialize` and `serialize` schema methods. It
implements `MutableMapping` protocol, so it can be used like any dictionary. What it adds is
custom logic for handling provided keys and default values.

Let us consider below data, which is exemplary user resource document:
```python
data = {
    "schemas": [
        "urn:ietf:params:scim:schemas:core:2.0:User",
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
    ],
    "externalId": "1",
    "userName": "bjensen@example.com",
    "name": {
        "familyName": "Jensen",
        "givenName": "Barbara",
    },
    "emails": [
        {"value": "bjensen@example.com", "type": "work", "primary": True},
        {"value": "babs@jensen.org", "type": "home"},
    ],
    "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
        "employeeNumber": "1",
        "costCenter": "4130",
        "organization": "Universal Studios",
        "division": "Theme Park",
        "department": "Tour Operations",
        "manager": {
            "value": "26118915-6090-4610-87e4-49d8ca9f808d",
            "$ref": "../Users/26118915-6090-4610-87e4-49d8ca9f808d",
            "displayName": "John Doe",
        },
    },
}
```
`ScimData` can be populated with it.
```python
from scimpler.data import ScimData

scim_data = ScimData(data)
```

It is possible to read the attribute in a case-insensitive way.
```python
>>> scim_data["USERNAME"]
"bjensen@example.com"
```

As well as specific sub-attribute.
```python
>>> scim_data["name.givenname"]
"Barbara"
```

If you read sub-attribute of multi-valued complex attribute, you get all values for that sub-attribute.
```python
>>> scim_data["emails.value"]
["bjensen@example.com", "babs@jensen.org"]
```

To access attribute from extension, you need to provide extension schema URI.
```python
>>> scim_data["urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:manager.displayName"]
"John Doe"
```

A key in `ScimData` can be an instance of [`AttrRep`](api_reference/scimpler_data/attr_rep.md) 
and [`BoundedAttrRep`](api_reference/scimpler_data/bounded_attr_rep.md), what makes it very
convenient to use, when you have schema instance.

```python
>>> from scimpler.schemas import UserSchema
>>>
>>> user = UserSchema()
>>> scim_data[user.attrs.emails__value]
["bjensen@example.com", "babs@jensen.org"]

>>> scim_data[user.attrs.manager__displayName]
"John Doe"
```

If the value for the specified key can not be found, the special `Missing` object is returned to
indicate the client did not provide value. It is required since `None` / `null` has special
semantics of clearing the present value of the attribute in service provider.


Setting the value is similar. SCIM requires the extension data to reside in its own namespace (which is
schema URI). `ScimData` does it for you. It is enough to provide simple mapping of `BoundedAttrRep` to value.

```python
print(
    ScimData(
        {
            user.attrs.name__formatted: "John Doe",
            user.attrs.userName: "johndoe",
            user.attrs.emails: [{"value": "john@doe.com"}],
            user.attrs.employeeNumber: "42",
            user.attrs.manager__displayName: "For Sure Not John Doe"
        }
    ).to_dict()
)
```
Output
```
{
    "name": {
        "formatted": "John Doe"
    },
    "userName": "johndoe",
    "emails": [{"value": "john@doe.com"}],
    "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
        "employeeNumber": "42",
        "manager": {
            "displayName": "For Sure Not John Doe"
        }
    }
}
```

You can add the key and value to existing data.

```python
scim_data.set(user.attrs.nickName, "johny")
```

Every schema allows you to filter the data. This kind of filtering bases on attribute properties.
Not to be confused with [Filtering](users_guide.md#filtering).

```python
from scimpler.data import AttrFilter


# resulting data will contain only "readOnly" attributes
scim_data = user.filter(
    scim_data, AttrFilter(filter_=lambda attr: attr.mutability == "readOnly")
)
```

## Filtering
SCIM defines complex syntax for filter definition and `scimpler` supports it. [`Filter`](api_reference/scimpler_data/filter.md)
supports validation, deserialization, and serialization. You can also pass data to the deserialized
filter to check if there is match.

```python
from scimpler.data import Filter


issues = Filter.validate(
    "userName eq 'johndoe' or (emails[type neq 'home'] and nickName sw 15)"
)
print(issues.to_dict(message=True))
```
```
{
    "_errors": [
        {
            "code": 104,
            "message": "unknown operator 'neq' in expression 'type neq 'home''"
        },
        {
            "code": 110,
            "message": "operand 15 is not compatible with 'sw' operator"
        }
    ]
}
```

Valid filter expression can be deserialized, and later the `Filter` instance can be serialized.

```python
filter_ = Filter.deserialize(
    "userName eq 'johndoe' or (emails[type ne 'home'] and nickName sw 'j')"
)
print(filter_.serialize())
```
```
userName eq 'johndoe' or (emails[type ne 'home'] and nickName sw 'j')
```

`Filter` instance can be converted to dictionary.

```python
print(filter_.to_dict())
```
```
{
    "op": "or",
    "sub_ops": [
        {
            "op": "eq",
            "attr": "userName",
            "value": "johndoe"
        },
        {
            "op": "and",
            "sub_ops": [
                {
                    "op": "complex",
                    "attr": "emails",
                    "sub_op": {
                        "op": "ne",
                        "attr": "type",
                        "value": "home"
                    }
                }, 
                {
                    "op": "sw",
                    "attr": "nickName",
                    "value": "j"
                }
            ]
        }
    ]
}
```

If the data is passed to filter, the flag indicating whether there is a match is returned.

```python
filter_(  # True
    {
        "userName": "johndoe",
        "emails": [{"type": "home", "value": "home@example.com"}]
        "nickName": "johny"
    }
)
filter_(  # False
    {
        "userName": "doejohn",
        "emails": [{"type": "work", "value": "work@example.com"}]
        "nickName": "doe"
    }
)
```


## Sorting

## Request and response validation

## Integrations
### marshmallow