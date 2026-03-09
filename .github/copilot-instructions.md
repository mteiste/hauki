# Project Instructions for GitHub Copilot

## Interaction Style

**Present Plans Before Permanent Changes**: Before initiating any actions that would result in permanent changes (file edits, deletions, system modifications), always present a clear plan and available options to the user first. Wait for confirmation before proceeding. This does not apply to read-only operations like searches, file reads, or running lint checks.

## Configuration Philosophy

**No Magic Defaults**: Always require explicit configuration. When creating Makefiles or configuration files, if required values are not defined, fail with clear error messages rather than silently using default values. Users should be forced to make conscious decisions about their configuration.

## Project Context

This is a Raspberry Pi Pico W MicroPython development project. The build system is Makefile-driven, and all host-specific configuration should be externalized to `config.mk` (which is gitignored).

## Development Environment

### Build System & Commands

**Always use Makefile targets**: When performing common tasks (linting, uploading, etc.), always use the appropriate make target instead of running commands directly. Only run commands directly if there's no make target that accomplishes the task.

Key make targets:

- `make lint` or `make lint-python` - Run Python linting with ruff
- `make lint-markdown` - Run markdown linting
- `make upload` - Upload files to Pico
- `make prepare` - Setup environment

The project's Python tools (ruff, ampy, etc.) are installed in `.venv` and should be invoked via make targets.

### MicroPython Support

The project uses MicroPython for Raspberry Pi Pico W. For IDE support (autocomplete, type hints):

- MicroPython stubs are installed in the virtual environment (`micropython-rp2-pico-w-stubs==1.20.0.post5`)
- VS Code is configured to use the project's `.venv` Python interpreter
- Type checking is set to "basic" mode to avoid excessive errors for MicroPython-specific code
- The stubs provide autocomplete for MicroPython modules like `machine`, `network`, `time`, etc.

### VS Code Configuration

Project-specific VS Code settings (`.vscode/settings.json` and `.vscode/extensions.json`) are committed to the repository as they define MicroPython environment setup. User-specific VS Code files remain gitignored.

## Coding Style

### Comments

**Explain Why, Not What**: Comments should explain the reasoning behind code, not describe what the code does.

Principles:

- **Remove "what" comments**: Don't describe what the code does if it's obvious from reading the code
- **Remove "how" comments**: Don't explain the mechanics of standard operations
- **Keep "why" comments**: Explain design decisions, constraints, or non-obvious choices
- **Keep constraint comments**: Document platform limitations or requirements (e.g., "MicroPython requires 9 elements")
- **Keep design pattern comments**: Explain sentinel values or special data structures (e.g., "Slot 0 is always None")

Examples to avoid:

```python
# Get current time
current_time = clock.utc_now_timestamp()

# Calculate the difference
time_diff = current_time - start_time

# Fetch data from API
data = api.get_data()
```

Preferred:

```python
# Offset by 1 for the None sentinel at index 0
slot_with_offset = slot_index + 1

# For display purposes, weekday recalculation can be skipped
local_weekday = weekday

# Ensure URL doesn't have trailing slash
if self.url.endswith('/'):
    self.url = self.url[:-1]
```

### Logging and Debugging

**Error-Only Logging**: This is an embedded device project - only log errors, not progress or success messages.

Principles:

- **Remove progress logging**: No prints like "Testing...", "Connecting...", "Successfully connected", "Display updated!"
- **Keep error logging**: Always log errors: "Error: WiFi connection failed", "Error: status 404", "Failed to sync RTC"
- **Minimal exceptions**: Critical system feedback like safe mode messages in boot.py are kept for debugging boot issues
- **Rationale**: Embedded devices have limited serial bandwidth and users only need to know when something goes wrong, not every successful operation

Examples to avoid:

```python
print("Testing WiFi connection...")
if wifi.connect():
    print("Successfully connected!")
```

Preferred:

```python
if not wifi.connect():
    print("Error: WiFi connection failed")
```

### Defensive Coding

**No Defensive Coding**: Assume configuration is done correctly. Don't add validation checks "just in case".

Principles:

- Don't check if config values exist unless there's a real current need
- Don't validate types or ranges unless actually required by the current implementation
- Fail fast and loud when something is genuinely wrong (let exceptions propagate)
- Don't add try/except blocks around everything preemptively

### Future-Proofing

**Implement Only What's Needed Now**: Don't add code for potential future use cases.

Principles:

- No placeholder methods (like empty cleanup methods)
- No unused variables or attributes "for later"
- No "just in case" parameters or configuration options
- If a method isn't called by current code, don't create it

### Control Flow Simplification

**Avoid Unnecessary Nesting**: When all branches return, avoid if/elif/else nesting.

Pattern:

```python
# Avoid nested conditions when all branches return
def get_data():
    data = None
    try:
        data = fetch_from_network()
    except Exception:
        pass

    if data is None:
        return None

    if not validate(data):
        return None

    # Success path at the end
    return process(data)
```

This approach keeps code flat and easier to read than deeply nested if/else structures.
