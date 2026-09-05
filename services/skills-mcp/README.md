# Agentic Skills MCP Worker

Public, stateless, read-only MCP endpoint for the Agentic Skills catalogue.

## Endpoint

After deployment, configure MCP-compatible clients with:

```json
{
  "url": "https://agentic-skills-mcp.digows.com"
}
```

The Worker reads [`catalog/index.json`](../../catalog/index.json) from the public GitHub repository at the current `main` commit. Local files are fetched from that immutable commit and verified against the index digest. Federated upstream files are fetched only from their manifest-declared GitHub repository and immutable commit, verified against their upstream digest, then resolved with any declared section overlay.

## Tools

- `list_skills` provides compact, paginated published-skill metadata.
- `search_skills` performs bounded lexical discovery.
- `get_skill` retrieves canonical `SKILL.md` content.
- `get_skill_file` retrieves only a file declared in the published manifest.

The Worker never executes scripts or upstream hooks, accepts credentials, follows mutable upstream branches, fetches arbitrary URLs, or serves planned and draft skills. It has no secrets, storage binding, or write capability.

## Local checks

```bash
npm ci
npm run check
npm run dev
```

Use an MCP inspector or a compatible client to test `http://localhost:8787`. `GET /healthz` is only an operational health check; it is not an MCP endpoint.
