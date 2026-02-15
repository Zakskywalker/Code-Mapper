import types
import unittest

import csharp_scan_main as appmod


class PrereqTests(unittest.TestCase):
    def test_collect_missing_prerequisites_accepts_valid_python(self):
        version = types.SimpleNamespace(major=3, minor=11)
        missing = appmod.collect_missing_prerequisites(
            version_info=version,
            module_checker=lambda name: object(),
        )
        self.assertEqual(missing, [])

    def test_collect_missing_prerequisites_flags_old_python(self):
        version = types.SimpleNamespace(major=3, minor=8)
        missing = appmod.collect_missing_prerequisites(
            version_info=version,
            module_checker=lambda name: object(),
        )
        self.assertTrue(any("Python 3.9+" in item for item in missing))

    def test_collect_missing_prerequisites_flags_missing_module(self):
        version = types.SimpleNamespace(major=3, minor=11)
        missing = appmod.collect_missing_prerequisites(
            version_info=version,
            module_checker=lambda name: None if name == "PIL" else object(),
        )
        self.assertTrue(any("Pillow" in item for item in missing))


class LanguageDetectionTests(unittest.TestCase):
    def setUp(self):
        self.mapper = appmod.CSharpProMapper.__new__(appmod.CSharpProMapper)

    def test_detect_language_csharp(self):
        lang = self.mapper.detect_language("example.cs", ["public class A {}"])
        self.assertEqual(lang, "csharp")

    def test_detect_language_python(self):
        lang = self.mapper.detect_language("example.py", ["class A:", "    def b(self):", "        pass"])
        self.assertEqual(lang, "python")

    def test_detect_language_malbolge(self):
        lang = self.mapper.detect_language("hello.mal", ["(=<`#9]~6ZY32Vx/4Rs+0No-&Jk)"])
        self.assertEqual(lang, "malbolge")

    def test_programming_language_heuristic(self):
        self.assertTrue(self.mapper.is_probably_programming_language(["class A {", "return 1;"]))
        self.assertFalse(self.mapper.is_probably_programming_language(["this is plain text", "notes and prose"]))


if __name__ == "__main__":
    unittest.main()
