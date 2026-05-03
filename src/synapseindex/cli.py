import argparse
import asyncio
import logging
from pathlib import Path
from typing import Sequence

from . import index as run_index


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="synapseindex",
        description="Build SynapseIndex page indexes for supported documents.",
    )
    parser.add_argument("source", help="Source markdown file or directory to index.")
    parser.add_argument("destination", help="Destination directory for generated index files.")
    parser.add_argument("--root-name", default="s_root", help="Root folder name under destination.")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level for CLI output.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(level=getattr(logging, args.log_level), format="%(levelname)s %(name)s - %(message)s")

    source_path = Path(args.source)
    if not source_path.exists():
        parser.error(f"Source path does not exist: {source_path}")

    asyncio.run(
        run_index(
            source=str(source_path),
            destination=args.destination,
            root_name=args.root_name,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

