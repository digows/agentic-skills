---
id: 672fca9d-8e91-40fb-8ee9-936cfe9fd2e8
title: Skills MCP Worker
status: draft
---
# Goal

Provide a public, provider-agnostic read-only MCP endpoint that lets compatible agents discover and retrieve published skills from this repository.

# Scope

Implement a Cloudflare Worker in this repository; generate and validate a compact skill index; serve stateless Streamable HTTP MCP tools and optional resources; obtain the public catalogue from immutable GitHub content; and deploy it to the digows Cloudflare account.

# Constraints

- GitHub remains the canonical source for skills and catalogue metadata.
- The Worker accepts no credentials and performs no external writes.
- Published skills only are discoverable.
- Content retrieval is pinned to a source commit and verified against a digest from the index.
- The service is stateless and does not require OAuth, Durable Objects, KV, R2, or a GitHub token for the public MVP.
- Worker code and deployment configuration remain public in this repository.

# Acceptance criteria

- A generated index lists published skills with stable identifiers, compact discovery metadata, source commit, and SHA-256 digest.
- `/mcp` supports compatible stateless MCP clients and exposes bounded list, search, skill, and skill-file retrieval.
- Inputs, result sizes, relative paths, GitHub origins, and file hashes are validated; no arbitrary URL fetch or script execution is possible.
- Unit and integration tests cover discovery, pagination, retrieval, invalid input, digest mismatch, stale-cache fallback, and protocol tool listing.
- CI validates the Worker, index generation, package lock, and existing repository gates.
- The Worker is deployed to the digows Cloudflare profile and verified with a live read-only MCP request.
- Documentation explains client configuration, security boundaries, release behavior, and direct GitHub fallback.
