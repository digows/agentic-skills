from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import build_skill_index


class BuildSkillIndexTests(unittest.TestCase):
    def test_published_skill_includes_its_canonical_category_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            skill_directory = root / "skills" / "software-engineering" / "example-skill"
            skill_directory.mkdir(parents=True)
            (skill_directory / "SKILL.md").write_text(
                "---\nname: example-skill\ndescription: Performs an example task.\n---\n# Example\n",
                encoding="utf-8"
            )
            (skill_directory / "catalog.json").write_text(
                '{"id":"example-skill","status":"published","version":"1.0.0","category":"software-engineering","facets":["automation"],"risk":"low","compatibility":[]}',
                encoding="utf-8"
            )

            index = build_skill_index.build_index(root)

            self.assertEqual("skills/software-engineering/example-skill", index["skills"][0]["directory"])

    def test_rejects_catalog_outside_the_category_skill_layout(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            catalog_path = root / "skills" / "example-skill" / "catalog.json"
            catalog_path.parent.mkdir(parents=True)
            catalog_path.write_text("{}", encoding="utf-8")

            with self.assertRaises(ValueError):
                build_skill_index.build_index(root)

    def test_published_upstream_skill_preserves_its_immutable_origin_and_overlay(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            entry_directory = root / "upstreams" / "example-official"
            entry_directory.mkdir(parents=True)
            (entry_directory / "catalog.json").write_text(
                """{
  "schema_version": "1.0",
  "id": "example-official",
  "version": "1.2.3",
  "status": "published",
  "category": "software-engineering",
  "facets": ["automation"],
  "risk": "moderate",
  "description": "Uses the official example skill.",
  "source": {"repository": "example/official-skills", "commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "license": "Apache-2.0", "reviewed_at": "2026-09-05"},
  "files": [{"path": "SKILL.md", "source_path": "skills/example/SKILL.md", "sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", "size_bytes": 123, "content_type": "text/markdown"}],
  "compatibility": []
}""",
                encoding="utf-8"
            )
            (entry_directory / "overlay.json").write_text(
                """{
  "schema_version": "1.0",
  "upstream_id": "example-official",
  "operations": [{"operation": "append", "section": "## Safety", "content": "Use the local policy."}]
}""",
                encoding="utf-8"
            )

            index = build_skill_index.build_index(root)

            skill = index["skills"][0]
            self.assertEqual("upstream", skill["origin"]["kind"])
            self.assertEqual("example/official-skills", skill["origin"]["repository"])
            self.assertEqual("append", skill["origin"]["overlay"][0]["operation"])


if __name__ == "__main__":
    unittest.main()
