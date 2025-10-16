#################################################################################
# GLOBALS                                                                       #
#################################################################################

PROJECT_NAME = scout
PYTHON_VERSION = 3.9
PYTHON_INTERPRETER = python3
PACKAGE_MANAGER = pip

#################################################################################
# INSTALLATION COMMANDS                                                         #
#################################################################################

## Create virtual environment (if it doesn't exist)
.PHONY: venv
venv:
	@if [ ! -d ".venv" ]; then \
		echo "Creating virtual environment..."; \
		$(PYTHON_INTERPRETER) -m venv .venv; \
		echo ">>> Virtual environment created at .venv"; \
		echo ">>> Activate with: source .venv/bin/activate"; \
	else \
		echo ">>> Virtual environment already exists at .venv"; \
	fi

## Install Python Dependencies
.PHONY: install
install: venv
	pip install -e .
	@echo ">>> Base dependencies installed."

## Install development dependencies
.PHONY: install-dev
install-dev: venv
	pip install -e ".[dev]"
	@echo ">>> Development dependencies installed"

#################################################################################
# CODE HYGIENE COMMANDS                                                         #
#################################################################################

## Delete all compiled Python files and caches
.PHONY: clean
clean:
	find . -type f -name "*.py[co]" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	find . -type d -name ".ipynb_checkpoints" -exec rm -rf {} +
	@echo ">>> Cleaned Python cache files"

## Lint code using ruff (use `make format` to auto-fix)
.PHONY: lint
lint:
	ruff check scout
	ruff format --check scout
	@echo ">>> Linting complete"

## Format source code with ruff
.PHONY: format
format:
	ruff check --select I --fix scout  # Fix import sorting
	ruff format scout
	@echo ">>> Code formatted"

#################################################################################
# UTILITY COMMANDS                                                              #
#################################################################################

## Show recently modified files (like tree + ls -ltr)
.PHONY: recent
recent:
	@find . -type f -not -path '*/\.*' -not -path '*/__pycache__/*' -not -path '*/venv/*' -not -path '*/.venv/*' -printf '%T@ %p\n' | sort -n | tail -20 | perl -MTime::Piece -MTime::Seconds -nE 'chomp; ($$t, $$f) = split / /, $$_, 2; $$now = time; $$diff = $$now - int($$t); if ($$diff < 60) { $$ago = sprintf "%ds ago", $$diff } elsif ($$diff < 3600) { $$ago = sprintf "%dm ago", $$diff/60 } elsif ($$diff < 86400) { $$ago = sprintf "%dh ago", $$diff/3600 } else { $$ago = sprintf "%dd ago", $$diff/86400 } printf "%-12s %s\n", $$ago, $$f'

## Show cache file statistics
.PHONY: cache-stats
cache-stats:
	@echo ">>> Cache file statistics:"
	@python3 scripts/cache_stats.py

## Log cache statistics to timestamped file
.PHONY: cache-log
cache-log:
	@mkdir -p outs/logs
	@TIMESTAMP=$$(date +%Y%m%d_%H%M%S); \
	LOGFILE="outs/logs/cache_stats_$${TIMESTAMP}.txt"; \
	echo "SCOUT Cache Statistics - $$(date)" > $$LOGFILE; \
	echo "========================================" >> $$LOGFILE; \
	echo "" >> $$LOGFILE; \
	python3 scripts/cache_stats.py >> $$LOGFILE; \
	echo "" >> $$LOGFILE; \
	echo "Detailed file info:" >> $$LOGFILE; \
	ls -lh data/cache/*.json >> $$LOGFILE; \
	echo ">>> Cache statistics logged to $$LOGFILE"

#################################################################################
# Self Documenting Boilerplate                                                  #
#################################################################################

.DEFAULT_GOAL := help

define PRINT_HELP_PYSCRIPT
import re, sys; \
lines = '\n'.join([line for line in sys.stdin]); \
matches = re.findall(r'\n## (.*)\n[\s\S]+?\n([a-zA-Z_-]+):', lines); \
print('SCOUT - Scraping Career Opportunities Using Technology\n'); \
print('Available commands:\n'); \
print('\n'.join(['{:20}{}'.format(*reversed(match)) for match in matches]))
endef
export PRINT_HELP_PYSCRIPT

help:
	@$(PYTHON_INTERPRETER) -c "$${PRINT_HELP_PYSCRIPT}" < $(MAKEFILE_LIST)
