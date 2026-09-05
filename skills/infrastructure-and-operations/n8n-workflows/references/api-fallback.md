# Public API fallback

Use this path only when the required native MCP tool is unavailable.

1. Normalize the selected n8n base URL without changing its host, port, or configured path prefix.
2. Retrieve `<base-url>/api/v1/openapi.yml` when the target exposes it. Select the method, request schema, response schema, security scheme, and status codes from that exact contract.
3. For optional or restricted operations, call `GET <base-url>/api/v1/discover` only with query parameters documented by that target contract.
4. Send a resolved API key only in `X-N8N-API-KEY`; never log or return the value.
5. Do not substitute an internal endpoint, API method from another instance, or MCP-only behavior when the target contract lacks the requested operation.

The Public API is appropriate for documented workflow reads and mutations. It does not automatically provide the Workflow SDK build, graph verification, or lifecycle testing facilities of the native MCP path. Apply the same retrieve, validate, test, authority, and handoff requirements manually before reporting success.

Official references:

- https://docs.n8n.io/connect/n8n-api/api-reference/
- https://docs.n8n.io/connect/n8n-api/authentication/
- https://github.com/n8n-io/n8n/blob/master/packages/cli/src/public-api/v1/openapi.yml
