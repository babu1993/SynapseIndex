import os
import shutil
import asyncio
from concurrent.futures import ProcessPoolExecutor
from util import walk_tree, print_tree
from index import get_parsers
import logging
from node import Node, export_tree

LOGGER = logging.getLogger(__name__)

MAX_CHILDREN_LENGTH = os.getenv("SY_MAX_CHILDREN_LENGTH", 3)

def _make_tree_worker(path: str):
    """Worker function for multiprocessing - runs in separate process"""
    import asyncio
    return asyncio.run(get_parsers(path).make_tree(path))


async def index(source: str, destination: str, thinning_func=None, root_name="root") -> None:
    node_index_list = []
    if os.path.exists(destination):
        shutil.rmtree(destination)
    os.makedirs(destination)
    if os.path.isdir(destination):
        root_folder = os.path.join(destination, root_name)
        os.mkdir(root_folder)
    else:
        raise Exception(f"Destination {destination} does not exist")
    if os.path.exists(source):
        if os.path.isdir(source):
            # Use multiprocessing for directory flow
            paths = list(walk_tree(source))
            with ProcessPoolExecutor() as executor:
                loop = asyncio.get_event_loop()
                tasks = [loop.run_in_executor(executor, _make_tree_worker, path) for path in paths]
                results = await asyncio.gather(*tasks)
                node_index_list.extend([result for result in results if result is not None])
        elif os.path.isfile(source):
            # Async call for single file
            tree = await get_parsers(source).make_tree(source)
            if tree is not None:
                node_index_list.append(tree)
    if node_index_list:
        if len(node_index_list) > MAX_CHILDREN_LENGTH and thinning_func is not None:
            node_index_list = await thinning_func(node_index_list)
        root_node = Node(name="root", children=node_index_list, description="")
        export_tree(root_node, root_folder)





