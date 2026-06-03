"""Pydantic schemas for the ported security-server endpoints.

Field names are kept in camelCase via `Field(alias=...)` and a shared
`ConfigDict(populate_by_name=True, alias_generator=...)` so the existing
front-end's JSON payloads remain unchanged.
"""
