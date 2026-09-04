# Agentic Skills

[![Validate](https://github.com/digows/agentic-skills/actions/workflows/validate.yml/badge.svg)](https://github.com/digows/agentic-skills/actions/workflows/validate.yml)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)

A provider-agnostic catalogue of portable Agent Skills for AI agents, coding agents, workflow automation, and multi-model agent harnesses. Canonical instructions use the open [Agent Skills](https://agentskills.io/specification) format; provider-specific packaging stays outside the portable skill.

The project exists to make specialized operational knowledge usable by both small and advanced models without coupling that knowledge to a single model, provider, or harness.

## Status

The repository is in its foundation phase. It contains no published skills yet. The first planned domains are n8n, GitLab, Home Assistant, MikroTik, UniFi, and RITA; they are tracked in [`catalog/planned-skills.json`](catalog/planned-skills.json), not represented by empty or activatable skills.

## Repository layout

```text
skills/<skill-id>/
  SKILL.md                 # Portable Agent Skills entrypoint
  catalog.json             # Repository catalogue sidecar
  evals/definition.json    # Reproducible evaluation contract
  adapters/<provider>/     # Optional, non-canonical provider packaging
schemas/                   # JSON Schema contracts
catalog/                   # Taxonomy and planned-skill registry
tooling/                   # Dependency-free validation and tests
```

Skills are deliberately flat under `skills/`. Categories are catalogue metadata, not directories, because discovery behavior is not consistently recursive across agent harnesses.

## Quality gate

Run the exact repository gate locally:

```bash
python3 tooling/validate_repository.py
python3 -m unittest discover -s tooling/tests -p "test_*.py" -v
```

The same commands run for pull requests and pushes to `main`. They do not require credentials or repository secrets.

## MCP discovery endpoint

MCP-compatible agents can discover and retrieve published skills through the public read-only Worker in [`services/skills-mcp`](services/skills-mcp). The Worker resolves the current Git commit, verifies each file digest, and never executes skill scripts. Agents without MCP support can use the same catalogue directly from GitHub.

## Compatibility model

The canonical `SKILL.md` contains only portable Agent Skills fields and instructions. `catalog.json` records requirements, risk, provenance, compatibility evidence, and evaluation references. Provider-specific material belongs under `adapters/`; it must not alter the portable skill contract.

See [`docs/catalog-contract.md`](docs/catalog-contract.md) before adding a skill and [`CONTRIBUTING.md`](CONTRIBUTING.md) before opening a pull request.

## Planned domains

The first domains are intentionally planned, not prematurely published: n8n, GitLab, Home Assistant, MikroTik, UniFi, and RITA. Every future skill must include a concrete authority boundary, compatibility evidence, and an evaluation definition before it is considered published.

## Contributing

Contributions are welcome under the [Apache License 2.0](LICENSE). Start with [`CONTRIBUTING.md`](CONTRIBUTING.md), use the skill-request issue form for new domains, and keep pull requests focused and reproducible.

## Security

Do not commit credentials, live endpoints with embedded credentials, private network inventories, customer data, or production exports. Report vulnerabilities privately through the [security advisory form](https://github.com/digows/agentic-skills/security/advisories/new); see [`SECURITY.md`](SECURITY.md).
