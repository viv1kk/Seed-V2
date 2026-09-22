"""Shared model base.

Python is written in snake_case and TypeScript reads camelCase. Rather
than translating at every boundary, models serialise under camelCase
aliases and accept either form on the way in. FR-L4 names the field
`blockedOn`, and this is what makes the wire match the requirement
without contorting the Python.
"""

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class Schema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )
