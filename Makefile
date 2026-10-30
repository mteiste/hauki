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
	@echo "  make deploy         - Copy to the Pi and install there (PI_HOST=hauki)"
	@echo "  make install        - Install and (re)start the service (run on the Pi)"
	@echo "  make case-preview   - Render PNG previews of the case model to case/build/"
	@echo "  make case-open      - Open the case model in the OpenSCAD GUI"
	@echo "  make case-check     - Check that the case clears the hardware"
	@echo "  make case-stl       - Export printable STL files to case/build/"
	@echo "  make clean          - Remove venv, caches and case renders"

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

# Runs on the Pi: puts the code, config and unit in place and (re)starts the service.
# The hauki user and the OS preparation are manual steps, see README.md.
.PHONY: install
install:
	@if [ ! -f config.json ]; then \
		echo "Error: config.json not found. Copy config.json.example and edit it first."; \
		exit 1; \
	fi
	@if ! id hauki > /dev/null 2>&1; then \
		echo "Error: user hauki does not exist. See 'Service user' in README.md."; \
		exit 1; \
	fi
	sudo install -d -m 0755 /opt/hauki /opt/hauki/src
	sudo rsync -a --delete --exclude __pycache__ --chown=root:root --chmod=D755,F644 src/ /opt/hauki/src/
	sudo install -m 0640 -o root -g hauki config.json /opt/hauki/config.json
	sudo install -m 0644 hauki.service /etc/systemd/system/hauki.service
	sudo systemctl daemon-reload
	sudo systemctl enable hauki
	sudo systemctl restart hauki
	@echo "Service installed. Check status: sudo systemctl status hauki"
	@echo "Follow logs: sudo journalctl -u hauki -f"

# Runs on the workstation: copies the working tree to ~/hauki on the Pi and installs
# from there
PI_HOST ?= hauki
.PHONY: deploy
deploy:
	rsync -a --delete --exclude .git --exclude .venv --exclude .nodejs --exclude node_modules \
		--exclude package-lock.json --exclude __pycache__ --exclude .ruff_cache --exclude .claude \
		--exclude case --exclude docs \
		./ $(PI_HOST):hauki/
	ssh $(PI_HOST) 'cd hauki && make install'

# Case model, rendered with the OpenSCAD Flatpak on the host
OPENSCAD := flatpak run --socket=x11 --env=DISPLAY=$(or $(DISPLAY),:0) org.openscad.OpenSCAD
CASE_MODEL := case/case.scad
CASE_BUILD := case/build
CASE_RENDER := --imgsize=1200,900 --viewall --autocenter --projection=ortho --colorscheme=Tomorrow

.PHONY: case-preview
case-preview:
	@mkdir -p $(CASE_BUILD)
	$(OPENSCAD) -o $(CASE_BUILD)/assembly.png --camera=0,0,0,60,0,25,0 $(CASE_RENDER) $(CASE_MODEL)
	$(OPENSCAD) -o $(CASE_BUILD)/front.png --camera=0,0,0,0,0,0,0 $(CASE_RENDER) $(CASE_MODEL)
	$(OPENSCAD) -o $(CASE_BUILD)/rear.png --camera=0,0,0,0,180,0,0 $(CASE_RENDER) $(CASE_MODEL)
	$(OPENSCAD) -o $(CASE_BUILD)/exploded.png -D 'part="exploded"' --camera=0,0,0,65,0,30,0 $(CASE_RENDER) $(CASE_MODEL)
	$(OPENSCAD) -o $(CASE_BUILD)/section.png -D 'part="section"' --camera=0,0,0,90,0,90,0 $(CASE_RENDER) $(CASE_MODEL)

.PHONY: case-open
case-open:
	$(OPENSCAD) $(CASE_MODEL)

# The case clears the hardware when OpenSCAD reports an empty result
.PHONY: case-check
case-check:
	@mkdir -p $(CASE_BUILD)
	$(OPENSCAD) -o $(CASE_BUILD)/clash.stl -D 'part="clash"' $(CASE_MODEL) 2>&1 | grep -E -i 'empty|Volumes|ERROR|WARNING' || true

.PHONY: case-stl
case-stl:
	@mkdir -p $(CASE_BUILD)
	$(OPENSCAD) -o $(CASE_BUILD)/back.stl -D 'part="back"' $(CASE_MODEL)
	$(OPENSCAD) -o $(CASE_BUILD)/lid.stl -D 'part="lid"' $(CASE_MODEL)
	$(OPENSCAD) -o $(CASE_BUILD)/plugs.stl -D 'part="plugs"' $(CASE_MODEL)

.PHONY: clean
clean:
	rm -rf $(VENV) $(CASE_BUILD)
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "Cleanup complete"
