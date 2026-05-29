import asyncio
import logging
import os
from concurrent.futures import ProcessPoolExecutor
from typing import Any

from .index import get_parsers
from .node import Node, export_tree, LocalStorage, Storage, llm_util
from .node.thinning import DefaultThinning
from .util import walk_tree

LOGGER = logging.getLogger(__name__)
MAX_FILE_COUNT_FOR_INDEXING = int(os.getenv("MAX_FILE_COUNT_FOR_INDEXING", 3))

def _make_tree_worker(path: str):
    """Worker function for multiprocessing - runs in separate process"""
    import asyncio
    return asyncio.run(get_parsers(path).make_tree(path))

DEFAULT_THINNING = DefaultThinning()

def initialize():
    llm_util.llm_initialize()

async def reset(destination: str, root_name: str, storage: Storage):
    destination_exists = await storage.exists(destination)
    if destination_exists:
        await storage.reset(destination)
    destination = await storage.mkdir(destination)
    destination_exists = await storage.exists(destination)
    if destination_exists:
        root_folder = await storage.join(destination, root_name)
        root_folder = await storage.mkdir(root_folder)
        return root_folder
    else:
        raise Exception(f"Destination {destination} does not exist")

async def index(source: str, destination: str, thinning_func: Any=DEFAULT_THINNING, storage=None, root_name="s_root", start_count=0, start_fresh=True) -> None:
    if storage is None:
        storage = LocalStorage()
    if start_fresh and start_count == 0:
        root_folder = await reset(destination, root_name, storage)
        root_node = Node(name="root", description="", node_id="root_node")
    else:
        root_folder = await storage.join(destination, root_name)
        root_node_path = await storage.join(root_folder, f"0_root_node.json")
        root_node = await Node.from_json(path=root_node_path, storage=storage)
    node_index_list = []
    total_paths = 0
    if os.path.exists(source):
        if os.path.isdir(source):
            # Use multiprocessing for directory flow
            paths = list(walk_tree(source))
            total_paths = len(paths)
            LOGGER.info(f"Batch:{(start_count / MAX_FILE_COUNT_FOR_INDEXING) + 1}")
            with ProcessPoolExecutor() as executor:
                loop = asyncio.get_event_loop()
                end = min(start_count + MAX_FILE_COUNT_FOR_INDEXING, total_paths)
                tasks = [loop.run_in_executor(executor, _make_tree_worker, path) for path in paths[start_count:end]]
                results = await asyncio.gather(*tasks)
                node_index_list.extend([result for result in results if result is not None])
        elif os.path.isfile(source):
            # Async call for single file
            tree = await get_parsers(source).make_tree(source)
            if tree is not None:
                node_index_list.append(tree)
    root_node.children.extend(node_index_list)
    if node_index_list:
        if thinning_func is not None:
            LOGGER.info(f"Before thinning: {root_node}")
            root_node = await thinning_func(root_node)
            LOGGER.info(f"After thinning: {root_node}")
        await export_tree(root_node, root_folder, storage=storage)
    if (total_paths - start_count) > MAX_FILE_COUNT_FOR_INDEXING:
        await index(source, destination, thinning_func, storage, root_name,
                    start_count=start_count+MAX_FILE_COUNT_FOR_INDEXING)

async def get_doc(path: Any, storage: Storage=None):
    if storage is None:
        storage = LocalStorage()
    async def get_json_path(inner_path):
        if inner_path.endswith(".json"):
            return inner_path
        async for p in storage.walk(inner_path):
            return await get_json_path(p)
        return None
    path = await get_json_path(path)
    context_node = await Node.from_json(path, storage)
    return context_node