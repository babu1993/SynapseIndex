import asyncio
import json
import logging
import os
from typing import List, Callable, Awaitable, Tuple, Any

from litellm import acompletion

MODEL = None
LOGGER = logging.getLogger(__name__)


class Model:
    def __init__(self, name=None, api_key=None):
        self.model = name
        self.api_key = api_key

    @staticmethod
    def build_from_env() -> 'Model':
        model = os.getenv("SY_MODEL_NAME")
        if model:
            model = model.removeprefix("litellm/")
        return Model(model, os.getenv("SY_MODEL_API_KEY"))

    def get_model_params(self) -> dict:
        return {"model": self.model, "api_key": self.api_key}


if MODEL is None:
    MODEL = Model.build_from_env()


async def llm_completion(prompt, **kwargs):
    max_retries = 10
    messages = [{"role": "user", "content": prompt}]
    params = MODEL.get_model_params() if MODEL else {}
    params = params | kwargs
    for i in range(max_retries):
        try:
            response = await acompletion(
                messages=messages,
                temperature=0,
                **params
            )
            return response
        except Exception as e:
            print(e)
            if i < max_retries - 1:
                await asyncio.sleep(1)
            else:
                logging.error('Max retries reached for prompt: ' + prompt)
                return ""
    return None


async def generate_node_summary(node):
    LOGGER.info("Generating summary for node: " + node.node_id)
    prompt = f"""You are given a part of a document, your task is to generate a description of the partial document about what are main points covered in the partial document.

    Partial Document Text: {node.text}

    Directly return the description, do not include any other text.
    """
    response = await llm_completion(prompt)
    response = response.choices[0].message
    return response.content if response else ""


async def check_similarity(node_list: List, combine_similar: Callable[[List[str], str], Awaitable[Any]]) -> List[Any]:
    LOGGER.info("Checking similarity for nodes: " + ",".join([node.node_id for node in node_list]))
    all_node_ids = [str(node.node_id) for node in node_list]
    node_description_map = {str(node.node_id): str(getattr(node, "description", "") or "") for node in node_list}
    prompt = f"""Role: Expert Data Analyst
                Task: Group partial documents based on content similarity and generate a single line description for the group.
                Instructions:
                Semantic Analysis: Evaluate the provided document descriptions. Group them together if they cover the same topic, event, or subject matter, even if the wording differs.
                Exhaustiveness: Every Document ID provided in the input must be accounted for.
                Singletons: If a document is unique and does not relate to any others, treat it as a group of one.
                Tool Execution: Call the combine_similar tool exactly once with all groups.
                Input Format:
                The documents are provided below in ID: Description format, separated by double newlines.
                Input Data:
                {"\n\n".join(f"{node.node_id}:{node.description}" for node in node_list)}
                Output:
                Use combine_similar with this shape:
                combine_similar(groups=[{{"node_ids":["ID_A","ID_B"],"description":"..."}}, {{"node_ids":["ID_C"],"description":"..."}}])
            """
    tools = [
        {
            "type": "function",
            "function": {
                "name": "combine_similar",
                "description": "Combine similar nodes into a single node. The input is a list of node IDs that are deemed similar based on their descriptions.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "groups": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "node_ids": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "List of similar node IDs for this group.",
                                    },
                                    "description": {
                                        "type": "string",
                                        "description": "Single-line summary for this group.",
                                    },
                                },
                                "required": ["node_ids", "description"],
                            },
                            "description": "List of groups with node_ids and description.",
                        }
                    },
                    "required": ["groups"],
                },
            },
        }
    ]
    response = await llm_completion(prompt, tools=tools)
    if not response or not getattr(response, "choices", None):
        return

    finalized_groups: List[Tuple[List[str], str]] = []

    for choice in response.choices:
        message = getattr(choice, "message", None)
        if not message:
            continue

        tool_calls = getattr(message, "tool_calls", None) or []
        for tool_call in tool_calls:
            function = getattr(tool_call, "function", None)
            if not function or function.name != "combine_similar":
                continue

            raw_args = function.arguments or "{}"
            fn_args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args

            if not isinstance(fn_args, dict):
                LOGGER.warning("Skipping combine_similar call with invalid args: %s", fn_args)
                continue

            # Backward compatible: accept either groups=[[]] or node_ids=[] from model output.
            groups = fn_args.get("groups")
            if isinstance(groups, list):
                for group in groups:
                    if isinstance(group, dict):
                        node_ids = group.get("node_ids")
                        group_description = str(group.get("description", "")).strip()
                        if isinstance(node_ids, list) and node_ids:
                            normalized_ids = [str(node_id) for node_id in node_ids if str(node_id)]
                            if normalized_ids:
                                finalized_groups.append((normalized_ids, group_description))
                    elif isinstance(group, list) and group:
                        # Legacy model shape: groups=[['id1','id2']]
                        normalized_ids = [str(node_id) for node_id in group if str(node_id)]
                        if normalized_ids:
                            fallback_description = ", ".join(
                                node_description_map.get(node_id, "") for node_id in normalized_ids
                            ).strip()
                            finalized_groups.append((normalized_ids, fallback_description))
                continue

            node_ids = fn_args.get("node_ids")
            if isinstance(node_ids, list) and node_ids:
                normalized_ids = [str(node_id) for node_id in node_ids if str(node_id)]
                if normalized_ids:
                    group_description = str(fn_args.get("description", "")).strip()
                    if not group_description:
                        group_description = ", ".join(
                            node_description_map.get(node_id, "") for node_id in normalized_ids
                        ).strip()
                    finalized_groups.append((normalized_ids, group_description))

    covered_ids = {node_id for group_ids, _ in finalized_groups for node_id in group_ids}

    # Guarantee unique nodes are processed as singleton groups.
    for node_id in all_node_ids:
        if node_id not in covered_ids:
            finalized_groups.append(([node_id], node_description_map.get(node_id, "")))

    seen_groups = set()
    combined_children_list = []
    for group_ids, group_description in finalized_groups:
        unique_group = []
        for node_id in group_ids:
            if node_id in all_node_ids and node_id not in unique_group:
                unique_group.append(node_id)
        if not unique_group:
            continue

        group_key = tuple(unique_group)
        if group_key in seen_groups:
            continue
        seen_groups.add(group_key)
        if not group_description:
            group_description = ", ".join(node_description_map.get(node_id, "") for node_id in unique_group).strip()
        combined_children = await combine_similar(unique_group, group_description)
        combined_children_list.append(combined_children)
    return combined_children_list



