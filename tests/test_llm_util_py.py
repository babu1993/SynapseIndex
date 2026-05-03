import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import synapseindex.node.llm_util as llm_mod


def _tool_response(arguments: dict):
    tool_call = SimpleNamespace(
        function=SimpleNamespace(name="combine_similar", arguments=json.dumps(arguments))
    )
    message = SimpleNamespace(content="", tool_calls=[tool_call])
    choice = SimpleNamespace(message=message)
    return SimpleNamespace(choices=[choice])


class TestLlmUtil(unittest.IsolatedAsyncioTestCase):
    async def test_model_build_from_env_removes_prefix(self):
        with patch.object(llm_mod.os, "getenv", side_effect=lambda k: {
            "SY_MODEL_NAME": "litellm/my-model",
            "SY_MODEL_API_KEY": "k",
        }.get(k)):
            model = llm_mod.Model.build_from_env()
        self.assertEqual(model.model, "my-model")
        self.assertEqual(model.api_key, "k")

    async def test_llm_completion_retries_then_succeeds(self):
        with patch.object(llm_mod, "acompletion", AsyncMock(side_effect=[Exception("boom"), "ok"])) as completion_mock, patch.object(
            llm_mod.asyncio, "sleep", AsyncMock()
        ) as sleep_mock:
            value = await llm_mod.llm_completion("p")

        self.assertEqual(value, "ok")
        self.assertEqual(completion_mock.await_count, 2)
        sleep_mock.assert_awaited_once()

    async def test_generate_node_summary_returns_message_content(self):
        fake_response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="summary text"))]
        )
        node = SimpleNamespace(node_id="1", text="abc")
        with patch.object(llm_mod, "llm_completion", AsyncMock(return_value=fake_response)):
            out = await llm_mod.generate_node_summary(node)
        self.assertEqual(out, "summary text")

    async def test_check_similarity_processes_groups_and_singletons(self):
        nodes = [
            SimpleNamespace(node_id="1", description="A"),
            SimpleNamespace(node_id="2", description="B"),
            SimpleNamespace(node_id="3", description="C"),
        ]
        response = _tool_response(
            {
                "groups": [
                    {"node_ids": ["1", "2"], "description": "ab-group"},
                ]
            }
        )
        combine_similar = AsyncMock(side_effect=lambda ids, desc: {"ids": ids, "desc": desc})

        with patch.object(llm_mod, "llm_completion", AsyncMock(return_value=response)):
            grouped = await llm_mod.check_similarity(nodes, combine_similar)

        self.assertEqual(combine_similar.await_count, 2)
        combine_similar.assert_any_await(["1", "2"], "ab-group")
        combine_similar.assert_any_await(["3"], "C")
        self.assertEqual(len(grouped), 2)

    async def test_check_similarity_accepts_legacy_node_ids_payload(self):
        nodes = [SimpleNamespace(node_id="x", description="DX")]
        response = _tool_response({"node_ids": ["x"], "description": "legacy"})
        combine_similar = AsyncMock(return_value="combined")

        with patch.object(llm_mod, "llm_completion", AsyncMock(return_value=response)):
            grouped = await llm_mod.check_similarity(nodes, combine_similar)

        combine_similar.assert_awaited_once_with(["x"], "legacy")
        self.assertEqual(grouped, ["combined"])

