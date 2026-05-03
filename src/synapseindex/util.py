import logging
import os

from .node import Node


def walk_tree(root:str):
    for (dirpath, _, filenames) in os.walk(root):
        for filename in filenames:
            yield os.path.join(dirpath, filename)

def print_tree(root:Node):
    logging.info(root)
    if len(root.children) > 0:
        for child in root.children:
            print_tree(child)
