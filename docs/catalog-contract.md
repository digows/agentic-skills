# Catalogue contract

## Design boundary

Each published skill has three distinct layers:

1. `SKILL.md` is the portable Agent Skills entrypoint.
2. `catalog.json` is repository metadata for discovery, governance, and evidence.
3. `adapters/<provider>/` holds optional provider packaging that cannot be expressed portably.

The catalogue can also federate an upstream skill without copying it. An upstream entry lives at `upstreams/<skill-id>/catalog.json`; it records the upstream GitHub repository, full immutable commit SHA, license, reviewed date, and every retrievable file with its SHA-256. Its optional `overlay.json` is local policy with deterministic precedence over the upstream content.

Do not put provider-specific frontmatter, credentials, or user-specific configuration in `SKILL.md`. The canonical file uses the Agent Skills fields `name`, `description`, and, when applicable, `license`, `compatibility`, `metadata`, and `allowed-tools`.

## Required published-skill files

```text
skills/<category>/<skill-id>/
  SKILL.md
  catalog.json
  evals/
    definition.json
```

`<skill-id>` and the `name` frontmatter value are lowercase kebab-case and must match. `<category>` must be one of the stable categories in [`catalog/taxonomy.json`](../catalog/taxonomy.json) and must match `catalog.json.category`. This directory level is for repository navigation; agents discover skills through the generated catalogue index or MCP tools.

## Catalogue metadata

`catalog.json` conforms to [`schemas/catalog.schema.json`](../schemas/catalog.schema.json). It records:

- semantic version and lifecycle state;
- one primary category plus facets;
- declared side effects and risk level;
- upstream source and review date;
- requirements and compatibility evidence; and
- evaluation definition and report references.

When `requirements.credentials` is non-empty, `catalog.json` must also contain the portable `authentication` policy defined in [`authentication-contract.md`](authentication-contract.md), and `SKILL.md` must contain an `## Authentication` section. The policy records how an agent must resolve and recover authentication, including the clipboard-first onboarding UX; it never contains a secret, host inventory, or runtime-specific secret path.

When `requirements.network_access` is `true`, `catalog.json` must also contain `upstream_compatibility` and `SKILL.md` must contain an `## Upstream compatibility` section. See [`upstream-compatibility-contract.md`](upstream-compatibility-contract.md). This is separate from `compatibility`: the former records target-service/API evidence, while the latter records agent-harness evidence.

For every networked skill, contributors must first search for an official OpenAPI contract and record the result in `api_contract_discovery`. When found, record its official source and target-relative retrieval path; when not found, record the official evidence for its absence. Use the selected target's contract at runtime instead of inferring endpoints from prose, UI traffic, or another deployment.

Categories are stable, broad groups in [`catalog/taxonomy.json`](../catalog/taxonomy.json). Facets describe the capability, artifact, execution context, and side effect without creating a directory hierarchy.

## Federated upstream skills and overlays

Use an upstream entry when its maintainer is the authority and the skill already solves the task. Do not fork or copy it into `skills/` merely to list it here.

`overlay.json` can modify one exact Markdown section in the upstream `SKILL.md` using three operations: `append`, `replace`, or `remove`. The operation targets a single heading such as `## Authentication`; `append` and `replace` supply replacement body content, while `remove` removes that heading and its section. Operations are applied in order. If a target heading is absent or ambiguous, resolution fails rather than applying a patch loosely.

An overlay is for explicit, reviewed supplementation. It must not silently change provenance, claim upstream behavior that was not reviewed, execute upstream scripts or hooks, or grant/deny harness tools and MCP servers. Harness permissions remain outside the catalogue.

The MCP returns the resolved content and retains upstream provenance in discovery metadata. It downloads only manifest-declared files from the declared GitHub repository at the declared commit, verifies the upstream file SHA-256, and then applies the overlay in memory. It never follows a mutable branch or an agent-supplied URL.

Every federated upstream entry declares `authentication`: either `null` when the referenced skill does not need access, or the same portable authentication policy required by local skills. When authentication is needed, an overlay must make that policy operational in the resolved skill without introducing provider-specific onboarding.

## Evaluations

`evals/definition.json` conforms to [`schemas/evaluation.schema.json`](../schemas/evaluation.schema.json). Its cases must represent realistic requests, include the expected outcome, and identify whether a human review is required. Measure a no-skill baseline and retain the report location in `catalog.json`; do not infer benefit from a single successful run.

## Risk levels

| Level | Meaning |
| --- | --- |
| `low` | Read-only or local transformation with no sensitive inputs. |
| `moderate` | Bounded changes or access to non-sensitive service data. |
| `high` | External writes, credentials, infrastructure control, or sensitive operational data. |
| `critical` | Security enforcement, destructive operations, privileged access, or broad production impact. |

High- and critical-risk skills require explicit authority checks, a dry-run or confirmation boundary where feasible, and evaluation coverage for denied or unsafe requests.

## Script contract

Scripts must be deterministic, non-interactive by default, explicit about input and output, and safe to retry. They must not fetch and execute remote content, use privilege escalation, or obscure side effects. The repository validator applies a deliberately narrow static check; maintainers still review scripts manually.
