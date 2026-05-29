import os
import tempfile
import unittest
import importlib
from unittest.mock import AsyncMock, Mock, patch

import synapseindex.node as node_mod

synapse_pkg = importlib.reload(importlib.import_module("synapseindex"))


class _FakeParser:
    def __init__(self, tree):
        self._tree = tree

    async def make_tree(self, _path):
        return self._tree


class _FakeExecutor:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False


class TestSynapseIndexInit(unittest.IsolatedAsyncioTestCase):
    def test_make_tree_worker_runs_parser_make_tree(self):
        tree = node_mod.Node(name="t")
        with patch.object(synapse_pkg, "get_parsers", return_value=_FakeParser(tree)):
            out = synapse_pkg._make_tree_worker("/tmp/a.md")
        self.assertEqual(out, tree)

    async def test_index_single_file_exports_tree(self):
        tree = node_mod.Node(name="tree")
        thinning = AsyncMock(side_effect=lambda node: node)

        with tempfile.TemporaryDirectory() as tmpdir:
            source = os.path.join(tmpdir, "doc.md")
            destination = os.path.join(tmpdir, "out")
            with open(source, "w", encoding="utf-8") as f:
                f.write("# hi")

            with patch.object(synapse_pkg, "get_parsers", return_value=_FakeParser(tree)), patch.object(
                synapse_pkg, "export_tree", AsyncMock()
            ) as export_mock:
                await synapse_pkg.index(source=source, destination=destination, thinning_func=thinning)

        thinning.assert_awaited_once()
        export_mock.assert_awaited_once()

    async def test_index_directory_flow_uses_executor_and_gather(self):
        n1 = node_mod.Node(name="n1")
        fake_loop = Mock()
        fake_loop.run_in_executor = Mock(side_effect=[object(), object()])

        with tempfile.TemporaryDirectory() as tmpdir:
            source = os.path.join(tmpdir, "src")
            destination = os.path.join(tmpdir, "out")
            os.mkdir(source)

            with patch.object(synapse_pkg, "walk_tree", return_value=["a.md", "b.md"]), patch.object(
                synapse_pkg, "ProcessPoolExecutor", return_value=_FakeExecutor()
            ), patch.object(synapse_pkg.asyncio, "get_event_loop", return_value=fake_loop), patch.object(
                synapse_pkg.asyncio, "gather", AsyncMock(return_value=[n1, None])
            ) as gather_mock, patch.object(synapse_pkg, "export_tree", AsyncMock()) as export_mock:
                await synapse_pkg.index(source=source, destination=destination, thinning_func=None)

        gather_mock.assert_awaited_once()
        export_mock.assert_awaited_once()

    async def test_index_raises_when_destination_path_not_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source = os.path.join(tmpdir, "doc.md")
            destination = os.path.join(tmpdir, "out")
            with open(source, "w", encoding="utf-8") as f:
                f.write("# hi")

            with patch.object(synapse_pkg.os.path, "isdir", return_value=False):
                with self.assertRaises(Exception):
                    await synapse_pkg.index(source=source, destination=destination, thinning_func=None)

    async def test_initialize_calls_llm_initialize(self):
        with patch.object(synapse_pkg.llm_util, "llm_initialize") as llm_init_mock:
            synapse_pkg.initialize()
        llm_init_mock.assert_called_once()

    async def test_reset_destination_exists_and_not_exists(self):
        storage = AsyncMock()
        storage.exists.side_effect = [True, True, False]
        storage.reset = AsyncMock()
        storage.mkdir = AsyncMock(side_effect=["/tmp/dir", "/tmp/dir/root"])
        storage.join = AsyncMock(return_value="/tmp/dir/root")
        # destination exists branch
        result = await synapse_pkg.reset("/tmp/dir", "root", storage)
        self.assertEqual(result, "/tmp/dir/root")
        # destination does not exist branch
        storage.exists.side_effect = [False]
        with self.assertRaises(Exception):
            await synapse_pkg.reset("/tmp/dir", "root", storage)

    async def test_get_doc_returns_node(self):
        storage = AsyncMock()
        storage.read = AsyncMock(return_value={"name": "n", "description": "", "start_line": 0, "end_line": 0, "children": [], "node_id": "nid", "parent_id": None, "level": 0, "text": ""})
        storage.exists = AsyncMock(return_value=True)
        storage.join = AsyncMock(return_value="/tmp/n.json")
        # direct .json path
        node = await synapse_pkg.get_doc("/tmp/n.json", storage)
        self.assertEqual(node.name, "n")
        # indirect path (walk yields a .json)
        async def async_gen(items):
            for item in items:
                yield item
        storage.walk = lambda _: async_gen(["/tmp/n.json"])
        node = await synapse_pkg.get_doc("/tmp/dir", storage)
        self.assertEqual(node.name, "n")

    async def test_index_start_fresh_false_and_recursive(self):
        storage = AsyncMock()
        storage.exists = AsyncMock(return_value=True)
        storage.join = AsyncMock(side_effect=lambda *a, **k: "/".join(a[1:]))
        storage.read = AsyncMock(return_value={"name": "root", "description": "", "start_line": 0, "end_line": 0, "children": [], "node_id": "root_node", "parent_id": None, "level": 0, "text": ""})
        storage.mkdir = AsyncMock(return_value="/tmp/dir")
        storage.reset = AsyncMock()

        fake_loop = Mock()
        # Return a unique object per call; no risk of running out during recursion.
        fake_loop.run_in_executor = Mock(side_effect=lambda *args, **kwargs: object())

        with patch.object(synapse_pkg.os.path, "exists", return_value=True), \
             patch.object(synapse_pkg.os.path, "isdir", return_value=True), \
             patch.object(synapse_pkg, "walk_tree", return_value=["a.md", "b.md", "c.md", "d.md"]), \
             patch.object(synapse_pkg, "ProcessPoolExecutor"), \
             patch.object(synapse_pkg.asyncio, "get_event_loop", return_value=fake_loop), \
             patch.object(synapse_pkg.asyncio, "gather", AsyncMock(return_value=[None, None, None])), \
             patch.object(synapse_pkg, "export_tree", AsyncMock()):
            # start_fresh False, triggers loading from json
            await synapse_pkg.index("src", "dest", storage=storage, start_fresh=False)
            # recursive call branch
            await synapse_pkg.index("src", "dest", storage=storage, start_count=0)
