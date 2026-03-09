# Makefile for Raspberry Pi Pico MicroPython development

# Load local configuration (copy config.mk.example to config.mk)
-include config.mk

# Configuration
VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
AMPY := $(VENV)/bin/ampy
STUBGEN := $(VENV)/bin/stubgen
NODEDIR := .nodejs
NODE := $(NODEDIR)/bin/node
NPM := $(NODEDIR)/bin/npm
MARKDOWNLINT := node_modules/.bin/markdownlint-cli2

# Helper functions to check required config values
define check_port
	@if [ -z "$(PORT)" ]; then \
		echo "Error: PORT is not defined. Copy config.mk.example to config.mk and set your serial port"; \
		exit 1; \
	fi
endef

define check_font_definition
	@if [ -z "$(FONT_PATH)" ] || [ -z "$(FONT_SIZES)" ]; then \
		echo "Error: FONT_PATH and FONT_SIZES must both be defined in config.mk"; \
		echo "  Example: FONT_PATH = /usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"; \
		echo "  Example: FONT_SIZES = 12 14 16 20 24 32"; \
		exit 1; \
	fi
	@if [ ! -f "$(FONT_PATH)" ]; then \
		echo "Error: Font file not found at $(FONT_PATH)"; \
		echo "  Find fonts with: fc-list | grep -i dejavu"; \
		exit 1; \
	fi
endef

# Directories
SRC_DIR := src
LIB_DIR := lib

# Auto-discover all Python files in src/ directory
SRC_FILES := $(wildcard $(SRC_DIR)/*.py)

.PHONY: help
help:
	@echo "Raspberry Pi Pico Development Makefile"
	@echo ""
	@echo "Setup targets:"
	@echo "  make prepare        - Create venv, install dependencies"
	@echo "  make clean          - Remove virtual environment and cleanup"
	@echo "  make fonts          - Generate custom font files (requires font-to-py)"
	@echo ""
	@echo "Linting targets:"
	@echo "  make lint           - Run all linters"
	@echo "  make lint-python    - Lint Python files with Ruff"
	@echo "  make lint-markdown  - Lint all markdown files"
	@echo ""
	@echo "Pico targets:"
	@echo "  make upload         - Upload everything (src + lib) to Pico"
	@echo "  make upload-app     - Upload only src/ files to Pico"
	@echo "  make upload-lib     - Upload lib/ directory to Pico"
	@echo "  make clean-pico     - Remove all files from Pico, upload only boot.py + safe main"
	@echo "  make ls             - List files on Pico"
	@echo "  make reset          - Soft reset the Pico (restart)"
	@echo "  make monitor        - Connect to Pico serial console (Ctrl+A K to exit)"

# Setup virtual environment and install dependencies
.PHONY: prepare
prepare:
	@if [ ! -d "$(VENV)" ]; then \
		echo "Creating virtual environment..."; \
		python3 -m venv $(VENV); \
		$(PIP) install --upgrade pip; \
		$(PIP) install -r requirements.txt; \
		echo "✓ Virtual environment created and dependencies installed"; \
	fi
	@if [ -f "$(NODE)" ]; then \
		export PATH="$$(pwd)/$(NODEDIR)/bin:$$PATH"; \
	fi; \
	if ! command -v node > /dev/null; then \
		echo "Installing Node.js 18 locally in $(NODEDIR)/..."; \
		mkdir -p $(NODEDIR); \
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
		NODE_VERSION="18.20.5"; \
		NODE_DIST="node-v$${NODE_VERSION}-$${OS}-$${NODE_ARCH}"; \
		echo "Downloading Node.js $${NODE_VERSION} for $${OS}-$${NODE_ARCH}..."; \
		curl -fsSL "https://nodejs.org/dist/v$${NODE_VERSION}/$${NODE_DIST}.tar.gz" -o $(NODEDIR)/node.tar.gz; \
		echo "Extracting Node.js..."; \
		tar -xzf $(NODEDIR)/node.tar.gz -C $(NODEDIR) --strip-components=1; \
		rm $(NODEDIR)/node.tar.gz; \
		echo "✓ Node.js installed to $(NODEDIR)/"; \
	fi
	@if [ ! -f "$(MARKDOWNLINT)" ]; then \
		echo "Installing markdown linter..."; \
		if [ -f "$(NODE)" ]; then \
			export PATH="$$(pwd)/$(NODEDIR)/bin:$$PATH"; \
		fi; \
		npm install; \
		echo "✓ Markdown linter installed"; \
	fi
	@if [ ! -d "tools/micropython-font-to-py" ]; then \
		echo "Setting up font-to-py tool..."; \
		mkdir -p tools; \
		git clone --depth=1 https://github.com/peterhinch/micropython-font-to-py.git tools/micropython-font-to-py; \
		echo "✓ font-to-py downloaded to tools/micropython-font-to-py"; \
	fi
	@if [ ! -f "lib/writer.py" ] && [ -f "tools/micropython-font-to-py/writer/writer.py" ]; then \
		echo "Copying writer.py to lib/..."; \
		mkdir -p lib; \
		cp tools/micropython-font-to-py/writer/writer.py lib/; \
		$(STUBGEN) lib/writer.py -o . && mv writer.pyi lib/writer.pyi 2>/dev/null || true; \
		echo "✓ writer.py copied to lib/"; \
	fi
	@if [ ! -d "tools/mrequests" ]; then \
		echo "Downloading mrequests library for MicroPython..."; \
		mkdir -p tools; \
		git clone --depth=1 https://github.com/SpotlightKid/mrequests.git tools/mrequests; \
		echo "✓ mrequests downloaded to tools/mrequests"; \
	fi
	@if [ ! -d "lib/mrequests" ] && [ -d "tools/mrequests/mrequests" ]; then \
		echo "Copying mrequests to lib/..."; \
		mkdir -p lib; \
		cp -r tools/mrequests/mrequests lib/; \
		echo "✓ mrequests copied to lib/mrequests/"; \
	fi

# Ensure ampy is available
$(AMPY): prepare

# Generate custom font files for MicroPython
.PHONY: fonts
fonts: prepare
	$(check_font_definition)
	@echo "Generating custom fonts from $(FONT_PATH)..."
	@mkdir -p lib/fonts
	@for size in $(FONT_SIZES); do \
		echo "  Generating $${size}pt font..."; \
		$(PYTHON) tools/micropython-font-to-py/font_to_py.py \
			"$(FONT_PATH)" $${size} lib/fonts/font$${size}.py -r \
			-c "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyzäöåÄÖÅ0123456789:.,!?°C@%/- "; \
	done
	@echo "  Generating 48pt font for price display (minimal charset)..."
	@$(PYTHON) tools/micropython-font-to-py/font_to_py.py \
		"$(FONT_PATH)" 48 lib/fonts/font48.py -r \
		-c "0123456789.-"
	@echo ""
	@echo "✓ Fonts generated successfully!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Run 'make upload-lib' to upload fonts to Pico"
	@echo "  2. See docs/fonts.md for usage examples"

# Upload all Python files from src/ to Pico
.PHONY: upload-app
upload-app: $(AMPY)
	$(check_port)
	@if [ -d "$(SRC_DIR)" ]; then \
		echo "Uploading Python files from $(SRC_DIR)/ to Pico on $(PORT)..."; \
		for file in $(SRC_DIR)/*.py; do \
			if [ -f "$$file" ]; then \
				echo "  Uploading $$(basename $$file)..."; \
				$(AMPY) --port $(PORT) put "$$file" /$$(basename $$file); \
			fi; \
		done; \
	else \
		echo "Error: $(SRC_DIR)/ directory not found"; \
		exit 1; \
	fi
	@if [ -f "config.json" ]; then \
		echo "Uploading config.json..."; \
		$(AMPY) --port $(PORT) put config.json; \
	else \
		echo "Warning: config.json not found. Copy config.json.example to config.json"; \
	fi
	@echo "Upload complete!"

# Upload lib directory
.PHONY: upload-lib
upload-lib: fonts $(AMPY)
	$(check_port)
	@if [ -d "$(LIB_DIR)" ]; then \
		echo "Uploading lib/ directory to Pico on $(PORT)..."; \
		$(AMPY) --port $(PORT) mkdir /lib 2>/dev/null || true; \
		for file in $(LIB_DIR)/*.py; do \
			if [ -f "$$file" ]; then \
				echo "  Uploading $$(basename $$file)..."; \
				$(AMPY) --port $(PORT) put "$$file" /lib/$$(basename $$file); \
			fi; \
		done; \
		if [ -d "$(LIB_DIR)/fonts" ]; then \
			echo "  Uploading fonts subdirectory..."; \
			$(AMPY) --port $(PORT) mkdir /lib/fonts 2>/dev/null || true; \
			for file in $(LIB_DIR)/fonts/*.py; do \
				if [ -f "$$file" ]; then \
					echo "    Uploading $$(basename $$file)..."; \
					$(AMPY) --port $(PORT) put "$$file" /lib/fonts/$$(basename $$file); \
				fi; \
			done; \
		fi; \
		if [ -d "$(LIB_DIR)/mrequests" ]; then \
			echo "  Uploading mrequests subdirectory..."; \
			$(AMPY) --port $(PORT) mkdir /lib/mrequests 2>/dev/null || true; \
			for file in $(LIB_DIR)/mrequests/*.py; do \
				if [ -f "$$file" ]; then \
					echo "    Uploading $$(basename $$file)..."; \
					$(AMPY) --port $(PORT) put "$$file" /lib/mrequests/$$(basename $$file); \
				fi; \
			done; \
		fi; \
		echo "Library upload complete!"; \
	else \
		echo "No lib/ directory found"; \
	fi

# Upload everything (src + lib)
.PHONY: upload
upload: upload-app upload-lib

# Remove all files from Pico and upload only boot.py + safe main.py
.PHONY: clean-pico
clean-pico: $(AMPY)
	$(check_port)
	@echo "Removing all files from Pico on $(PORT)..."
	@$(AMPY) --port $(PORT) run tools/clean_pico.py
	@echo "Uploading boot.py..."
	@$(AMPY) --port $(PORT) put $(SRC_DIR)/boot.py /boot.py
	@echo "Uploading safe main.py..."
	@$(AMPY) --port $(PORT) put tools/safe_main.py /main.py
	@echo "Pico cleaned. Only boot.py and safe main.py present."

# List files on Pico (recursively)
.PHONY: ls
ls: $(AMPY)
	$(check_port)
	@echo "Files on Pico ($(PORT)):"
	@$(AMPY) --port $(PORT) ls -r -l

# Reset/restart the Pico (soft reset)
.PHONY: reset
reset: prepare
	$(check_port)
	@echo "Resetting Pico on $(PORT)..."
	@$(PYTHON) -c "import serial; import time; s = serial.Serial('$(PORT)', 115200, timeout=1); s.write(b'\\x03\\x04'); time.sleep(0.5); s.close()"
	@echo "Pico reset complete!"

# Monitor serial output from Pico
.PHONY: monitor
monitor:
	$(check_port)
	@if ! command -v screen > /dev/null; then \
		echo "Error: screen is not installed"; \
		exit 1; \
	fi
	@echo "Connecting to Pico console on $(PORT)..."
	@echo "Press Ctrl+A then K to exit, or Ctrl+C to interrupt running program"
	@screen $(PORT) 115200

# Run all linters
.PHONY: lint
lint: lint-python lint-markdown

# Lint Python files
.PHONY: lint-python
lint-python: prepare
	@echo "Linting Python files..."
	$(VENV)/bin/ruff check $(SRC_DIR) || true

# Lint markdown files
.PHONY: lint-markdown
lint-markdown:
	@if [ -f "$(NODE)" ]; then \
		export PATH="$$(pwd)/$(NODEDIR)/bin:$$PATH"; \
	fi; \
	if [ -f "$(MARKDOWNLINT)" ]; then \
		npm run lint:markdown || true; \
	else \
		echo "Warning: markdownlint-cli2 is not installed. Run 'make prepare' first."; \
	fi

# Test Home Assistant API from host machine
.PHONY: test-ha
test-ha: $(AMPY)
	@if [ ! -f "config.json" ]; then \
		echo "Error: config.json not found"; \
		echo "  Copy config.json.example to config.json and configure it"; \
		exit 1; \
	fi
	@echo "Testing Home Assistant API connectivity..."
	@$(PYTHON) tools/test_homeassistant.py

# Clean up build artifacts and libraries
.PHONY: clean
clean:
	rm -rf $(LIB_DIR)
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .mypy_cache .ruff_cache
	@echo "Cleanup complete"

# Clean everything including development environment
.PHONY: distclean
distclean: clean
	rm -rf $(VENV)
	rm -rf $(NODEDIR)
	rm -rf node_modules
	rm -rf tools/micropython-font-to-py tools/mrequests
	@echo "Full cleanup complete"
