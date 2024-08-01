`scimpler` provides functionalities that can be used both on Service Provider
and Provisioning client sides. It is agnostic to any existing web frameworks,
so it probably will not work out of the box in your case. However, most of the hard work has already been
done for you. **SCIM 2.0** protocol exactly specifies how the entities may, should, and
must behave (depending on the case). `scimpler` maps all _possible_ requirements and makes them
ready to use.

`scimpler`, among many features, enables SCIM schema definition and _stateless_ validation. This means
that any requirement specified by the protocol that requires _state_ is not checked by the library.

Check below topics to learn more about `scimpler`!

[Schema definition](users_guide.md#schema-definition)<br>
[Data validation](users_guide.md#data-validation)

---

## Schema definition

`scimpler` provides all schemas specified by the protocol, and some of them can be adjusted for a
particular needs.

**Resource schemas and extensions**

- urn:ietf:params:scim:schemas:core:2.0:User
- urn:ietf:params:scim:schemas:extension:enterprise:2.0:User
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
        attr_names=["name.formatted", "x509Certificates"],
        include=False,
    )
)
enterprise_extension = EnterpriseUserSchemaExtension(
    AttrFilter(
        attr_names=["manager"],
        include=True,
    )
)
user_schema.extend(enterprise_extension, required=True)
```

!!! info
    
    Required attributes and sub-attributes (like `id` or `schemas` in resources) are included anyway.

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

Every schema provides three main functionalities: data **validation**, **deserialization**, and **serialization**.

---

## Data validation

Placeholder
