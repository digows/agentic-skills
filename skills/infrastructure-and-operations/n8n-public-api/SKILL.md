---
name: n8n-public-api
description: Use n8n Public API v1 to inspect and safely manage workflows, executions, credentials, projects, variables, tags, data tables, users, and supported instance resources. Use for n8n /api/v1 requests, OpenAPI discovery, API-key authentication, and capability checks on a selected n8n instance.
license: Apache-2.0
---

# n8n Public API v1

Use this skill only for n8n's documented public API at `/api/v1`. Do not infer or call internal UI endpoints. The selected instance's OpenAPI document and discovery response are the source of truth for its available operations and request schemas.

## Core procedure

1. Identify the explicit target profile or base URL and the requested operation: read, create, update, delete, retry, stop, transfer, activate, or deactivate.
2. Read [`references/openapi.md`](references/openapi.md) before selecting an endpoint or composing a request body.
3. Resolve authentication for the selected target as described below.
4. For a restricted, optional, plan-gated, or uncertain operation, use the target's documented capability-discovery surface before composing the request.
5. For list operations, follow [`references/pagination.md`](references/pagination.md). Preserve cursors exactly and treat them as opaque.
6. State the side effect before a mutation. Request confirmation for destructive, external-write, activation, deactivation, credential, user, project-membership, source-control, or package-management operations unless that authority was already explicit.
7. Validate response status and shape against the selected target's OpenAPI. Do not invent endpoints, fields, or public API behavior.

## Authentication

Resolve the target before resolving a credential. The target is a canonical n8n base URL or named local profile; it is not inferred from a workflow ID, hostname suffix, or a generic token.

Use only the credential reference bound to that exact target in local harness configuration. For the documented public API flow, send the resolved API key only in the `X-N8N-API-KEY` header. Never place a secret in a URL, prompt, source-controlled file, command trace, or response.

If a valid credential is already available for the selected profile, continue without prompting. Ask for setup or reauthorization only if the profile is missing, the credential cannot be resolved, or the target returns `401` or `403`. Stop on either status; do not try a credential from another profile. A `404` does not establish that a resource belongs to another instance.

When a harmless authenticated read is documented and needed to validate a new profile, perform it once and record only the outcome, never the authorization header or token.

## Upstream compatibility

This draft targets the n8n Public API v1 contract, not a claimed n8n service-release range. Before every task, retrieve the selected instance's OpenAPI document. For operations affected by licensing, role, scope, feature availability, or optional resources, also use the documented `GET /discover` capability surface when available on that target.

Do not infer support from another host, a nearby n8n release, the public documentation, or a response schema from a different instance. If the target OpenAPI or discovery response does not expose the requested operation, report it as unsupported for that target.

## Operational boundaries

- The public API supports inspecting, retrying, stopping, and deleting existing executions. Do not claim it provides a generic endpoint to start a new manual workflow execution unless the selected target's OpenAPI explicitly provides one.
- Retrieve the current workflow before updating it. Treat changes to an active workflow, activation, and deactivation as potentially externally visible operations; require explicit authority.
- Treat credential create, update, test, transfer, and delete operations as sensitive. Never return credential secrets even if a response includes a redacted or placeholder field.
- Treat user, project, package, source-control, and security-audit operations as privileged until the selected target's OpenAPI, discovery data, scopes, and user authority demonstrate otherwise.
- For an unknown API response or schema mismatch, stop and inspect the target OpenAPI or discovery data instead of guessing a retry payload.
