---
id: 17c1b11e-51bf-4779-b373-4a28a7e9f51b
title: Agent Skills Foundation
status: in_progress
---
# Goal

Establish a public, provider-agnostic Agent Skills repository before publishing domain skills.

# Scope

Create the canonical skill layout; catalogue and evaluation schemas; local validation and security checks; GitHub Actions gates; contribution, issue, pull-request, and security reporting guidance; and placeholders for n8n, GitLab, Home Assistant, MikroTik, UniFi, and RITA.

# Constraints

- Canonical skills remain compliant with the open Agent Skills format.
- Provider-specific behavior stays outside canonical SKILL.md files.
- CI runs without repository secrets, default write privileges, or unpinned actions.
- No domain skill is published until the foundation gates pass.

# Acceptance criteria

- Repository documentation explains layout, compatibility model, local checks, and contribution flow.
- JSON Schemas validate the catalogue sidecar and evaluation definitions.
- Local tooling validates Agent Skills frontmatter, schema conformance, links, forbidden secret patterns, and unsafe script patterns.
- CI executes the same checks on pull requests and main, with least-privilege permissions and pinned action references.
- Pull requests and issues have structured templates; security reports have a private reporting path.
- The named future domains are represented as intentional placeholders, not empty or invalid skills.
- The full local gate passes from a clean checkout without credentials.
