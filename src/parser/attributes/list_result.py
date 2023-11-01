from ..attributes import type as at
from .attributes import Attribute

total_results = Attribute(
    name="totalResults",
    type_=at.Integer,
    required=True,
)

start_index = Attribute(
    name="startIndex",
    type_=at.Integer,
)

items_per_page = Attribute(
    name="itemsPerPage",
    type_=at.Integer,
)
