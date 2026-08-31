from __future__ import annotations

from pathlib import Path
import unittest

import yaml


SOURCE_ROOT = Path(__file__).resolve().parents[2]
ROOT = SOURCE_ROOT if (SOURCE_ROOT / "orinoco.yaml").is_file() else SOURCE_ROOT / "github-template"


class DownstreamContractTests(unittest.TestCase):
    def test_declared_paths_use_the_compositional_boundary(self) -> None:
        config = yaml.safe_load((ROOT / "orinoco.yaml").read_text(encoding="utf-8"))
        self.assertEqual("site-specific/metadata/records", config["paths"]["records"])
        self.assertEqual("site-specific/content", config["paths"]["editorial"])
        self.assertEqual("site-specific", config["paths"]["site"])
        self.assertEqual(".orinoco-lite/site", config["paths"]["framework"])
        self.assertEqual("extensions", config["paths"]["extensions"])

    def test_extensions_are_empty_by_default(self) -> None:
        files = [
            path.relative_to(ROOT / "extensions").as_posix()
            for path in (ROOT / "extensions").rglob("*")
            if path.is_file() and path.name != ".gitkeep"
        ]
        self.assertEqual([], files)

    def test_supported_layout_override_is_declarative(self) -> None:
        path = ROOT / "site-specific/overrides/layouts"
        self.assertTrue(path.is_dir())
        self.assertFalse((ROOT / "extensions/layouts").exists())


if __name__ == "__main__":
    unittest.main()
