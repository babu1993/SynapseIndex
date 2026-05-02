import os
from parsers.md_parser import MDParser
from parsers import Parser

parsers_map = {
    "md": MDParser
}

def get_parsers(path: str) -> Parser:
    if os.path.isfile(path):
        file_type = path.strip().split(".")[-1]
        return parsers_map[file_type]()
    else:
        raise NotImplementedError(f"No parser for {path}")