import unittest
import importlib
from unittest.mock import patch

index_mod = importlib.import_module("synapseindex.index")


class TestIndexModule(unittest.TestCase):
    def test_get_parsers_returns_md_parser_for_markdown_file(self):
        with patch.object(index_mod.os.path, "isfile", return_value=True):
            parser = index_mod.get_parsers("/tmp/doc.md")
        self.assertIsInstance(parser, index_mod.MDParser)

    def test_get_parsers_raises_for_non_file_path(self):
        with patch.object(index_mod.os.path, "isfile", return_value=False):
            with self.assertRaises(NotImplementedError):
                index_mod.get_parsers("/tmp/nope")

