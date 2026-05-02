import json
import os.path

from node.llm_util import generate_node_summary

NODE_COUNT = 0

class Node:

    @staticmethod
    def get_node_id():
        global NODE_COUNT
        NODE_COUNT += 1
        return f"{os.getpid()}_{NODE_COUNT}".zfill(8)

    def __init__(self, name, description=None, start_line=0, end_line=0, children=None, node_id=None, parent_id=None, **kwargs):
        self.name = name
        self.description = description
        self.start_line = start_line
        self.end_line = end_line
        self.children = children if children is not None else []
        self.node_id = node_id if node_id else Node.get_node_id()
        self.parent_id = parent_id
        self.level = kwargs.get("level", 0)
        self.text = kwargs.get("text", "")

    async def generate_description(self):
        # Placeholder for description generation logic, e.g. using an LLM
        self.description = await generate_node_summary(self)
    def get_json(self, path):
        return {
            "name": self.name,
            "description": self.description,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "children": [{"path":f"{path}{os.path.sep}{child.level}_{child.node_id}",
                          "desc": child.description} for child in self.children],
            "text": self.text
        }

    def __str__(self):
        return f"Node(id={self.node_id}, name={self.name}, description={self.description}, start_line={self.start_line}, end_line={self.end_line}, children_count={len(self.children)})\n\n{self.text}"

def export_tree(node, root_path):
    node_json = node.get_json(root_path)
    with open(os.path.join(root_path, f"{node.level}_{node.node_id}.json"), "w") as f:
        json.dump(node_json, f)
    for child in node.children:
        child_path = os.path.join(root_path, f"{child.level}_{child.node_id}")
        os.mkdir(child_path)
        export_tree(child, child_path)