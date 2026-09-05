#!/usr/bin/env python3
"""Generate the compact, public index consumed by the read-only MCP Worker."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


INDEX_PATH = Path("catalog/index.json")
SCHEMA_VERSION = "1.0"
UPSTREAMS_DIRECTORY = Path("upstreams")


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def build_index(root: Path) -> dict[str, Any]:
    skills: list[dict[str, Any]] = []
    skills_directory = root / "skills"
    if skills_directory.is_dir():
        for catalog_path in sorted(skills_directory.rglob("catalog.json")):
            relative_catalog_path = catalog_path.relative_to(skills_directory)
            if len(relative_catalog_path.parts) != 3:
                raise ValueError(f"{catalog_path}: catalog sidecar must be located at skills/<category>/<skill-id>/catalog.json")
            catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
            if catalog.get("status") != "published":
                continue
            skill_directory = catalog_path.parent
            skill_path = skill_directory / "SKILL.md"
            if not skill_path.is_file():
                raise ValueError(f"{catalog_path}: published skill has no SKILL.md")
            content = skill_path.read_bytes()
            skills.append(
                {
                    "id": catalog["id"],
                    "directory": skill_directory.relative_to(root).as_posix(),
                    "name": catalog["id"],
                    "description": read_skill_description(skill_path),
                    "version": catalog["version"],
                    "category": catalog["category"],
                    "facets": catalog["facets"],
                    "risk": catalog["risk"],
                    "compatibility": catalog["compatibility"],
                    "origin": {"kind": "local"},
                    "files": [
                        {
                            "path": "SKILL.md",
                            "sha256": sha256(content),
                            "size_bytes": len(content),
                            "content_type": "text/markdown"
                        }
                    ]
                }
            )
    skills.extend(build_upstream_skills(root))
    identifiers = [skill["id"] for skill in skills]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("published local and upstream skills must have unique identifiers")
    return {"schema_version": SCHEMA_VERSION, "skills": skills}


def build_upstream_skills(root: Path) -> list[dict[str, Any]]:
    upstreams_directory = root / UPSTREAMS_DIRECTORY
    if not upstreams_directory.is_dir():
        return []

    skills: list[dict[str, Any]] = []
    for catalog_path in sorted(upstreams_directory.glob("*/catalog.json")):
        entry_directory = catalog_path.parent
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        if catalog.get("status") != "published":
            continue
        identifier = catalog.get("id")
        if not isinstance(identifier, str) or entry_directory.name != identifier:
            raise ValueError(f"{catalog_path}: upstream catalog id must match its directory")
        source = catalog.get("source")
        if not isinstance(source, dict):
            raise ValueError(f"{catalog_path}: upstream catalog source must be an object")
        required_source_keys = {"repository", "commit", "license", "reviewed_at"}
        if set(source) != required_source_keys:
            raise ValueError(f"{catalog_path}: upstream catalog source keys are invalid")
        if not all(isinstance(source.get(key), str) and source[key] for key in required_source_keys):
            raise ValueError(f"{catalog_path}: upstream catalog source values must be non-empty strings")
        if len(source["commit"]) != 40 or any(character not in "0123456789abcdef" for character in source["commit"]):
            raise ValueError(f"{catalog_path}: upstream catalog source commit must be a full lowercase SHA")

        overlay = read_overlay(entry_directory, identifier)
        files = catalog.get("files")
        if not isinstance(files, list) or not files:
            raise ValueError(f"{catalog_path}: upstream catalog files must be a non-empty array")
        index_files: list[dict[str, Any]] = []
        for file in files:
            if not isinstance(file, dict) or set(file) != {"path", "source_path", "sha256", "size_bytes", "content_type"}:
                raise ValueError(f"{catalog_path}: upstream file metadata is invalid")
            if not all(isinstance(file[key], str) and file[key] for key in ("path", "source_path", "sha256", "content_type")):
                raise ValueError(f"{catalog_path}: upstream file string metadata is invalid")
            if not isinstance(file["size_bytes"], int) or file["size_bytes"] < 0:
                raise ValueError(f"{catalog_path}: upstream file size must be a non-negative integer")
            if len(file["sha256"]) != 64 or any(character not in "0123456789abcdef" for character in file["sha256"]):
                raise ValueError(f"{catalog_path}: upstream file SHA-256 is invalid")
            if file["path"].startswith("/") or ".." in Path(file["path"]).parts:
                raise ValueError(f"{catalog_path}: upstream file path is unsafe")
            if file["source_path"].startswith("/") or ".." in Path(file["source_path"]).parts:
                raise ValueError(f"{catalog_path}: upstream source path is unsafe")
            index_files.append(file)
        if not any(file["path"] == "SKILL.md" for file in index_files):
            raise ValueError(f"{catalog_path}: upstream catalog must declare SKILL.md")
        skills.append(
            {
                "id": identifier,
                "directory": entry_directory.relative_to(root).as_posix(),
                "name": identifier,
                "description": required_string(catalog, "description", catalog_path),
                "version": required_string(catalog, "version", catalog_path),
                "category": required_string(catalog, "category", catalog_path),
                "facets": required_string_array(catalog, "facets", catalog_path),
                "risk": required_string(catalog, "risk", catalog_path),
                "compatibility": catalog.get("compatibility", []),
                "origin": {
                    "kind": "upstream",
                    "repository": source["repository"],
                    "commit": source["commit"],
                    "license": source["license"],
                    "reviewed_at": source["reviewed_at"],
                    "overlay": overlay
                },
                "files": index_files
            }
        )
    return skills


def read_overlay(entry_directory: Path, identifier: str) -> list[dict[str, str]]:
    overlay_path = entry_directory / "overlay.json"
    if not overlay_path.is_file():
        return []
    overlay = json.loads(overlay_path.read_text(encoding="utf-8"))
    if not isinstance(overlay, dict) or set(overlay) != {"schema_version", "upstream_id", "operations"}:
        raise ValueError(f"{overlay_path}: overlay keys are invalid")
    if overlay.get("schema_version") != "1.0" or overlay.get("upstream_id") != identifier:
        raise ValueError(f"{overlay_path}: overlay identity is invalid")
    operations = overlay.get("operations")
    if not isinstance(operations, list):
        raise ValueError(f"{overlay_path}: operations must be an array")
    normalized: list[dict[str, str]] = []
    for operation in operations:
        if not isinstance(operation, dict) or operation.get("operation") not in {"append", "replace", "remove"}:
            raise ValueError(f"{overlay_path}: operation type is invalid")
        section = operation.get("section")
        if not isinstance(section, str) or not section.startswith("#") or "\n" in section:
            raise ValueError(f"{overlay_path}: operation section must be a single Markdown heading")
        expected_keys = {"operation", "section"} if operation["operation"] == "remove" else {"operation", "section", "content"}
        if set(operation) != expected_keys:
            raise ValueError(f"{overlay_path}: operation keys are invalid")
        normalized_operation = {"operation": operation["operation"], "section": section}
        if operation["operation"] != "remove":
            content = operation.get("content")
            if not isinstance(content, str) or not content.strip() or len(content.encode("utf-8")) > 32 * 1024:
                raise ValueError(f"{overlay_path}: operation content is invalid")
            normalized_operation["content"] = content
        normalized.append(normalized_operation)
    return normalized


def required_string(catalog: dict[str, Any], key: str, path: Path) -> str:
    value = catalog.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{path}: upstream catalog {key} must be a non-empty string")
    return value


def required_string_array(catalog: dict[str, Any], key: str, path: Path) -> list[str]:
    value = catalog.get(key)
    if not isinstance(value, list) or not value or not all(isinstance(item, str) and item.strip() for item in value):
        raise ValueError(f"{path}: upstream catalog {key} must be a non-empty string array")
    return value


def read_skill_description(skill_path: Path) -> str:
    lines = skill_path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        raise ValueError(f"{skill_path}: invalid frontmatter")
    for line in lines[1:]:
        if line == "---":
            break
        if line.startswith("description:"):
            value = line.partition(":")[2].strip()
            return value.strip("\"'")
    raise ValueError(f"{skill_path}: no description frontmatter")


def serialized_index(index: dict[str, Any]) -> str:
    return json.dumps(index, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the public Agentic Skills MCP index.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--check", action="store_true", help="fail when catalog/index.json is stale")
    arguments = parser.parse_args()
    root = arguments.root.resolve()
    expected = serialized_index(build_index(root))
    index_path = root / INDEX_PATH
    actual = index_path.read_text(encoding="utf-8") if index_path.is_file() else ""
    if arguments.check:
        if actual != expected:
            print("catalog/index.json is stale; run python3 tooling/build_skill_index.py")
            return 1
        print("Skill index is current.")
        return 0
    index_path.write_text(expected, encoding="utf-8")
    print(f"Wrote {index_path.relative_to(root)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
