import json
import os.path
import shutil
from pathlib import Path
from typing import Protocol, Any

import aiofiles
import aiofiles.os

from .llm_util import generate_node_summary

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

class Storage(Protocol):
    async def store(self, path: Any, node_json: dict) -> None:
        pass
    async def mkdir(self, path: Any) -> None:
        pass
    async def read(self, path: Any) -> Node:
        pass
    async def reset(self, path: Any) -> None:
        pass
    async def exists(self, path: Any) -> bool:
        pass
    async def join(self, root_path: Any, path: Any) -> Any:
        pass

class LocalStorage(Storage):

    async def store(self, path: str, node_json: dict) -> None:
        json_str = json.dumps(node_json)
        async with aiofiles.open(path, "w") as f:
            await f.write(json_str)
    async def read(self, path: str) -> Node:
        # async with aiofiles.open(path, "r") as f:
        #     return json.loads(await f.read())
        pass
    async def mkdir(self, path: str) -> None:
        await aiofiles.os.mkdir(path)

    async def reset(self, path: str) -> None:
        shutil.rmtree(path)

    async def exists(self, path: str) -> bool:
        return await aiofiles.os.path.exists(path)

    async def join(self, root_path, path) -> Any:
        return os.path.join(root_path, path)


LOCAL_STORAGE = LocalStorage()

async def export_tree(node, root_path, storage:Storage=None):
    if not storage:
        storage = LOCAL_STORAGE
    node_json = node.get_json(root_path)
    path = await storage.join(root_path, f"{node.level}_{node.node_id}.json")
    await storage.store(path, node_json)
    for child in node.children:
        child_path = await storage.join(root_path, f"{child.level}_{child.node_id}")
        await storage.mkdir(child_path)
        await export_tree(child, child_path)