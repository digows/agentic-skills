#!/usr/bin/env python3
"""Validate portable-skill repository contracts without third-party dependencies."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse


SKILL_IDENTIFIER_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SEMVER_PATTERN = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)
MARKDOWN_LINK_PATTERN = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+[^)]*)?\)")
ACTION_USES_PATTERN = re.compile(r"^\s*(?:-\s*)?uses:\s*([^@\s]+)@([^\s#]+)", re.MULTILINE)
ACTION_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
SECRET_PATTERNS = {
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,255}\b"),
    "GitLab token": re.compile(r"\bglpat-[A-Za-z0-9_-]{20,255}\b"),
    "private key": re.compile(r"-----BEGIN [A-Z ]+ PRIVATE KEY-----"),
    "OpenAI API key": re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")
}
UNSAFE_SCRIPT_PATTERNS = {
    "remote content piped to a shell": re.compile(r"\b(?:curl|wget)\b[^\n|]*\|\s*(?:ba)?sh\b", re.IGNORECASE),
    "privilege escalation": re.compile(r"\bsudo\b"),
    "dynamic shell evaluation": re.compile(r"\beval\s+\$"),
    "world-writable permission": re.compile(r"\bchmod\s+(?:-R\s+)?777\b")
}
ALLOWED_FRONTMATTER_KEYS = {
    "name",
    "description",
    "license",
    "compatibility",
    "metadata",
    "allowed-tools"
}
EXPECTED_PLANNED_IDS = {"n8n", "gitlab", "home-assistant", "mikrotik", "unifi", "rita"}
VALID_CATEGORIES = {
    "software-engineering",
    "data-and-ai",
    "infrastructure-and-operations",
    "security-and-compliance",
    "research-and-knowledge",
    "documents-and-content",
    "product-and-design",
    "business-and-productivity",
    "agent-development"
}
VALID_RISKS = {"low", "moderate", "high", "critical"}


@dataclass(frozen=True)
class ValidationError:
    path: Path
    message: str

    def render(self, root: Path) -> str:
        try:
            display_path = self.path.relative_to(root)
        except ValueError:
            display_path = self.path
        return f"{display_path}: {self.message}"


def _read_json(path: Path, errors: list[ValidationError]) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as exception:
        errors.append(ValidationError(path, f"cannot read file: {exception}"))
    except json.JSONDecodeError as exception:
        errors.append(ValidationError(path, f"invalid JSON: {exception.msg} at line {exception.lineno}"))
    return None


def _is_https_url(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def _is_iso_date(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _validate_required_keys(
    value: Any,
    required_keys: set[str],
    allowed_keys: set[str],
    path: Path,
    context: str,
    errors: list[ValidationError]
) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        errors.append(ValidationError(path, f"{context} must be an object"))
        return None
    missing_keys = sorted(required_keys - value.keys())
    unknown_keys = sorted(value.keys() - allowed_keys)
    if missing_keys:
        errors.append(ValidationError(path, f"{context} is missing keys: {', '.join(missing_keys)}"))
    if unknown_keys:
        errors.append(ValidationError(path, f"{context} has unsupported keys: {', '.join(unknown_keys)}"))
    return value


def _parse_frontmatter(path: Path, errors: list[ValidationError]) -> dict[str, str] | None:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exception:
        errors.append(ValidationError(path, f"cannot read skill: {exception}"))
        return None
    if not lines or lines[0] != "---":
        errors.append(ValidationError(path, "SKILL.md must begin with YAML frontmatter delimiter '---'"))
        return None
    try:
        closing_index = lines.index("---", 1)
    except ValueError:
        errors.append(ValidationError(path, "SKILL.md frontmatter has no closing delimiter"))
        return None
    if not any(line.strip() for line in lines[closing_index + 1:]):
        errors.append(ValidationError(path, "SKILL.md must contain instructions after frontmatter"))

    frontmatter: dict[str, str] = {}
    for line_number, line in enumerate(lines[1:closing_index], start=2):
        if not line.strip() or line.startswith((" ", "\t", "#")):
            continue
        key, separator, raw_value = line.partition(":")
        if not separator or not key.strip():
            errors.append(ValidationError(path, f"invalid frontmatter line {line_number}"))
            continue
        normalized_key = key.strip()
        if normalized_key not in ALLOWED_FRONTMATTER_KEYS:
            errors.append(ValidationError(path, f"unsupported canonical frontmatter key '{normalized_key}'"))
            continue
        value = raw_value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        frontmatter[normalized_key] = value
    return frontmatter


def _validate_skill(path: Path, errors: list[ValidationError]) -> None:
    skill_directory = path.parent
    skill_id = skill_directory.name
    frontmatter = _parse_frontmatter(path, errors)
    if frontmatter is None:
        return
    if not SKILL_IDENTIFIER_PATTERN.fullmatch(skill_id):
        errors.append(ValidationError(path, "skill directory name must be lowercase kebab-case"))
    name = frontmatter.get("name")
    description = frontmatter.get("description")
    if not _is_nonempty_string(name):
        errors.append(ValidationError(path, "frontmatter requires a non-empty name"))
    elif name != skill_id:
        errors.append(ValidationError(path, "frontmatter name must match the skill directory name"))
    if not _is_nonempty_string(description):
        errors.append(ValidationError(path, "frontmatter requires a non-empty description"))
    catalog_path = skill_directory / "catalog.json"
    evaluation_path = skill_directory / "evals" / "definition.json"
    if not catalog_path.is_file():
        errors.append(ValidationError(path, "published skill requires catalog.json"))
    if not evaluation_path.is_file():
        errors.append(ValidationError(path, "published skill requires evals/definition.json"))


def _validate_catalog_sidecar(path: Path, errors: list[ValidationError]) -> None:
    catalog = _read_json(path, errors)
    if catalog is None:
        return
    required_keys = {
        "schema_version", "id", "version", "status", "category", "facets", "risk", "source",
        "requirements", "compatibility", "evaluations"
    }
    allowed_keys = required_keys | {"authentication"}
    catalog = _validate_required_keys(catalog, required_keys, allowed_keys, path, "catalog", errors)
    if catalog is None:
        return
    if catalog.get("schema_version") != "1.0":
        errors.append(ValidationError(path, "catalog schema_version must be '1.0'"))
    skill_id = path.parent.name
    if catalog.get("id") != skill_id:
        errors.append(ValidationError(path, "catalog id must match the skill directory name"))
    if not isinstance(catalog.get("version"), str) or not SEMVER_PATTERN.fullmatch(catalog["version"]):
        errors.append(ValidationError(path, "catalog version must be semantic versioning"))
    if catalog.get("status") not in {"draft", "published", "deprecated"}:
        errors.append(ValidationError(path, "catalog status is invalid"))
    if catalog.get("category") not in VALID_CATEGORIES:
        errors.append(ValidationError(path, "catalog category is not in catalog/taxonomy.json"))
    elif path.parent.parent.name != catalog["category"]:
        errors.append(ValidationError(path, "catalog category must match the skill category directory"))
    facets = catalog.get("facets")
    if not isinstance(facets, list) or not facets or not all(_is_nonempty_string(item) for item in facets):
        errors.append(ValidationError(path, "catalog facets must be a non-empty string array"))
    elif len(set(facets)) != len(facets):
        errors.append(ValidationError(path, "catalog facets must be unique"))
    if catalog.get("risk") not in VALID_RISKS:
        errors.append(ValidationError(path, "catalog risk is invalid"))

    source = _validate_required_keys(
        catalog.get("source"), {"upstream", "reviewed_at"}, {"upstream", "reviewed_at"}, path, "catalog source", errors
    )
    if source is not None:
        if not _is_https_url(source.get("upstream")):
            errors.append(ValidationError(path, "catalog source upstream must be an HTTPS URL"))
        if not _is_iso_date(source.get("reviewed_at")):
            errors.append(ValidationError(path, "catalog source reviewed_at must be an ISO date"))

    requirements = _validate_required_keys(
        catalog.get("requirements"), {"credentials", "network_access", "tools"},
        {"credentials", "network_access", "tools"}, path, "catalog requirements", errors
    )
    if requirements is not None:
        if not isinstance(requirements.get("credentials"), list) or not all(
            _is_nonempty_string(item) for item in requirements["credentials"]
        ):
            errors.append(ValidationError(path, "catalog requirements credentials must be a string array"))
        if not isinstance(requirements.get("network_access"), bool):
            errors.append(ValidationError(path, "catalog requirements network_access must be boolean"))
        if not isinstance(requirements.get("tools"), list) or not all(
            _is_nonempty_string(item) for item in requirements["tools"]
        ):
            errors.append(ValidationError(path, "catalog requirements tools must be a string array"))

    authentication = catalog.get("authentication")
    credentials = requirements.get("credentials") if requirements is not None else None
    if isinstance(credentials, list) and credentials and authentication is None:
        errors.append(ValidationError(path, "catalog requires authentication metadata when credentials are declared"))
    if authentication is not None:
        authentication = _validate_required_keys(
            authentication,
            {"methods", "target_binding", "prompting", "failure_behavior"},
            {"methods", "target_binding", "prompting", "failure_behavior"},
            path,
            "catalog authentication",
            errors
        )
        if authentication is not None:
            methods = authentication.get("methods")
            if not isinstance(methods, list) or not methods or not all(_is_nonempty_string(method) for method in methods):
                errors.append(ValidationError(path, "catalog authentication methods must be a non-empty string array"))
            elif len(methods) != len(set(methods)):
                errors.append(ValidationError(path, "catalog authentication methods must be unique"))
            if authentication.get("target_binding") != "exact-target":
                errors.append(ValidationError(path, "catalog authentication target_binding must be 'exact-target'"))
            if authentication.get("prompting") != "when-missing-or-invalid":
                errors.append(ValidationError(path, "catalog authentication prompting must be 'when-missing-or-invalid'"))
            if authentication.get("failure_behavior") != "stop":
                errors.append(ValidationError(path, "catalog authentication failure_behavior must be 'stop'"))
    if isinstance(credentials, list) and credentials:
        skill_path = path.parent / "SKILL.md"
        if skill_path.is_file() and not re.search(r"^## Authentication\\s*$", skill_path.read_text(encoding="utf-8"), re.MULTILINE):
            errors.append(ValidationError(skill_path, "authenticated skill must contain an '## Authentication' section"))

    compatibility = catalog.get("compatibility")
    if not isinstance(compatibility, list):
        errors.append(ValidationError(path, "catalog compatibility must be an array"))
    else:
        for index, evidence in enumerate(compatibility):
            evidence_context = f"catalog compatibility[{index}]"
            evidence = _validate_required_keys(
                evidence, {"harness", "version", "verified_at", "result"},
                {"harness", "version", "verified_at", "result"}, path, evidence_context, errors
            )
            if evidence is None:
                continue
            if not _is_nonempty_string(evidence.get("harness")) or not _is_nonempty_string(evidence.get("version")):
                errors.append(ValidationError(path, f"{evidence_context} harness and version must be non-empty strings"))
            if not _is_iso_date(evidence.get("verified_at")):
                errors.append(ValidationError(path, f"{evidence_context} verified_at must be an ISO date"))
            if evidence.get("result") not in {"pass", "partial", "fail"}:
                errors.append(ValidationError(path, f"{evidence_context} result is invalid"))

    evaluations = _validate_required_keys(
        catalog.get("evaluations"), {"definition", "baseline_report", "skill_report"},
        {"definition", "baseline_report", "skill_report"}, path, "catalog evaluations", errors
    )
    if evaluations is not None:
        definition = evaluations.get("definition")
        if not isinstance(definition, str) or not re.fullmatch(r"evals/.+\.json", definition):
            errors.append(ValidationError(path, "catalog evaluations definition must point to evals/*.json"))
        elif not (path.parent / definition).is_file():
            errors.append(ValidationError(path, "catalog evaluations definition does not exist"))
        for report_name in ("baseline_report", "skill_report"):
            if not _is_nonempty_string(evaluations.get(report_name)):
                errors.append(ValidationError(path, f"catalog evaluations {report_name} must be non-empty"))


def _validate_evaluation_definition(path: Path, errors: list[ValidationError]) -> None:
    definition = _read_json(path, errors)
    if definition is None:
        return
    definition = _validate_required_keys(
        definition, {"schema_version", "skill_id", "cases"}, {"schema_version", "skill_id", "cases"},
        path, "evaluation definition", errors
    )
    if definition is None:
        return
    if definition.get("schema_version") != "1.0":
        errors.append(ValidationError(path, "evaluation schema_version must be '1.0'"))
    if definition.get("skill_id") != path.parents[1].name:
        errors.append(ValidationError(path, "evaluation skill_id must match the skill directory name"))
    cases = definition.get("cases")
    if not isinstance(cases, list) or not cases:
        errors.append(ValidationError(path, "evaluation cases must be a non-empty array"))
        return
    case_ids: set[str] = set()
    for index, case in enumerate(cases):
        context = f"evaluation case {index}"
        case = _validate_required_keys(
            case, {"id", "prompt", "kind", "expected_outcome", "human_review_required"},
            {"id", "prompt", "kind", "expected_outcome", "human_review_required", "tags"}, path, context, errors
        )
        if case is None:
            continue
        case_id = case.get("id")
        if not isinstance(case_id, str) or not SKILL_IDENTIFIER_PATTERN.fullmatch(case_id):
            errors.append(ValidationError(path, f"{context} id must be lowercase kebab-case"))
        elif case_id in case_ids:
            errors.append(ValidationError(path, f"{context} id must be unique"))
        else:
            case_ids.add(case_id)
        if not _is_nonempty_string(case.get("prompt")) or not _is_nonempty_string(case.get("expected_outcome")):
            errors.append(ValidationError(path, f"{context} prompt and expected_outcome must be non-empty strings"))
        if case.get("kind") not in {"success", "failure", "regression", "selection"}:
            errors.append(ValidationError(path, f"{context} kind is invalid"))
        if not isinstance(case.get("human_review_required"), bool):
            errors.append(ValidationError(path, f"{context} human_review_required must be boolean"))
        tags = case.get("tags", [])
        if not isinstance(tags, list) or not all(_is_nonempty_string(item) for item in tags):
            errors.append(ValidationError(path, f"{context} tags must be a string array"))
        elif len(tags) != len(set(tags)):
            errors.append(ValidationError(path, f"{context} tags must be unique"))


def _validate_planned_skills(path: Path, errors: list[ValidationError]) -> None:
    registry = _read_json(path, errors)
    if registry is None:
        return
    registry = _validate_required_keys(registry, {"schema_version", "items"}, {"schema_version", "items"}, path, "planned registry", errors)
    if registry is None:
        return
    if registry.get("schema_version") != "1.0":
        errors.append(ValidationError(path, "planned registry schema_version must be '1.0'"))
    items = registry.get("items")
    if not isinstance(items, list):
        errors.append(ValidationError(path, "planned registry items must be an array"))
        return
    found_ids: set[str] = set()
    for index, item in enumerate(items):
        context = f"planned registry item {index}"
        item = _validate_required_keys(
            item, {"id", "title", "status", "category", "facets", "risk", "upstream", "scope"},
            {"id", "title", "status", "category", "facets", "risk", "upstream", "scope"}, path, context, errors
        )
        if item is None:
            continue
        identifier = item.get("id")
        if not isinstance(identifier, str) or not SKILL_IDENTIFIER_PATTERN.fullmatch(identifier):
            errors.append(ValidationError(path, f"{context} id must be lowercase kebab-case"))
        elif identifier in found_ids:
            errors.append(ValidationError(path, f"{context} id must be unique"))
        else:
            found_ids.add(identifier)
        if not _is_nonempty_string(item.get("title")) or not _is_nonempty_string(item.get("scope")):
            errors.append(ValidationError(path, f"{context} title and scope must be non-empty strings"))
        if item.get("status") != "planned":
            errors.append(ValidationError(path, f"{context} status must be 'planned'"))
        if item.get("category") not in VALID_CATEGORIES:
            errors.append(ValidationError(path, f"{context} category is invalid"))
        facets = item.get("facets")
        if not isinstance(facets, list) or not facets or not all(_is_nonempty_string(facet) for facet in facets):
            errors.append(ValidationError(path, f"{context} facets must be a non-empty string array"))
        if item.get("risk") not in VALID_RISKS:
            errors.append(ValidationError(path, f"{context} risk is invalid"))
        if not _is_https_url(item.get("upstream")):
            errors.append(ValidationError(path, f"{context} upstream must be an HTTPS URL"))
    if found_ids != EXPECTED_PLANNED_IDS:
        errors.append(
            ValidationError(path, f"planned registry ids must be exactly: {', '.join(sorted(EXPECTED_PLANNED_IDS))}")
        )


def _validate_taxonomy(path: Path, errors: list[ValidationError]) -> None:
    taxonomy = _read_json(path, errors)
    if taxonomy is None:
        return
    taxonomy = _validate_required_keys(taxonomy, {"schema_version", "categories", "facet_types"},
        {"schema_version", "categories", "facet_types"}, path, "taxonomy", errors)
    if taxonomy is None:
        return
    if taxonomy.get("schema_version") != "1.0":
        errors.append(ValidationError(path, "taxonomy schema_version must be '1.0'"))
    categories = taxonomy.get("categories")
    if not isinstance(categories, list) or set(categories) != VALID_CATEGORIES:
        errors.append(ValidationError(path, "taxonomy categories must match the supported category set"))
    facets = taxonomy.get("facet_types")
    if not isinstance(facets, dict) or set(facets) != {"capability", "execution", "side_effect"}:
        errors.append(ValidationError(path, "taxonomy must define capability, execution, and side_effect facets"))


def _validate_schema_documents(root: Path, errors: list[ValidationError]) -> None:
    for schema_name in ("catalog.schema.json", "evaluation.schema.json"):
        path = root / "schemas" / schema_name
        schema = _read_json(path, errors)
        if not isinstance(schema, dict):
            continue
        if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            errors.append(ValidationError(path, "schema must declare JSON Schema draft 2020-12"))
        if not _is_https_url(schema.get("$id")):
            errors.append(ValidationError(path, "schema must declare an HTTPS $id"))
        if schema.get("type") != "object":
            errors.append(ValidationError(path, "top-level schema type must be object"))
        if not isinstance(schema.get("required"), list) or not schema["required"]:
            errors.append(ValidationError(path, "schema must define non-empty required fields"))


def _iter_text_files(root: Path) -> Iterable[Path]:
    ignored_directories = {".git", ".pytest_cache", ".wrangler", "__pycache__", "node_modules"}
    for path in root.rglob("*"):
        if not path.is_file() or any(part in ignored_directories for part in path.parts):
            continue
        try:
            if b"\0" not in path.read_bytes()[:8192]:
                yield path
        except OSError:
            continue


def _validate_secrets(root: Path, errors: list[ValidationError]) -> None:
    for path in _iter_text_files(root):
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for secret_name, pattern in SECRET_PATTERNS.items():
            if pattern.search(content):
                errors.append(ValidationError(path, f"possible {secret_name} detected"))


def _validate_scripts(root: Path, errors: list[ValidationError]) -> None:
    for path in _iter_text_files(root):
        if "scripts" not in path.parts:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern_name, pattern in UNSAFE_SCRIPT_PATTERNS.items():
            if pattern.search(content):
                errors.append(ValidationError(path, f"unsafe script pattern detected: {pattern_name}"))


def _validate_links(root: Path, errors: list[ValidationError]) -> None:
    for path in root.rglob("*.md"):
        if ".git" in path.parts or "node_modules" in path.parts:
            continue
        content = path.read_text(encoding="utf-8")
        for target in MARKDOWN_LINK_PATTERN.findall(content):
            if target.startswith(("#", "http://", "https://", "mailto:")):
                continue
            target_path = target.split("#", 1)[0]
            if not target_path:
                continue
            resolved_path = (path.parent / target_path).resolve()
            try:
                resolved_path.relative_to(root.resolve())
            except ValueError:
                errors.append(ValidationError(path, f"link escapes repository: {target}"))
                continue
            if not resolved_path.exists():
                errors.append(ValidationError(path, f"broken relative link: {target}"))


def _validate_workflows(root: Path, errors: list[ValidationError]) -> None:
    workflows_directory = root / ".github" / "workflows"
    validate_workflow = workflows_directory / "validate.yml"
    if not validate_workflow.is_file():
        errors.append(ValidationError(validate_workflow, "missing validation workflow"))
        return
    for path in sorted(workflows_directory.glob("*.y*ml")):
        content = path.read_text(encoding="utf-8")
        if "pull_request_target:" in content:
            errors.append(ValidationError(path, "pull_request_target is forbidden"))
        if re.search(r"\b(?:secrets|github\.token)\b", content, re.IGNORECASE):
            errors.append(ValidationError(path, "workflow must not access secrets or github.token"))
        if re.search(r"^\s*[^#\n]+:\s*write\s*$", content, re.MULTILINE):
            errors.append(ValidationError(path, "workflow must not request write permissions"))
        for action, revision in ACTION_USES_PATTERN.findall(content):
            if action.startswith("./"):
                continue
            if not ACTION_SHA_PATTERN.fullmatch(revision):
                errors.append(ValidationError(path, f"action must be pinned to a full commit SHA: {action}@{revision}"))
        if path == validate_workflow:
            if not re.search(r"^\s*contents:\s*read\s*$", content, re.MULTILINE):
                errors.append(ValidationError(path, "validation workflow requires contents: read permission"))
            if "pull_request:" not in content or "push:" not in content:
                errors.append(ValidationError(path, "validation workflow must run for pull requests and pushes"))


def _validate_skill_directory_layout(root: Path, errors: list[ValidationError]) -> None:
    skills_directory = root / "skills"
    if not skills_directory.is_dir():
        return
    for category_directory in sorted(skills_directory.iterdir()):
        if category_directory.name == "README.md":
            continue
        if not category_directory.is_dir():
            errors.append(ValidationError(category_directory, "skills directory may contain only category directories and README.md"))
            continue
        if category_directory.name not in VALID_CATEGORIES:
            errors.append(ValidationError(category_directory, "skill category directory is not in catalog/taxonomy.json"))
            continue
        for skill_directory in sorted(category_directory.iterdir()):
            if skill_directory.name == "README.md":
                continue
            if not skill_directory.is_dir():
                errors.append(ValidationError(skill_directory, "category directory may contain only skill directories and README.md"))
                continue
            if not SKILL_IDENTIFIER_PATTERN.fullmatch(skill_directory.name):
                errors.append(ValidationError(skill_directory, "skill directory name must be lowercase kebab-case"))

    for skill_path in sorted(skills_directory.glob("*/SKILL.md")):
        errors.append(ValidationError(skill_path, "skill must be located at skills/<category>/<skill-id>/SKILL.md"))
    for catalog_path in sorted(skills_directory.rglob("catalog.json")):
        if len(catalog_path.relative_to(skills_directory).parts) != 3:
            errors.append(ValidationError(catalog_path, "catalog sidecar must be located at skills/<category>/<skill-id>/catalog.json"))


def validate_repository(root: Path) -> list[ValidationError]:
    root = root.resolve()
    errors: list[ValidationError] = []
    required_files = [
        root / "README.md",
        root / "CONTRIBUTING.md",
        root / "SECURITY.md",
        root / "CODE_OF_CONDUCT.md",
        root / "schemas" / "catalog.schema.json",
        root / "schemas" / "evaluation.schema.json",
        root / "catalog" / "taxonomy.json",
        root / "catalog" / "planned-skills.json",
        root / "catalog" / "index.json",
        root / "services" / "skills-mcp" / "package-lock.json"
    ]
    for path in required_files:
        if not path.is_file():
            errors.append(ValidationError(path, "required repository file is missing"))
    if errors:
        return errors

    _validate_schema_documents(root, errors)
    _validate_taxonomy(root / "catalog" / "taxonomy.json", errors)
    _validate_planned_skills(root / "catalog" / "planned-skills.json", errors)
    _validate_skill_directory_layout(root, errors)
    for skill_path in sorted((root / "skills").glob("*/*/SKILL.md")) if (root / "skills").is_dir() else []:
        _validate_skill(skill_path, errors)
    for catalog_path in sorted((root / "skills").glob("*/*/catalog.json")) if (root / "skills").is_dir() else []:
        _validate_catalog_sidecar(catalog_path, errors)
    for evaluation_path in sorted((root / "skills").glob("*/*/evals/*.json")) if (root / "skills").is_dir() else []:
        _validate_evaluation_definition(evaluation_path, errors)
    _validate_links(root, errors)
    _validate_secrets(root, errors)
    _validate_scripts(root, errors)
    _validate_workflows(root, errors)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Agentic Skills repository contracts and policy.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1], help="repository root")
    arguments = parser.parse_args()
    errors = validate_repository(arguments.root)
    if errors:
        for error in errors:
            print(f"ERROR: {error.render(arguments.root.resolve())}")
        return 1
    print("Repository validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
