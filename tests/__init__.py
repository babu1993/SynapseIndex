import os
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))
SRC = os.path.join(ROOT, "src")
PKG_SRC = os.path.join(SRC, "synapseindex")

# The project uses absolute imports like `from node import ...` and `from index import ...`.
for path in (SRC, PKG_SRC):
    if path not in sys.path:
        sys.path.insert(0, path)

