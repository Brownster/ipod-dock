#!/usr/bin/env bash
# Simple test script to verify the python-gpod bindings are available.
# Run this after install.sh to ensure the virtual environment has
# functioning bindings.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -d "$PROJECT_DIR/.venv" ]; then
    source "$PROJECT_DIR/.venv/bin/activate"
fi

python - <<'PY'
import sys
try:
    import gpod  # type: ignore
except Exception as exc:
    print(f"Failed to import gpod bindings: {exc}")
    sys.exit(1)

print(f"gpod bindings imported from {getattr(gpod, '__file__', 'unknown')}")
try:
    gpod.Database("/tmp")
except Exception as exc:
    print(f"gpod.Database call raised {exc.__class__.__name__}: {exc}")
else:
    print("gpod.Database call succeeded")
print("Bindings test complete")
PY
