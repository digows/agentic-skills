# Upstream compatibility contract

This contract applies to every published skill with `requirements.network_access: true`. It describes compatibility with the target service. It is distinct from `catalog.json.compatibility`, which records evidence for agent harnesses.

## Required compatibility record

An applicable skill must declare `upstream_compatibility` in `catalog.json` and an `## Upstream compatibility` section in `SKILL.md`.

```json
{
  "service": "n8n",
  "api_version": "v1",
  "supported_service_versions": [">=1.70.0 <2.0.0"],
  "capability_discovery": {
    "strategy": "runtime-probe",
    "reference": "GET /api/v1/discover before an optional or restricted operation"
  },
  "openapi_contract": {
    "source_url": "https://github.com/n8n-io/n8n/blob/master/packages/cli/src/public-api/v1/openapi.yml",
    "target_path": "/api/v1/openapi.yml",
    "swagger_ui_path": "/api/v1/docs"
  },
  "evidence": [
    {
      "service_version": "1.80.0",
      "api_version": "v1",
      "verified_at": "2026-09-05",
      "result": "pass"
    }
  ]
}
```

- `service` identifies the target service.
- `api_version` identifies the API contract used by the skill.
- `supported_service_versions` is a non-empty list of documented version ranges or exact versions. Use the upstream version syntax; do not imply that an untested version is verified.
- `capability_discovery` states how the skill determines features available on a specific target. `runtime-probe` is preferred when the upstream provides a bounded discovery endpoint. `published-openapi` and `documentation` are valid when the exact service contract is available there. Use `none` only when the upstream has no capability-discovery mechanism, and state that reason in `reference`.
- Before writing a networked skill, search for an official machine-readable API contract. When the upstream publishes OpenAPI, record `openapi_contract`: `source_url` is its official HTTPS source, `target_path` is the absolute path to retrieve from the selected target, and `swagger_ui_path` is the optional target-relative interactive documentation path. Retrieve the target contract before choosing a version-sensitive, optional, or mutation request. If no official OpenAPI contract exists, record that finding and the authoritative documentation searched in `capability_discovery.reference`; never reconstruct endpoints from UI traffic or unofficial collections.
- `evidence` records exact service/API combinations that were evaluated. A published compatibility claim requires at least one passing result.

## Runtime behavior

Version is a selection boundary, not proof that a target supports every operation. Before an optional, restricted, plan-gated, or version-sensitive operation, the skill must use the declared discovery strategy against the selected target. It must stop and explain an unsupported operation rather than infer support from a nearby release, another host, or a documentation example.

Split a skill only when a new upstream major version changes its procedure, safety boundary, or authentication model materially. Otherwise, keep one skill, document the variant in `references/`, and select behavior through the declared capability-discovery strategy.
