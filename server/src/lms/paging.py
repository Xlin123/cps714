"""Shared bounds for paged list endpoints, so every list pages the same way.

Example::

    @router.get("")
    async def browse(limit: Limit = PAGE_SIZE_DEFAULT, offset: Offset = 0) -> ...: ...
"""

from typing import Annotated

from fastapi import Query

PAGE_SIZE_DEFAULT = 50
# Bounds the rows one request can pull.
PAGE_SIZE_MAX = 100

Limit = Annotated[int, Query(ge=1, le=PAGE_SIZE_MAX)]
Offset = Annotated[int, Query(ge=0)]
