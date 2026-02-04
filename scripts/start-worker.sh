#!/usr/bin/env bash
# Start the worker in a reproducible way from project root.
# - Activates .venv if present
# - Installs Python deps if missing
# - Starts the worker with REDIS_URL

set -euo pipefail

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT_DIR"

# Activate venv if available
if [ -f ".venv/bin/activate" ]; then
  # shellcheck source=/dev/null
  source .venv/bin/activate
else
  echo ".venv not found; create one with: python3 -m venv .venv"
  exit 1
fi

echo "Using python: $(which python) ($(python --version 2>&1))"
echo "Using pip: $(which pip) ($(pip --version 2>&1))"

# Install requirements if redis client is not present
if ! pip show redis >/dev/null 2>&1; then
  echo "Installing Python requirements..."
  pip install -r requirements.txt
  pip install redis
fi

# Default REDIS_URL if not provided
REDIS_URL="${REDIS_URL:-redis://localhost:6379}"

echo "Starting worker with REDIS_URL=$REDIS_URL"
exec env REDIS_URL="$REDIS_URL" python scaffold/worker/worker.py
#!/usr/bin/env bash
# Start the worker in a reproducible way from project root.
# - Activates .venv if present
# - Installs Python deps if missing
# - Starts the worker with REDIS_URL

set -euo pipefail

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT_DIR"

# Activate venv if available
if [ -f ".venv/bin/activate" ]; then
  # shellcheck source=/dev/null
  source .venv/bin/activate
else
  echo ".venv not found; create one with: python3 -m venv .venv"
  exit 1
fi

echo "Using python: $(which python) ($(python --version 2>&1))"
echo "Using pip: $(which pip) ($(pip --version 2>&1))"

# Install requirements if redis client is not present
if ! pip show redis >/dev/null 2>&1; then
  echo "Installing Python requirements..."
  pip install -r requirements.txt
  pip install redis
fi

# Default REDIS_URL if not provided
REDIS_URL="${REDIS_URL:-redis://localhost:6379}"

echo "Starting worker with REDIS_URL=$REDIS_URL"
exec env REDIS_URL="$REDIS_URL" python scaffold/worker/worker.py
