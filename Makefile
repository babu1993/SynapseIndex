PYTHON ?= python
PROJECT_ROOT := $(CURDIR)
PYTHONPATH_VALUE := $(PROJECT_ROOT)/src:$(PROJECT_ROOT)/src/synapseindex

.PHONY: test test-verbose

test:
	PYTHONPATH="$(PYTHONPATH_VALUE)" $(PYTHON) -m unittest discover -s tests

test-verbose:
	PYTHONPATH="$(PYTHONPATH_VALUE)" $(PYTHON) -m unittest discover -s tests -v

