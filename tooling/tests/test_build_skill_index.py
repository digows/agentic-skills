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


if __name__ == "__main__":
    unittest.main()
