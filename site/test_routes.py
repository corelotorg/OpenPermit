# SPDX-License-Identifier: Apache-2.0
import importlib.util
import tempfile
import unittest
from pathlib import Path


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).parent / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Routes(unittest.TestCase):
    def test_build_and_detect_regressions(self):
        builder, checker = load("build"), load("check")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(builder.build(root, "https://corelotorg.github.io/OpenPermit/"), 5)
            self.assertEqual(checker.check(root), [])
            (root / "spec/index.html").unlink()
            self.assertTrue(checker.check(root))
            builder.build(root, "https://openpermit.dev/")
            with (root / "index.html").open("a") as f:
                f.write('<a href="/docs/">broken project route</a><a href="https://github.com/SheetPros/OpenPermit">stale CTA</a>')
            errors = checker.check(root)
            self.assertTrue(any("root-relative" in e for e in errors))
            self.assertTrue(any("stale repository" in e for e in errors))

    def test_refuse_source_overwrite(self):
        builder = load("build")
        with self.assertRaises(ValueError):
            builder.build(builder.ROOT, "https://openpermit.dev/")


if __name__ == "__main__":
    unittest.main()
