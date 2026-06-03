"""Staff (security-server) HTTP endpoints, mounted under /security-api/api/*.

The routers in this package replace the legacy Spring `security-server`
service. Routing structure mirrors the old Java controllers 1-to-1 so the
existing `security-server-ui` front-end can keep working with only its
`VITE_API_BASE` flipped to `/security-api`.
"""
