# Target OpenAPI and capability discovery

Use the selected n8n instance's API contract, not a copied endpoint list, to select operations and construct requests.

1. Normalize the selected base URL without changing its host, port, or configured path prefix.
2. Retrieve `<base-url>/api/v1/openapi.yml` when the target permits it. Read the OpenAPI `info.version`, security schemes, paths, request schema, response schema, and documented status codes for the specific operation.
3. For optional, restricted, or version-sensitive operations, call `GET <base-url>/api/v1/discover` with only query parameters documented by that target OpenAPI. Use its result to verify accessible resources, operations, scopes, and schemas.
4. If either source is unavailable, use the official n8n endpoint reference only to explain the limitation or ask for the target's supported contract. Do not substitute an endpoint from another instance.

The upstream source OpenAPI is maintained in the n8n repository at `packages/cli/src/public-api/v1/openapi.yml`. It describes the Public API base path `/api/v1`, API-key security through `X-N8N-API-KEY`, and the public API version. It is a design reference, not proof that every deployed target exposes every operation.

Official references:

- https://docs.n8n.io/connect/n8n-api/api-reference/
- https://docs.n8n.io/connect/n8n-api/authentication/
- https://github.com/n8n-io/n8n/blob/master/packages/cli/src/public-api/v1/openapi.yml
