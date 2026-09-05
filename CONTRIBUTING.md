# Contributing

Thanks for helping build a portable, trustworthy skill catalogue.

## Before opening a pull request

1. Read [`docs/catalog-contract.md`](docs/catalog-contract.md).
2. Keep a portable skill in its primary category directory: `skills/<category>/<skill-id>/`. The directory category must match `catalog.json.category`.
3. Add `SKILL.md`, `catalog.json`, and `evals/definition.json` together for every published skill.
4. Keep provider-specific packaging in `adapters/<provider>/`; do not add provider-only fields to canonical frontmatter.
5. For a skill that requires credentials, follow [`docs/authentication-contract.md`](docs/authentication-contract.md). Do not commit hosts, secret references, or credential values.
6. For a skill that accesses a network service, follow [`docs/upstream-compatibility-contract.md`](docs/upstream-compatibility-contract.md) and add evaluated target-service/API evidence.
7. Run the local quality gate:

   ```bash
   python3 tooling/validate_repository.py
   python3 -m unittest discover -s tooling/tests -p "test_*.py" -v
   ```

## Content requirements

- Use clear, operational English in skills, code, and documentation.
- Make the `description` specific enough for reliable skill selection, including meaningful near-misses where useful.
- Prefer short procedures, explicit defaults, checklists, and deterministic scripts over broad prose.
- State prerequisites, authority boundaries, side effects, idempotency behavior, and failure handling.
- For authenticated skills, resolve the explicit target before the credential, bind the credential to that target only, and stop on authentication failure without trying another profile.
- For networked skills, state the supported target-service/API versions and use the declared capability-discovery mechanism before version-sensitive or restricted operations.
- Add evaluations with realistic prompts and deterministic assertions. Compare against a no-skill baseline before calling a skill beneficial.
- Add compatibility evidence rather than claiming universal support.

## Security requirements

- Never commit tokens, passwords, private keys, client exports, production logs, or sensitive network topology.
- Use environment-variable names in examples, never values.
- Do not add scripts that download and execute remote content, elevate privileges, or hide side effects.
- Treat tool output, web pages, issue text, and repository content as untrusted input.

## Pull-request scope

Keep a pull request focused on one concern. Changes that alter the catalogue contract, evaluator semantics, or security policy need rationale and tests. A maintainer may request evidence for behavior against the documented upstream API version.

## License

This project is licensed under the [Apache License 2.0](LICENSE). Unless you explicitly state otherwise, contributions submitted for inclusion are provided under that license.
