from src.attributes import type as at
from src.attributes.attributes import Attribute

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

resources = Attribute(
    name="Resources",
    type_=at.Unknown,
)
