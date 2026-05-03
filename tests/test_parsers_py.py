import tempfile
import unittest
from unittest.mock import AsyncMock, patch

from synapseindex.parsers import Parser
import synapseindex.parsers.md_parser as md_parser_mod


class FakeNode:
    def __init__(self, name, level=0, start_line=0, node_id=None):
        self.name = name
        self.level = level
        self.start_line = start_line
        self.end_line = 0
        self.node_id = node_id or name
        self.parent_id = None
        self.children = []
        self.text = ""
        self.description = ""

    async def generate_description(self):
        self.description = f"desc:{self.name}"


class DummyParser(Parser):
    async def make_tree(self, path: str) -> str:
        return path


class TestParsersModule(unittest.IsolatedAsyncioTestCase):
    async def test_parser_protocol_importable(self):
        parser = DummyParser()
        value = await parser.make_tree("x")
        self.assertEqual(value, "x")

    async def test_extract_nodes_from_md_builds_nodes_and_ranges(self):
        parser = md_parser_mod.MDParser()
        content = "# Title\nline\n## Section\nbody"
        with patch.object(md_parser_mod, "Node", FakeNode):
            nodes = await parser.extract_nodes_from_md(content)

        self.assertEqual(len(nodes), 2)
        self.assertEqual(nodes[0].name, "Title")
        self.assertEqual(nodes[0].end_line, 1)
        self.assertEqual(nodes[1].end_line, 3)
        self.assertEqual(nodes[0].description, "desc:Title")

    async def test_construct_tree_from_nodes_sets_parents(self):
        parser = md_parser_mod.MDParser()
        root = FakeNode("root", level=1, node_id="n1")
        child = FakeNode("child", level=2, node_id="n2")
        sibling = FakeNode("sibling", level=1, node_id="n3")

        tree = await parser.construct_tree_from_nodes([root, child, sibling])

        self.assertEqual(tree, sibling)
        self.assertEqual(child.parent_id, "n1")
        self.assertEqual(root.children[0], child)

    async def test_make_tree_reads_file_and_constructs_tree(self):
        parser = md_parser_mod.MDParser()
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as tmp:
            tmp.write("# A\ntext")
            tmp_path = tmp.name

        fake_nodes = [FakeNode("A")]
        with patch.object(parser, "extract_nodes_from_md", AsyncMock(return_value=fake_nodes)) as extract_mock, patch.object(
            parser, "construct_tree_from_nodes", AsyncMock(return_value=fake_nodes[0])
        ) as construct_mock:
            tree = await parser.make_tree(tmp_path)

        self.assertEqual(tree, fake_nodes[0])
        extract_mock.assert_awaited_once()
        construct_mock.assert_awaited_once_with(fake_nodes)

