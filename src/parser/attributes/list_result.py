from .attributes import Attribute, AttributeIssuer
from ..attributes import type as at


total_results = Attribute(
    name="totalResults",
    type_=at.Integer,
    issuer=AttributeIssuer.SERVICE_PROVIDER,
    required=True,
)

start_index = Attribute(
    name="startIndex",
    type_=at.Integer,
    issuer=AttributeIssuer.SERVICE_PROVIDER,
)

items_per_page = Attribute(
    name="itemsPerPage",
    type_=at.Integer,
    issuer=AttributeIssuer.SERVICE_PROVIDER,
)
