import logging
import re

from ..node import Node
from . import Parser

HEADER_REGEX = re.compile(r'^(#{1,6})\s+(.+)$')
LOGGER = logging.getLogger(__name__)


class MDParser(Parser):

    async def extract_nodes_from_md(self, content: str):
        lines = content.split("\n")
        nodes = []
        for line_no, line in enumerate(lines):
            header_match = HEADER_REGEX.match(line)
            if header_match:
                header_level = len(header_match.group(1))
                header_text = header_match.group(2).strip()
                node = Node(name=header_text, level=header_level, start_line=line_no)
                nodes.append(node)
        for node_index, node in enumerate(nodes):
            node.end_line = nodes[node_index + 1].start_line - 1 if node_index + 1 < len(nodes) else len(lines) - 1
            node.text = "\n".join(lines[node.start_line: node.end_line + 1])
            await node.generate_description()

        return nodes

    async def construct_tree_from_nodes(self, nodes):
        stack = []
        root = None
        for node in nodes:
            while stack and stack[-1].level >= node.level:
                stack.pop()
            if stack:
                stack[-1].children.append(node)
                node.parent_id = stack[-1].node_id
            else:
                root = node
            stack.append(node)
        return root

    async def make_tree(self, path: str):
        LOGGER.info("Making tree for document: %s", path)
        content = None
        with open(path, "r") as f:
            content = f.read()
        if not content:
            return None
        nodes = await self.extract_nodes_from_md(content)
        tree = await self.construct_tree_from_nodes(nodes)
        return tree
