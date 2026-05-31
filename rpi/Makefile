VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

.PHONY: help
help:
	@echo "HAUKI Raspberry Pi Makefile"
	@echo ""
	@echo "  make prepare   - Create venv, install dependencies"
	@echo "  make lint      - Run Ruff linter on src/"
	@echo "  make test-ha   - Verify Home Assistant connectivity"
	@echo "  make install   - Deploy systemd service (run on the RPi)"
	@echo "  make clean     - Remove venv and caches"

.PHONY: prepare
prepare:
	@if [ ! -d "$(VENV)" ]; then \
		python3 -m venv $(VENV); \
		$(PYTHON) -m pip install --upgrade pip; \
		$(PYTHON) -m pip install -r requirements.txt; \
		echo "✓ venv created and dependencies installed"; \
	fi

.PHONY: lint
lint: prepare
	$(PYTHON) -m ruff check src/

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
