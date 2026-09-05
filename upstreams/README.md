# Federated upstream skills

An upstream entry references an authoritative skill without copying or forking it. Each entry lives at `upstreams/<skill-id>/catalog.json`; an optional sibling `overlay.json` can append, replace, or remove a named Markdown section from the upstream `SKILL.md`.

Every upstream file is retrieved only from its declared GitHub repository and immutable full commit SHA. The Worker verifies the declared SHA-256 before applying an overlay. A source update is a reviewed repository change, never a runtime fetch of a branch such as `main`.

See [`docs/catalog-contract.md`](../docs/catalog-contract.md) for the entry and overlay contract.
