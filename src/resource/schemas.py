from src.resource.attributes import error as error_attrs
from src.resource.attributes import list_result as query_result_attrs
from src.resource.attributes import search_request as search_request_attrs
from src.resource.attributes import user as user_attrs
from src.resource.attributes import user_enterprise_extension as enterprise_attrs
from src.schemas import ResourceSchema, Schema, SchemaExtension

LIST_RESPONSE = Schema(
    schema="urn:ietf:params:scim:api:messages:2.0:listresponse",
    repr_="ListResponse",
    attrs=[
        query_result_attrs.total_results,
        query_result_attrs.start_index,
        query_result_attrs.items_per_page,
    ],
)

ERROR = Schema(
    schema="urn:ietf:params:scim:api:messages:2.0:error",
    repr_="Error",
    attrs=[
        error_attrs.status,
        error_attrs.scim_type,
        error_attrs.detail,
    ],
)

USER_ENTERPRISE_EXTENSION = SchemaExtension(
    schema="urn:ietf:params:scim:schemas:extension:enterprise:2.0:user",
    attrs=[
        enterprise_attrs.employee_number,
        enterprise_attrs.cost_center,
        enterprise_attrs.division,
        enterprise_attrs.department,
        enterprise_attrs.organization,
        enterprise_attrs.manager,
    ],
)

USER = ResourceSchema(
    schema="urn:ietf:params:scim:schemas:core:2.0:user",
    repr_="User",
    attrs=[
        user_attrs.user_name,
        user_attrs.name,
        user_attrs.display_name,
        user_attrs.nick_name,
        user_attrs.profile_url,
        user_attrs.title,
        user_attrs.user_type,
        user_attrs.preferred_language,
        user_attrs.locale,
        user_attrs.timezone,
        user_attrs.active,
        user_attrs.password,
        user_attrs.emails,
        user_attrs.ims,
        user_attrs.photos,
        user_attrs.addresses,
        user_attrs.groups,
        user_attrs.entitlements,
        user_attrs.roles,
        user_attrs.x509_certificates,
    ],
).with_extension(USER_ENTERPRISE_EXTENSION, required=True)

SEARCH_REQUEST = Schema(
    schema="urn:ietf:params:scim:api:messages:2.0:searchrequest",
    repr_="SearchRequest",
    attrs=[
        search_request_attrs.attributes,
        search_request_attrs.exclude_attributes,
        search_request_attrs.filter_,
        search_request_attrs.sort_by,
        search_request_attrs.sort_order,
        search_request_attrs.start_index,
        search_request_attrs.count,
    ],
)
