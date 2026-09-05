# Pagination

For a list endpoint, read its selected target OpenAPI before adding query parameters. When it exposes `limit` and `cursor`:

1. Send only documented filters and a bounded `limit`.
2. Preserve the returned cursor exactly; it is opaque.
3. Send that cursor only to the same target, resource, and operation that issued it.
4. Stop when the response has no next cursor.

Do not manufacture cursors, convert them to offsets, reuse them on another instance, or assume every n8n list endpoint supports the same pagination parameters.
