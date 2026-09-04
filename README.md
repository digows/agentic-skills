# Agentic Skills

A public catalogue of portable Agent Skills. The repository is intentionally provider-agnostic: portable instructions use the [Agent Skills](https://agentskills.io/specification) format, while provider-specific packaging or setup remains outside the canonical skill.

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

## Compatibility model

The canonical `SKILL.md` contains only portable Agent Skills fields and instructions. `catalog.json` records requirements, risk, provenance, compatibility evidence, and evaluation references. Provider-specific material belongs under `adapters/`; it must not alter the portable skill contract.

See [`docs/catalog-contract.md`](docs/catalog-contract.md) before adding a skill and [`CONTRIBUTING.md`](CONTRIBUTING.md) before opening a pull request.

## Security

Do not commit credentials, live endpoints with embedded credentials, private network inventories, customer data, or production exports. Report vulnerabilities privately through the [security advisory form](https://github.com/digows/agentic-skills/security/advisories/new); see [`SECURITY.md`](SECURITY.md).
