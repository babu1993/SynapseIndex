# SynapseIndex

SynapseIndex builds structured page-level indexes from documents so AI agents can retrieve relevant context for LLM workflows.

The current release focuses on **Markdown** input. It parses heading-based document structure, generates node summaries with an LLM, optionally groups related sections, and exports the result as a nested JSON index.

## Features

- Parses Markdown documents into a tree of sections based on `#`, `##`, `###`, and deeper headings
- Generates summaries for document nodes using an LLM configured through environment variables
- Supports indexing a single Markdown file or all supported files inside a directory
- Uses async processing and multiprocessing for directory-based indexing
- Exports the resulting index tree as JSON files that can be consumed by downstream AI agents
- Includes a command-line interface and a Python API

## Installation

### From source

```bash
git clone <your-repository-url>
cd SynapseIndex
pip install -e .
```

### After publishing to PyPI

```bash
pip install synapseindex
```

## Requirements

- Python `>= 3.13`
- An LLM provider compatible with the configured LiteLLM model
- Environment variables for model access:
  - `SY_MODEL_NAME`
  - `SY_MODEL_API_KEY`

## Configuration

Set the model configuration before running the indexer:

```bash
export SY_MODEL_NAME="google.gemma-3-4b-it"
export SY_MODEL_API_KEY="your-api-key"
```

`SY_MODEL_NAME` may optionally include the `litellm/` prefix; the code strips it automatically.

## Quick Start

Index a single Markdown file:

```bash
synapseindex /path/to/document.md /path/to/output
```

Index a directory of Markdown files:

```bash
synapseindex /path/to/docs /path/to/output
```

Choose a custom root folder name in the output:

```bash
synapseindex /path/to/docs /path/to/output --root-name docs_root
```

Enable more verbose logs:

```bash
synapseindex /path/to/docs /path/to/output --log-level DEBUG
```

## CLI Reference

```text
synapseindex SOURCE DESTINATION [--root-name NAME] [--log-level LEVEL]
```

### Arguments

- `SOURCE` - A Markdown file or a directory containing supported files
- `DESTINATION` - Directory where the generated index will be written

### Options

- `--root-name` - Name of the root output folder inside `DESTINATION` (default: `s_root`)
- `--log-level` - One of `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

## Python API

You can also call SynapseIndex directly from Python:

```python
import asyncio

from synapseindex import index

asyncio.run(index(source="/path/to/document.md", destination="/path/to/output"))
```

## Output Format

SynapseIndex writes a nested JSON structure under the destination directory.

At a high level, the output contains:

- a root folder (default: `s_root`)
- one JSON file for each node
- subdirectories for child nodes

Each exported node JSON includes fields such as:

- `name`
- `description`
- `start_line`
- `end_line`
- `children`
- `text`

This structure is designed to make section-level retrieval straightforward for downstream tools and agents.

## How It Works

1. Read the Markdown file or files
2. Detect headings and build a section tree
3. Generate a summary for each node with an LLM
4. Optionally group similar child nodes during thinning
5. Export the resulting tree as JSON files

## Current Limitations

- Only Markdown files are supported at the moment
- The current implementation expects LLM configuration to be available for summary generation
- If the destination directory already exists, it is removed before writing new output

## Development

Run the test suite with:

```bash
make test
```

For verbose test output:

```bash
make test-verbose
```

## License

This project is licensed under the terms of the `LICENSE` file included in this repository.

