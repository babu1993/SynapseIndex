import os
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

import synapseindex.node as node_mod
import synapseindex.node.thinning as thinning_mod


class FakeStorage:
    def __init__(self):
        self.store = AsyncMock()
        self.mkdir = AsyncMock()
        self.read = AsyncMock()
        self.join = AsyncMock(side_effect=lambda root_path, *paths: os.path.join(root_path, *paths))


class TestNodeModule(unittest.IsolatedAsyncioTestCase):
    async def test_generate_description_uses_llm_summary(self):
        node = node_mod.Node(name="n", text="body")
        with patch.object(node_mod, "generate_node_summary", AsyncMock(return_value="summary")):
            await node.generate_description()
        self.assertEqual(node.description, "summary")

    async def test_local_storage_store_and_read_roundtrip(self):
        storage = node_mod.LocalStorage()
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "node.json")
            payload = {"name": "a"}
            await storage.store(file_path, payload)
            loaded = await storage.read(file_path)
        self.assertEqual(loaded, payload)

    async def test_export_tree_stores_root_and_child(self):
        root = node_mod.Node(name="root", level=0, node_id="1")
        child = node_mod.Node(name="child", level=1, node_id="2")
        root.children.append(child)
        storage = FakeStorage()

        with tempfile.TemporaryDirectory() as tmpdir, patch.object(node_mod, "LOCAL_STORAGE", storage):
            await node_mod.export_tree(root, tmpdir, storage=storage)

        self.assertGreaterEqual(storage.store.await_count, 2)
        storage.mkdir.assert_called()


class TestThinningModule(unittest.IsolatedAsyncioTestCase):
    async def test_combine_similar_creates_parent_and_recurses(self):
        thinning = thinning_mod.DefaultThinning()
        a = node_mod.Node(name="A", node_id="a")
        b = node_mod.Node(name="B", node_id="b")

        with patch.object(thinning, "__call__", AsyncMock(side_effect=[a, b])) as call_mock:
            combined = await thinning.combine_similar(["a", "b"], "group desc", {"a": a, "b": b})

        self.assertEqual(combined.description, "group desc")
        self.assertEqual(len(combined.children), 2)
        self.assertEqual(call_mock.await_count, 2)

    async def test_call_skips_thinning_when_children_below_threshold(self):
        thinning = thinning_mod.DefaultThinning()
        thinning_mod.MAX_CHILDREN_LENGTH = 10
        root = node_mod.Node(name="root", children=[node_mod.Node(name="c1"), node_mod.Node(name="c2")])

        with patch.object(thinning, "__call__", AsyncMock(side_effect=root.children)) as recurse_mock:
            result = await thinning_mod.DefaultThinning.__call__(thinning, root)

        self.assertEqual(result, root)
        self.assertEqual(recurse_mock.await_count, 2)

    async def test_call_uses_check_similarity_when_threshold_exceeded(self):
        thinning = thinning_mod.DefaultThinning()
        thinning_mod.MAX_CHILDREN_LENGTH = 1
        root = node_mod.Node(name="root", children=[node_mod.Node(name="c1"), node_mod.Node(name="c2")])
        combined = [node_mod.Node(name="combined")]

        with patch.object(thinning_mod, "check_similarity", AsyncMock(return_value=combined)) as check_mock:
            result = await thinning(root)

        self.assertEqual(result.children, combined)
        check_mock.assert_awaited_once()
