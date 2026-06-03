#!/usr/bin/env bash
# Run the automated demo generator.
# Usage: ./run.sh --plan <path/to/demo_plan.yaml> [--live] [--no-start] [--port 3000]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ ! -f "$SCRIPT_DIR/venv/bin/activate" ]; then
    echo "venv not found. Run ./setup.sh first."
    exit 1
fi

source "$SCRIPT_DIR/venv/bin/activate"
cd "$SCRIPT_DIR"
python main.py "$@"
