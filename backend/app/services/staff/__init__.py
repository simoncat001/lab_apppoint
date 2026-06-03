"""Staff (security-server) business services.

These are FastAPI ports of the legacy Spring `service.impl.*ServiceImpl`
classes. They use the same SQLAlchemy `Base` / session as nemo, but operate
only on the `staff_*` tables.
"""
