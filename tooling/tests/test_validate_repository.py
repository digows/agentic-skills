from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import validate_repository as validator


class ValidateRepositoryTests(unittest.TestCase):
    def test_current_repository_passes_its_contract(self) -> None:
        repository_root = Path(__file__).resolve().parents[2]
        errors = validator.validate_repository(repository_root)
        self.assertEqual([], errors, [error.render(repository_root) for error in errors])

    def test_frontmatter_accepts_portable_required_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "SKILL.md"
            path.write_text(
                "---\nname: example-skill\ndescription: Performs a bounded task.\nmetadata:\n  author: example\n---\n# Example\n",
                encoding="utf-8"
            )
            errors: list[validator.ValidationError] = []
            frontmatter = validator._parse_frontmatter(path, errors)
            self.assertEqual([], errors)
            self.assertEqual("example-skill", frontmatter["name"])
            self.assertEqual("Performs a bounded task.", frontmatter["description"])

    def test_frontmatter_rejects_nonportable_key(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "SKILL.md"
            path.write_text("---\nname: example\nprovider: test\n---\n# Example\n", encoding="utf-8")
            errors: list[validator.ValidationError] = []
            validator._parse_frontmatter(path, errors)
            self.assertTrue(any("unsupported canonical frontmatter key" in error.message for error in errors))

    def test_secret_scanner_flags_github_token_shape(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            path = root / "unsafe.txt"
            path.write_text("ghp_" + "a" * 36, encoding="utf-8")
            errors: list[validator.ValidationError] = []
            validator._validate_secrets(root, errors)
            self.assertTrue(any("GitHub token" in error.message for error in errors))

    def test_workflow_requires_full_sha_pin(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workflow = root / ".github" / "workflows" / "validate.yml"
            workflow.parent.mkdir(parents=True)
            workflow.write_text(
                "on:\n  pull_request:\n  push:\npermissions:\n  contents: read\njobs:\n  test:\n    steps:\n      - uses: actions/checkout@v4\n",
                encoding="utf-8"
            )
            errors: list[validator.ValidationError] = []
            validator._validate_workflows(root, errors)
            self.assertTrue(any("full commit SHA" in error.message for error in errors))

    def test_workflow_accepts_read_only_full_sha_pin(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workflow = root / ".github" / "workflows" / "validate.yml"
            workflow.parent.mkdir(parents=True)
            workflow.write_text(
                "on:\n  pull_request:\n  push:\npermissions:\n  contents: read\njobs:\n  test:\n    steps:\n      - uses: actions/checkout@" + "a" * 40 + "\n",
                encoding="utf-8"
            )
            errors: list[validator.ValidationError] = []
            validator._validate_workflows(root, errors)
            self.assertEqual([], errors)

    def test_unsafe_script_scanner_flags_remote_shell_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            script = root / "skills" / "example" / "scripts" / "unsafe.sh"
            script.parent.mkdir(parents=True)
            script.write_text("curl https://example.invalid/install | sh\n", encoding="utf-8")
            errors: list[validator.ValidationError] = []
            validator._validate_scripts(root, errors)
            self.assertTrue(any("remote content piped to a shell" in error.message for error in errors))

    def test_skill_directory_layout_rejects_flat_skill(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            skill = root / "skills" / "example-skill" / "SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_text("---\nname: example-skill\ndescription: Example.\n---\n# Example\n", encoding="utf-8")
            errors: list[validator.ValidationError] = []
            validator._validate_skill_directory_layout(root, errors)
            self.assertTrue(any("skills/<category>/<skill-id>/SKILL.md" in error.message for error in errors))

    def test_catalog_category_must_match_its_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "skills" / "software-engineering" / "example-skill" / "catalog.json"
            path.parent.mkdir(parents=True)
            path.write_text(
                """{
  "schema_version": "1.0",
  "id": "example-skill",
  "version": "1.0.0",
  "status": "published",
  "category": "infrastructure-and-operations",
  "facets": ["automation"],
  "risk": "low",
  "source": {"upstream": "https://example.com", "reviewed_at": "2026-09-04"},
  "requirements": {"credentials": [], "network_access": false, "tools": []},
  "compatibility": [],
  "evaluations": {"definition": "evals/definition.json", "baseline_report": "baseline", "skill_report": "skill"}
}""",
                encoding="utf-8"
            )
            errors: list[validator.ValidationError] = []
            validator._validate_catalog_sidecar(path, errors)
            self.assertTrue(any("must match the skill category directory" in error.message for error in errors))

    def test_credentials_require_authentication_policy(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "skills" / "software-engineering" / "example-skill" / "catalog.json"
            path.parent.mkdir(parents=True)
            path.write_text(
                """{
  "schema_version": "1.0",
  "id": "example-skill",
  "version": "1.0.0",
  "status": "published",
  "category": "software-engineering",
  "facets": ["automation"],
  "risk": "low",
  "source": {"upstream": "https://example.com", "reviewed_at": "2026-09-05"},
  "requirements": {"credentials": ["api-key"], "network_access": true, "tools": []},
  "api_contract_discovery": {"result": "not-published", "absence_evidence_url": "https://example.com/api"},
  "compatibility": [],
  "evaluations": {"definition": "evals/definition.json", "baseline_report": "baseline", "skill_report": "skill"}
}""",
                encoding="utf-8"
            )
            errors: list[validator.ValidationError] = []
            validator._validate_catalog_sidecar(path, errors)
            self.assertTrue(any("requires authentication metadata" in error.message for error in errors))

    def test_authenticated_skill_requires_authentication_section(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            skill_directory = Path(temporary_directory) / "skills" / "software-engineering" / "example-skill"
            skill_directory.mkdir(parents=True)
            (skill_directory / "SKILL.md").write_text(
                "---\nname: example-skill\ndescription: Example.\n---\n# Example\n",
                encoding="utf-8"
            )
            catalog_path = skill_directory / "catalog.json"
            catalog_path.write_text(
                """{
  "schema_version": "1.0",
  "id": "example-skill",
  "version": "1.0.0",
  "status": "published",
  "category": "software-engineering",
  "facets": ["automation"],
  "risk": "low",
  "source": {"upstream": "https://example.com", "reviewed_at": "2026-09-05"},
  "requirements": {"credentials": ["api-key"], "network_access": true, "tools": []},
  "api_contract_discovery": {"result": "not-published", "absence_evidence_url": "https://example.com/api"},
  "authentication": {"methods": ["api-key"], "target_binding": "exact-target", "prompting": "when-missing-or-invalid", "failure_behavior": "stop"},
  "compatibility": [],
  "evaluations": {"definition": "evals/definition.json", "baseline_report": "baseline", "skill_report": "skill"}
}""",
                encoding="utf-8"
            )
            errors: list[validator.ValidationError] = []
            validator._validate_catalog_sidecar(catalog_path, errors)
            self.assertTrue(any("must contain an '## Authentication' section" in error.message for error in errors))

    def test_networked_skill_requires_upstream_compatibility(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "skills" / "software-engineering" / "example-skill" / "catalog.json"
            path.parent.mkdir(parents=True)
            path.write_text(
                """{
  "schema_version": "1.0",
  "id": "example-skill",
  "version": "1.0.0",
  "status": "published",
  "category": "software-engineering",
  "facets": ["automation"],
  "risk": "low",
  "source": {"upstream": "https://example.com", "reviewed_at": "2026-09-05"},
  "requirements": {"credentials": [], "network_access": true, "tools": []},
  "compatibility": [],
  "evaluations": {"definition": "evals/definition.json", "baseline_report": "baseline", "skill_report": "skill"}
}""",
                encoding="utf-8"
            )
            errors: list[validator.ValidationError] = []
            validator._validate_catalog_sidecar(path, errors)
            self.assertTrue(any("requires upstream_compatibility" in error.message for error in errors))
            self.assertTrue(any("requires api_contract_discovery" in error.message for error in errors))

    def test_draft_networked_skill_can_defer_authentication_and_compatibility_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "skills" / "software-engineering" / "example-skill" / "catalog.json"
            path.parent.mkdir(parents=True)
            path.write_text(
                """{
  "schema_version": "1.0",
  "id": "example-skill",
  "version": "0.1.0",
  "status": "draft",
  "category": "software-engineering",
  "facets": ["automation"],
  "risk": "low",
  "source": {"upstream": "https://example.com", "reviewed_at": "2026-09-05"},
  "requirements": {"credentials": ["api-key"], "network_access": true, "tools": []},
  "api_contract_discovery": {"result": "not-published", "absence_evidence_url": "https://example.com/api"},
  "compatibility": [],
  "evaluations": {"definition": "evals/definition.json", "baseline_report": "pending", "skill_report": "pending"}
}""",
                encoding="utf-8"
            )
            errors: list[validator.ValidationError] = []
            validator._validate_catalog_sidecar(path, errors)
            self.assertFalse(any("requires authentication metadata" in error.message for error in errors))
            self.assertFalse(any("requires upstream_compatibility" in error.message for error in errors))

    def test_api_contract_discovery_requires_official_source_and_absolute_target_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "skills" / "software-engineering" / "example-skill" / "catalog.json"
            path.parent.mkdir(parents=True)
            path.write_text(
                """{
  "schema_version": "1.0",
  "id": "example-skill",
  "version": "0.1.0",
  "status": "draft",
  "category": "software-engineering",
  "facets": ["automation"],
  "risk": "low",
  "source": {"upstream": "https://example.com", "reviewed_at": "2026-09-05"},
  "requirements": {"credentials": [], "network_access": true, "tools": []},
  "api_contract_discovery": {"result": "openapi", "source_url": "http://example.com/openapi.json", "target_path": "openapi.json", "swagger_ui_path": "docs"},
  "upstream_compatibility": {
    "service": "Example API",
    "api_version": "v1",
    "supported_service_versions": ["1.x"],
    "capability_discovery": {"strategy": "published-openapi", "reference": "https://example.com/docs"},
    "evidence": []
  },
  "compatibility": [],
  "evaluations": {"definition": "evals/definition.json", "baseline_report": "pending", "skill_report": "pending"}
}""",
                encoding="utf-8"
            )
            errors: list[validator.ValidationError] = []
            validator._validate_catalog_sidecar(path, errors)
            messages = [error.message for error in errors]
            self.assertIn("catalog api_contract_discovery source_url must be an HTTPS URL", messages)
            self.assertIn("catalog api_contract_discovery target_path must be an absolute target path", messages)
            self.assertIn("catalog api_contract_discovery swagger_ui_path must be an absolute target path", messages)

    def test_upstream_compatibility_requires_passing_evidence_and_skill_section(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            skill_directory = Path(temporary_directory) / "skills" / "software-engineering" / "example-skill"
            skill_directory.mkdir(parents=True)
            (skill_directory / "SKILL.md").write_text(
                "---\nname: example-skill\ndescription: Example.\n---\n# Example\n",
                encoding="utf-8"
            )
            catalog_path = skill_directory / "catalog.json"
            catalog_path.write_text(
                """{
  "schema_version": "1.0",
  "id": "example-skill",
  "version": "1.0.0",
  "status": "published",
  "category": "software-engineering",
  "facets": ["automation"],
  "risk": "low",
  "source": {"upstream": "https://example.com", "reviewed_at": "2026-09-05"},
  "requirements": {"credentials": [], "network_access": true, "tools": []},
  "api_contract_discovery": {"result": "not-published", "absence_evidence_url": "https://example.com/api"},
  "upstream_compatibility": {
    "service": "Example API",
    "api_version": "v1",
    "supported_service_versions": ["1.x"],
    "capability_discovery": {"strategy": "documentation", "reference": "https://example.com/docs"},
    "evidence": [{"service_version": "1.0.0", "api_version": "v1", "verified_at": "2026-09-05", "result": "partial"}]
  },
  "compatibility": [],
  "evaluations": {"definition": "evals/definition.json", "baseline_report": "baseline", "skill_report": "skill"}
}""",
                encoding="utf-8"
            )
            errors: list[validator.ValidationError] = []
            validator._validate_catalog_sidecar(catalog_path, errors)
            self.assertTrue(any("requires at least one passing evidence" in error.message for error in errors))
            self.assertTrue(any("must contain an '## Upstream compatibility' section" in error.message for error in errors))


if __name__ == "__main__":
    unittest.main()
