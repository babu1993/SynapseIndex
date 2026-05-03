import unittest
from unittest.mock import patch

import synapseindex.util as util_mod


class FakeNode:
    def __init__(self, name, children=None):
        self.name = name
        self.children = children or []

    def __str__(self):
        return f"Node<{self.name}>"


class TestUtilModule(unittest.TestCase):
    def test_walk_tree_yields_all_files(self):
        fake_walk = [
            ("/root", [], ["a.md", "b.md"]),
            ("/root/sub", [], ["c.md"]),
        ]
        with patch.object(util_mod.os, "walk", return_value=fake_walk):
            paths = list(util_mod.walk_tree("/root"))
        self.assertEqual(paths, ["/root/a.md", "/root/b.md", "/root/sub/c.md"])

    def test_print_tree_logs_recursively(self):
        root = FakeNode("root", [FakeNode("a"), FakeNode("b", [FakeNode("c")])])
        with patch.object(util_mod.logging, "info") as info_mock:
            util_mod.print_tree(root)
        self.assertEqual(info_mock.call_count, 4)

