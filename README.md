# scimpler: SCIM integrations made simpler
![GitHub CI](https://github.com/Pagerous/scimpler/actions/workflows/ci.yaml/badge.svg)
[![Lines of Code](https://sonarcloud.io/api/project_badges/measure?project=Pagerous_scimpler&metric=ncloc)](https://sonarcloud.io/summary/new_code?id=Pagerous_scimpler)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=Pagerous_scimpler&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=Pagerous_scimpler)
[![Reliability Rating](https://sonarcloud.io/api/project_badges/measure?project=Pagerous_scimpler&metric=reliability_rating)](https://sonarcloud.io/summary/new_code?id=Pagerous_scimpler)
[![Security Rating](https://sonarcloud.io/api/project_badges/measure?project=Pagerous_scimpler&metric=security_rating)](https://sonarcloud.io/summary/new_code?id=Pagerous_scimpler)
[![Maintainability Rating](https://sonarcloud.io/api/project_badges/measure?project=Pagerous_scimpler&metric=sqale_rating)](https://sonarcloud.io/summary/new_code?id=Pagerous_scimpler)

`scimpler` makes it easier to ensure both Service Provider and Provisioning Client
integrate with **SCIM 2.0** protocol flawlessly. It implements definitions, validation rules, and
operations, as specified in [RFC-7643](https://www.rfc-editor.org/rfc/rfc7643) 
and [RFC-7644](https://www.rfc-editor.org/rfc/rfc7644).

# Features
- All SCIM-defined resource and API message schemas
- Custom resource schemas and extensions
- SCIM requests and responses validation
- Filters with SCIM-defined and custom operators
- Data sorting
- Attribute-based data filtering
- Convenient SCIM data access and composition
- Optional integration with [marshmallow](https://pagerous.github.io/scimpler/api_reference/scimpler_ext/marshmallow/) schemas


### **[See documentation](https://pagerous.github.io/scimpler/)**


# Installation

Use **pip** to install `scimpler`.

```
pip install scimpler
```

If you want to integrate with marshmallow, install `scimpler` with optional dependencies.

```
pip install "scimpler[marshmallow]"
```

# Quick start
## Set Service Provider configuration

```python
from scimpler import config

config.set_service_provider_config(
    config.ServiceProviderConfig.create(
        patch={"supported": True}
    )
)
```

## Validate request

```python
from scimpler import query_string, validator
from scimpler.schemas import UserSchema

query_string_handler = query_string.ResourceObjectPatch()
val = validator.ResourceObjectPatch(resource_schema=UserSchema())

request_query_string = {
    "attributes": "name,bad^attributeName"
}
request_data = {
    "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
    "Operations": [
        {
            "op": "add",
            "path": "nickName",
            "value": "Pagerous",
        },
        {
            "op": "replace",
            "path": "emails[type eq 'home']",
            "value": 42,
        },
        {
            "op": "remove",
            "path": "name.nonExisting"
        },
        {
            "op": "replace",
            "path": "ims[ty"
        }
    ]
}

query_string_issues = query_string_handler.validate(request_query_string)
request_issues = val.validate_request(request_data)

print("query_string_issues:\n", query_string_issues.to_dict(message=True))
print("request_issues:\n", request_issues.to_dict(message=True))
```

Output
```
query_string_issues:
{
  "attributes": {
    "1": {
      "_errors": [
        {"code": 17, "message": "bad attribute name "bad^attributeName""}
      ]
    }
  }
}

request_issues:
{
  "body": {
    "Operations": {
      "1": {
        "value": {
          "errors": [{"code": 2, "message": "bad type, expecting 'complex'"}]
        }
      },
      "2": {
        "path": {
          "errors": [{"code": 28, "message": "unknown modification target"}]
        }
      }
      "3": {
        "path": {
          "errors": [{"code": 1, "message": "bad value syntax"}]
        },
        "value": {
          "errors": [{"code": 5, "message": "missing"}]
        }
      },
    }
  }
}
```

## Deserialize (or serialize) data

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

# convenient, case-insensitive data access
print(deserialized["name.formatted"])
print(deserialized["pRoFiLeUrL"])
print(deserialized["emails"][0].get("display"))
```
Output
```
Arkadiusz Pajor
https://www.linkedin.com/in/arkadiusz-pajor/
Missing
```

## Validate response

```python
from scimpler.data import AttrValuePresenceConfig
from scimpler.schemas import UserSchema
from scimpler import validator

response_data = {
    "schemas": [
        "urn:ietf:params:scim:schemas:core:2.0:User",
    ],
    "id": "1",
    "externalId": "1",
    "userName": "Pagerous",
    "password": "12345678",
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
    "meta": {
        "resourceType": "User",
        "created": "1997-10-17T00:00:00",
        "lastModified": "2024-09-09T22:13:00",
        "location": "https://example.com/v2/Users/1",
    }
}
val = validator.ResourceObjectGet(resource_schema=UserSchema())

response_issues = val.validate_response(
    status_code=201,
    body=response_data,
    presence_config=AttrValuePresenceConfig(
        "RESPONSE",
        attr_reps=["name.familyName", "emails.primary"],
        include=False
    )
)

print(response_issues.to_dict(message=True))
```
Output
```
{
  "body": {
    "name": {
      "familyName": {
        "_errors": [{"code": 7, "message": "must not be returned"}]
      }
    },
    "password": {
      "_errors": [{"code": 7, "message": "must not be returned"}]
    },
    "emails": {
      "0": {
        "primary": {
          "_errors": [{"code": 7, "message": "must not be returned"}]
        }
      }
    }
  },
  "status": {
    "_errors": [
      {"code": 19, "message": "bad status code, expecting '200'"}
    ]
  }
}
```
