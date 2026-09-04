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


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def build_index(root: Path) -> dict[str, Any]:
    skills: list[dict[str, Any]] = []
    skills_directory = root / "skills"
    if not skills_directory.is_dir():
        return {"schema_version": SCHEMA_VERSION, "skills": skills}

    for catalog_path in sorted(skills_directory.glob("*/catalog.json")):
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
                "name": catalog["id"],
                "description": read_skill_description(skill_path),
                "version": catalog["version"],
                "category": catalog["category"],
                "facets": catalog["facets"],
                "risk": catalog["risk"],
                "compatibility": catalog["compatibility"],
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
    return {"schema_version": SCHEMA_VERSION, "skills": skills}


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
