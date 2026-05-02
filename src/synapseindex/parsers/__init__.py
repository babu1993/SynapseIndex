from typing import Protocol


class Parser(Protocol):
    async def make_tree(self, path: str) -> str:
        pass