# Yasin-MCP Operational Runbook

**Status:** CONFIRMED against post-P2 implementation. Optional live steps are marked.

## 1. Installation

Supported Python (CI matrix): **3.10, 3.11, 3.12**.

Declared package range: `requires-python = ">=3.10"` for normal supported CPython environments. Native Termux Python 3.14 is **not currently a supported or verified runtime**; see §8.

```bash
git clone https://github.com/yusi20006-max/Yasin-MCP.git
cd Yasin-MCP
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

Runtime dependency: `mcp>=2,<3`, `PyYAML>=6,<7`.
Dev: pytest, ruff, mypy, bandit, types-PyYAML.

Console entrypoint: `yasin-mcp` → `yasin_mcp.server.cli:main`.

## 2. Running the server (stdio)

```bash
yasin-mcp
# or
python -m yasin_mcp
```

The process speaks MCP over **stdin/stdout**. Do not attach interactive prompts.

### Environment

| Variable / config | Required | Purpose |
|-------------------|----------|---------|
| GitHub token via `ServerConfig` / env used by config | No | Higher GitHub API rate limits (read-only) |
| `PATH` containing `yasin-operations` | No | Registers optional Operations tools |

Default CI and local unit tests do **not** require secrets.

## 3. Diagnostics

### Capability surface

```python
from yasin_mcp.server.runtime import ServerRuntime

rt = ServerRuntime.create()
print(rt.surface_info())
# package_version, capability_surface_version, operations_available, prefixes...
print(rt.capability_catalog())
```

### Tool discovery (MCP client)

Use any MCP stdio client: `initialize` → `list_tools`.
Expect non-empty catalog. `yasin_operations_*` present only if `operations_available` is true.

### Logs

Structured JSON logs via `yasin_mcp` logger. Correlation field: `request_id` when a scope is active.
Sensitive keys (`token`, `secret`, `password`, …) are redacted.

### Operations availability

```python
rt.surface_info()["operations_available"]  # PATH check only; does not launch gateway
```

### Cryptography / MCP import diagnostic

On platforms where the `cryptography` native extension may fail to load,
run these checks before diagnosing Yasin-MCP itself:

```bash
python -c "import cryptography; print(cryptography.__version__)"
python -c "from cryptography.hazmat.bindings._rust import exceptions; print('rust OK')"
python -c "import mcp; print('mcp import OK')"
python -c "from yasin_mcp.server.cli import main; print('CLI import OK')"
```

A `dlopen` / `PyLong_Type` failure while importing the Rust extension
indicates an environment/ABI dynamic-linking problem, not a Yasin-MCP
CLI logic error. Native Termux Python 3.14.x is currently outside the
verified runtime boundary for this project.

## 4. Failure modes

| Condition | Behavior | Evidence class |
|-----------|----------|----------------|
| Missing network (GitHub/docs) | Structured upstream / unavailable errors | UNIT + OPTIONAL_LIVE |
| GitHub 403/429 | Bounded retries (max 2), then `RateLimitedError` | UNIT (policy) |
| Missing registry file | `UnavailableDependencyError` / tools may report unresolved | UNIT |
| Malformed registry YAML | `ValidationError` | UNIT |
| Empty `projects: []` | Empty list; evidence may be unresolved | UNIT |
| `yasin-operations` absent | Tools not registered; runtime healthy | UNIT + LIVE_RUNTIME |
| Gateway timeout | `TimeoutMcpError` | UNIT |
| Invalid tool args | Validation / MCP error; process stays up | LIVE_RUNTIME |
| Unknown tool | MCP protocol error | LIVE_RUNTIME |
| Native Termux cryptography ABI failure | `import mcp` / CLI startup fails with `PyLong_Type` | ENVIRONMENT (unsupported) |

## 5. Evidence classes (do not conflate)

| Label | What it means |
|-------|----------------|
| **DEFAULT_CI** | Secret-free: ruff, mypy, bandit, pytest |
| **UNIT / MOCK** | Fake requesters, in-memory docs |
| **LIVE_RUNTIME** | Real `yasin-mcp` stdio + MCP SDK client |
| **OPTIONAL_LIVE** | Real network to GitHub/YASIN-DOCS when token/network available |
| **UNRESOLVED** | Could not be determined (e.g. no Hermes install) |

Optional evidence is **never** required for default CI green.

## 6. Quality commands

```bash
ruff check .
ruff format --check .
mypy src
bandit -q -ll -r src
pytest --cov=yasin_mcp
python -m compileall -q src
# Live MCP harness (no token required for discovery path):
pytest tests/test_live_mcp_client_harness.py -v
```

## 7. Common troubleshooting

1. **Empty tools / process exits** — ensure package installed (`pip install -e .`) and entrypoint is `yasin-mcp` or `python -m yasin_mcp`.
2. **Rate limited** — set a read-only GitHub token in config; retries are bounded (2).
3. **No operations tools** — install/publish `yasin-operations` on PATH; re-check `surface_info()["operations_available"]`.
4. **Registry unresolved** — YASIN-DOCS must expose a candidate registry path; missing file is expected UNRESOLVED, not a crash.
5. **`ImportError: cannot locate symbol "PyLong_Type"`** while importing `cryptography` or `mcp` — treat this as an environment/platform compatibility failure. Do not modify Yasin-MCP cryptographic behavior to bypass it.

## 8. Termux / Android compatibility boundary

### Native Termux (Python 3.14.x aarch64)

**Unsupported / unverified.** The target environment was verified as
Android/aarch64/native Termux with Python 3.14.6, `cryptography==50.0.0`,
`mcp==2.0.0`, and a shared Python build (`Py_ENABLE_SHARED=1`) providing
`libpython3.14.so`. `pip check` reports no broken requirements.

Nevertheless, importing `mcp` fails through the Rust extension in
`cryptography` with:

```text
ImportError: dlopen failed: cannot locate symbol "PyLong_Type"
referenced by .../cryptography/hazmat/bindings/_rust.abi3.so
```

This occurs during test collection for runtime-dependent tests, before
those tests can execute. It is independent of the Yasin-MCP CLI argument
handling fixed in PR #77.

Do not disable TLS/certificate verification, monkey-patch cryptography,
force incompatible native libraries, or replace the cryptographic
implementation with an unverified fallback. Those are not valid fixes
for this compatibility boundary.

### Candidate workaround: proot-distro Debian

A Debian userland inside Termux is a candidate workaround. It must be
verified on the target device before being described as a supported
runtime.

On the Termux host:

```bash
pkg update
pkg install proot-distro git
proot-distro install debian
proot-distro login debian
```

Inside Debian proot:

```bash
apt update
apt install -y python3 python3-venv python3-pip git
git clone https://github.com/yusi20006-max/Yasin-MCP.git
cd Yasin-MCP
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .
```

Verify before treating the workaround as confirmed:

```bash
python -c "import cryptography; print(cryptography.__version__)"
python -c "from cryptography.hazmat.bindings._rust import exceptions; print('rust OK')"
python -c "import mcp; print('mcp import OK')"
python -c "from yasin_mcp.server.cli import main; print('CLI import OK')"
yasin-mcp --version
yasin-mcp --help
```

Project Python constraints (`>=3.10`) and the CI matrix (3.10–3.12)
remain unchanged. The Termux limitation is platform/ABI-specific.
