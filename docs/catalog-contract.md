# Catalogue contract

## Design boundary

Each published skill has three distinct layers:

1. `SKILL.md` is the portable Agent Skills entrypoint.
2. `catalog.json` is repository metadata for discovery, governance, and evidence.
3. `adapters/<provider>/` holds optional provider packaging that cannot be expressed portably.

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

Categories are stable, broad groups in [`catalog/taxonomy.json`](../catalog/taxonomy.json). Facets describe the capability, artifact, execution context, and side effect without creating a directory hierarchy.

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
