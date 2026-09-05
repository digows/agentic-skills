# Authoring Agent Skills

This is the single execution guide for an agent creating, changing, or publishing a skill in this catalogue. Read it before creating files or proposing an implementation. The normative details linked from this guide remain authoritative when they conflict with a summary here.

## Operating model

The catalogue distributes portable instructions, not service credentials or provider-specific setup. Its public MCP server is read-only and resolves the catalogue from GitHub `main` at runtime. A merge that changes skill content, metadata, an upstream pin, or an overlay becomes available after the Worker cache refreshes (at most five minutes). Deploy the Worker only when changing its code or the MCP/catalogue protocol.

Canonical skills must work independently of a model, agent harness, or provider. Provider packaging may exist under `adapters/<provider>/`, but it must not change the canonical `SKILL.md` contract.

## Decision tree

Follow this order. Do not start by writing a new `SKILL.md`.

```text
New capability request
  |
  +-- Is there a maintained official skill that already owns the procedure?
  |     |
  |     +-- Yes: federate that exact skill from an immutable upstream commit.
  |     |          Add an overlay only for a reviewed, portable complement.
  |     |
  |     +-- No: create a local portable skill.
  |
  +-- Does it call a network service?
  |     |
  |     +-- Yes: find the official machine-readable API contract before writing instructions.
  |
  +-- Does it require credentials?
  |     |
  |     +-- Yes: apply the target-bound authentication and clipboard onboarding contract.
  |
  +-- Define category, risk, evidence, evaluation cases, and publication boundary.
  |
  +-- Build the index, validate, test, and open a focused pull request.
```

## 1. Research before authoring

Record facts, not assumptions. For an external service, establish all of the following before authoring:

1. The official maintainer, repository, license, and current immutable revision of any existing skill.
2. The official OpenAPI or other machine-readable contract. Prefer the selected target's contract at runtime when it publishes one.
3. The documented authentication methods, version boundaries, capability-discovery mechanism, and destructive or externally visible effects.
4. Whether an official MCP server, CLI, or native integration covers the task. Prefer it for the operation it actually exposes; do not claim it covers adjacent API operations without evidence.

Do not derive endpoints from browser traffic, copied endpoint lists, another tenant, or a UI. Do not treat an upstream branch, release alias, or documentation example as an immutable source.

For a networked local skill, record OpenAPI discovery in `catalog.json` according to [`upstream-compatibility-contract.md`](upstream-compatibility-contract.md). If no official OpenAPI exists, record official evidence of that absence instead.

## 2. Choose the ownership model

### Federated official skill

Use an upstream entry when the upstream maintainer already owns the core procedure. Do not copy or fork the source merely to make it discoverable here.

```text
upstreams/<skill-id>/
  catalog.json       # upstream repository, full commit SHA, license, file digests
  overlay.json       # optional local section-level supplement
```

The entry must declare every downloadable file, including each direct reference that the upstream `SKILL.md` tells an agent to read. Pin the repository, a full 40-character commit SHA, and a SHA-256 for every declared file. A source update is a reviewed catalogue change that moves the pin; never fetch an upstream branch dynamically.

The current Worker retrieves federated content only from GitHub through `raw.githubusercontent.com`; upstream `source.repository` is therefore an `owner/repository` GitHub identifier. Do not add a GitLab.com, registry, or arbitrary-URL source as a workaround. Supporting another forge is a Worker and catalogue-protocol change, with an explicit resolver, allowed-origin policy, immutable revision handling, digest verification, tests, and deployment.

Use `overlay.json` only for a specific portable addition, replacement, or removal of an exact Markdown heading. `append`, `replace`, and `remove` are applied in order. An absent or ambiguous heading is a failure, not a reason to patch loosely. An overlay cannot alter provenance, grant harness permissions, execute upstream scripts, or add organization-specific setup.

An upstream entry declares `authentication` as either `null` or the portable policy. If it requires access, its resolved content must operationalize the authentication policy, normally through an overlay.

### Local portable skill

Create a local skill only when no suitable official source exists or when the local procedure is genuinely independent and reusable.

```text
skills/<category>/<skill-id>/
  SKILL.md
  catalog.json
  evals/
    definition.json
  adapters/<provider>/       # optional and non-canonical
```

The directory category, directory identifier, `catalog.json.id`, and `SKILL.md` frontmatter `name` must agree. Use lowercase kebab-case identifiers. Choose one stable primary category from [`catalog/taxonomy.json`](../catalog/taxonomy.json); use facets for capability, execution context, and side effect instead of creating deeper category trees.

## 3. Write the canonical procedure

Write in concise operational English. The description must make the skill selectable by task and clarify meaningful near-misses. Keep the canonical frontmatter portable: `name`, `description`, and the supported Agent Skills fields only.

Every skill must state:

- when to use it and when not to use it;
- prerequisites and authority boundaries;
- read, write, destructive, publication, and user-visible effects;
- idempotency and verification steps where they matter;
- expected failure behavior and a stop condition for unsupported operations.

Use progressive disclosure. Keep the primary procedure short; declare reference files for detailed, conditional material. Prefer an upstream native MCP/CLI integration when available for an operation, then use the documented API fallback only if the selected target supports it.

Never include private hosts, secrets, secret paths, customer data, production exports, or provider-specific configuration in canonical content.

## 4. Authentication and first use

Apply the full [`authentication-contract.md`](authentication-contract.md) to every authenticated skill. The portable interaction is fixed:

1. Resolve the explicit target first.
2. Reuse a valid local profile bound to that exact target without prompting.
3. If no usable profile exists for an API key, ask exactly: `Copy the API key to your system clipboard, then reply ready.`
4. Only after that explicit reply, read the clipboard once if the harness exposes that capability; persist the value in the target-bound local profile and use it for the requested operation.
5. If clipboard reading is unavailable, state that in one sentence and ask the user to register the same target-bound profile through the harness's normal local credential mechanism. Do not provide per-provider setup guides in the canonical skill.
6. On `401` or `403`, stop. Do not try a credential from another target. Request setup or reauthorization only when the selected profile is absent, unavailable, or rejected.

The mapping is always:

```text
explicit target -> credential reference -> credential value at execution time
```

The MCP server never receives, stores, or validates these values. `catalog.json.authentication.onboarding` must be `clipboard-when-available`; repository validation enforces it.

## 5. Network APIs, versioning, and compatibility

For a local networked skill, use the target's selected OpenAPI contract before a version-sensitive, optional, restricted, or mutation request. Record:

- the official contract source URL;
- the target-relative OpenAPI and optional interactive-documentation paths;
- supported service/API versions;
- a concrete capability-discovery strategy; and
- evaluated evidence for every published compatibility claim.

Treat a service version as a selection boundary, not proof that every operation exists. Use the declared discovery mechanism and stop when an operation is unsupported. Do not hard-code pagination, request fields, or endpoints that the current target contract does not support.

Version a local skill with semantic versioning. Split a skill only when an upstream major version changes the procedure, safety boundary, or authentication model materially. For an upstream skill, preserve the upstream commit in provenance; update it only through a reviewed change that refreshes all affected file digests and overlays.

## 6. Metadata, risk, and evaluation

`catalog.json` is not optional governance decoration. It is the discovery, provenance, and evidence record. Declare a realistic risk level:

| Risk | Use when |
| --- | --- |
| `low` | Read-only or local work without sensitive inputs. |
| `moderate` | Bounded change or non-sensitive service data. |
| `high` | Credentials, external writes, infrastructure control, or sensitive operations. |
| `critical` | Privileged access, destructive actions, or broad production impact. |

High- and critical-risk skills need explicit authority checks, a dry-run or confirmation boundary where feasible, and evaluation cases for unsafe or denied requests. Every local published skill requires `evals/definition.json`; measure a no-skill baseline and retain report references before claiming a benefit.

## 7. Validate and publish

Before opening a pull request, run the complete local gate from the repository root:

```bash
python3 tooling/build_skill_index.py --check
python3 tooling/validate_repository.py
python3 -m unittest discover -s tooling/tests -p "test_*.py" -v
npm --prefix services/skills-mcp run check
git diff --check
```

Run `python3 tooling/build_skill_index.py` first whenever a published skill, upstream manifest, overlay, or its metadata changes. Include the generated `catalog/index.json` in the pull request.

Keep the pull request focused. State the official evidence, ownership decision (upstream or local), authentication and API-contract decision, risk, evaluation result, and every externally visible effect. Merge to `main` publishes catalogue data; Worker deployment is not part of normal skill publication.

## Non-negotiable anti-patterns

- Creating a local duplicate of an official skill instead of federating it.
- Fetching or referencing mutable upstream branches at runtime.
- Inventing API routes, fields, versions, pagination behavior, or MCP capabilities.
- Placing credentials, private target inventories, or secret-manager paths in the repository.
- Selecting a credential before selecting the target, or retrying another profile after authentication failure.
- Adding provider-specific credential onboarding to portable content.
- Publishing a planned or untested capability as an available skill.
- Modifying the Worker just to add or update skill content.

## Related contracts and examples

- [`catalog-contract.md`](catalog-contract.md): portable skill, upstream, overlay, risk, and evaluation requirements.
- [`authentication-contract.md`](authentication-contract.md): target-bound profiles and clipboard-first onboarding.
- [`upstream-compatibility-contract.md`](upstream-compatibility-contract.md): OpenAPI, capability discovery, versions, and evidence.
- [`../upstreams/n8n-workflows`](../upstreams/n8n-workflows): a federated official skill with declared references and a minimal Public API overlay.
- [`../CONTRIBUTING.md`](../CONTRIBUTING.md): pull-request and repository contribution requirements.
