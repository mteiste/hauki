VENV := .venv
PYTHON := $(VENV)/bin/python
NODEDIR := .nodejs
NODE := $(NODEDIR)/bin/node
NODE_VERSION := 22.23.4
MARKDOWNLINT := node_modules/.bin/markdownlint-cli2
# The system node (if any) may lack npm, so the pinned local copy is always used
NODE_PATH_ENV := PATH="$(CURDIR)/$(NODEDIR)/bin:$$PATH"

.PHONY: help
help:
	@echo "HAUKI Raspberry Pi Makefile"
	@echo ""
	@echo "  make prepare        - Create venv and install dev tools (workstation)"
	@echo "  make lint           - Run all linters"
	@echo "  make lint-python    - Run Ruff on src/ and tools/"
	@echo "  make lint-markdown  - Lint all markdown files"
	@echo "  make test-ha        - Verify Home Assistant connectivity"
	@echo "  make install        - Deploy systemd service (run on the RPi)"
	@echo "  make clean          - Remove venv and caches"

# Development setup on the workstation: Python venv (Ruff, Pillow for the PNG preview)
# and a local Node.js for markdownlint. Not for the Pi (no ARMv6 Node builds).
.PHONY: prepare
prepare:
	@if [ ! -d "$(VENV)" ]; then \
		echo "Creating virtual environment..."; \
		if command -v uv > /dev/null; then \
			uv venv -q $(VENV); \
		else \
			python3 -m venv $(VENV); \
		fi; \
	fi
	@if command -v uv > /dev/null; then \
		uv pip install -q -p $(PYTHON) -r requirements-dev.txt; \
	else \
		$(PYTHON) -m pip install -q -r requirements-dev.txt; \
	fi
	@echo "✓ Python dependencies installed"
	@if [ "$$($(NODE) --version 2>/dev/null)" != "v$(NODE_VERSION)" ]; then \
		ARCH=$$(uname -m); \
		OS=$$(uname -s | tr '[:upper:]' '[:lower:]'); \
		if [ "$$ARCH" = "x86_64" ]; then \
			NODE_ARCH="x64"; \
		elif [ "$$ARCH" = "aarch64" ] || [ "$$ARCH" = "arm64" ]; then \
			NODE_ARCH="arm64"; \
		else \
			echo "Error: Unsupported architecture: $$ARCH"; \
			exit 1; \
		fi; \
		NODE_DIST="node-v$(NODE_VERSION)-$${OS}-$${NODE_ARCH}"; \
		echo "Downloading Node.js $(NODE_VERSION) for $${OS}-$${NODE_ARCH}..."; \
		rm -rf $(NODEDIR); \
		mkdir -p $(NODEDIR); \
		curl -fsSL "https://nodejs.org/dist/v$(NODE_VERSION)/$${NODE_DIST}.tar.gz" -o $(NODEDIR)/node.tar.gz; \
		tar -xzf $(NODEDIR)/node.tar.gz -C $(NODEDIR) --strip-components=1; \
		rm $(NODEDIR)/node.tar.gz; \
		echo "✓ Node.js $(NODE_VERSION) installed to $(NODEDIR)/"; \
	fi
	@if [ ! -f "$(MARKDOWNLINT)" ]; then \
		echo "Installing markdown linter..."; \
		$(NODE_PATH_ENV) npm install --silent; \
		echo "✓ Markdown linter installed"; \
	fi

# Linters never fail the build: the point is to see every finding in one run, so
# check the output rather than the exit status
.PHONY: lint
lint: lint-python lint-markdown

.PHONY: lint-python
lint-python: prepare
	@echo "Linting Python files..."
	$(VENV)/bin/ruff check src/ tools/ || true

.PHONY: lint-markdown
lint-markdown: prepare
	@echo "Linting markdown files..."
	@$(NODE_PATH_ENV) npm run --silent lint:markdown || true

.PHONY: test-ha
test-ha: prepare
	@if [ ! -f config.json ]; then \
		echo "Error: config.json not found. Copy config.json.example and edit it."; \
		exit 1; \
	fi
	$(PYTHON) -c "\
import sys; sys.path.insert(0, 'src'); \
from config import Config; \
from homeassistant import HomeAssistant; \
ha = HomeAssistant(Config()); \
print('HA online:', ha.is_online)"

.PHONY: install
install:
	@if [ ! -f config.json ]; then \
		echo "Error: config.json not found. Copy config.json.example and edit it first."; \
		exit 1; \
	fi
	sudo useradd -r -s /bin/false hauki 2>/dev/null || true
	sudo usermod -a -G spi,gpio hauki
	sudo cp hauki.service /etc/systemd/system/hauki.service
	sudo systemctl daemon-reload
	sudo systemctl enable hauki
	sudo systemctl start hauki
	@echo "Service installed. Check status: sudo systemctl status hauki"
	@echo "Follow logs: sudo journalctl -u hauki -f"

.PHONY: clean
clean:
	rm -rf $(VENV)
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "Cleanup complete"
