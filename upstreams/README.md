# Federated upstream skills

An upstream entry references an authoritative skill without copying or forking it. Each entry lives at `upstreams/<skill-id>/catalog.json`; an optional sibling `overlay.json` can append, replace, or remove a named Markdown section from the upstream `SKILL.md`.

Every upstream file is retrieved only from its declared GitHub repository and immutable full commit SHA. The Worker verifies the declared SHA-256 before applying an overlay. A source update is a reviewed repository change, never a runtime fetch of a branch such as `main`.

Each entry declares `authentication`: `null` for a skill that needs no service access, or the portable policy from [`docs/authentication-contract.md`](../docs/authentication-contract.md). An authenticated upstream skill's overlay must apply the policy without adding harness-specific onboarding.

See [`docs/catalog-contract.md`](../docs/catalog-contract.md) for the entry and overlay contract.
