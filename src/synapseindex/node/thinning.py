import logging
import os
from functools import partial
from typing import Protocol, List, Dict

from . import Node
from .llm_util import check_similarity

LOGGER = logging.getLogger(__name__)
MAX_CHILDREN_LENGTH = os.getenv("SY_MAX_CHILDREN_LENGTH", 3)

class TreeThinning(Protocol):
    async def __call__(self, root_node:Node) -> Node:
        pass

class DefaultThinning(TreeThinning):

    async def combine_similar(self, node_ids: List[str], description: str, child_nodes:Dict[str, Node]) -> Node:
        # Placeholder for logic to combine similar nodes, e.g. using an LLM
        LOGGER.info(f"Combining similar nodes:{node_ids}<-{description}")
        combined_node = Node(description=description, name=child_nodes[node_ids[0]].name)
        for child_node in [child_nodes[_id] for _id in node_ids if _id in child_nodes]:
            combined_child_node = await self.__call__(child_node)
            combined_node.children.append(combined_child_node)
        return combined_node


    async def __call__(self, root_node:Node) -> Node:
        LOGGER.info(f"Starting thinning:{root_node.node_id}:{root_node.name}")
        child_nodes = {node.node_id: node for node in root_node.children}
        combine_similar_fn = partial(self.combine_similar, child_nodes=child_nodes)
        if len(root_node.children) < MAX_CHILDREN_LENGTH:
            LOGGER.info(f"Skipping thinning for node:{root_node.node_id}<-{root_node.parent_id}")
            combined_child_node_list = []
            for child_node in root_node.children:
                combined_child_node_list.append(await self.__call__(child_node))
            root_node.children = combined_child_node_list
            return root_node
        root_node.children = await check_similarity(root_node.children, combine_similar_fn)
        return root_node

