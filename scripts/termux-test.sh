#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ "$(uname -o 2>/dev/null || true)" != "Android" && -z "${TERMUX_VERSION:-}" ]]; then
  echo "ERROR: this script is intended for Termux/Android."
  exit 1
fi

if [[ ! -d .venv ]]; then
  echo "ERROR: .venv not found. Create the project virtualenv first."
  exit 1
fi

source .venv/bin/activate

PYTHON_BIN="$(command -v python)"
PYTHON_VERSION="$(python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"

if [[ "$PYTHON_VERSION" != "3.14" ]]; then
  echo "ERROR: Yasin-MCP Termux target is Python 3.14; found $PYTHON_VERSION."
  exit 1
fi

# Termux's Python shared library exports CPython symbols needed by
# cryptography's abi3 Rust extension, but Android's dynamic loader does not
# resolve them automatically for the extension. Preloading libpython makes
# the dependency visible to the extension without changing application code.
PYTHON_PREFIX="$(python -c 'import sys; print(sys.prefix)')"
LIBPYTHON="$PYTHON_PREFIX/lib/libpython3.14.so"
if [[ ! -f "$LIBPYTHON" ]]; then
  LIBPYTHON="${PREFIX:-}/lib/libpython3.14.so"
fi

if [[ ! -f "$LIBPYTHON" ]]; then
  echo "ERROR: cannot find libpython3.14.so."
  exit 1
fi

export LD_PRELOAD="$LIBPYTHON${LD_PRELOAD:+:$LD_PRELOAD}"

python - <<'PY'
import cryptography
import mcp
print("Termux compatibility: OK")
print("Python:", __import__("sys").version.split()[0])
print("cryptography:", cryptography.__version__)
print("mcp:", mcp.__version__ if hasattr(mcp, "__version__") else "installed")
PY

pytest -q "$@"
