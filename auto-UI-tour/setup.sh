#!/usr/bin/env bash
# Sets up the autodemo-toolkit Python venv with all required dependencies.
# Run once from the autodemo-toolkit/ directory.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== autodemo-toolkit setup ==="

# Create venv inside the toolkit directory
python3 -m venv "$SCRIPT_DIR/venv"
source "$SCRIPT_DIR/venv/bin/activate"

pip install --upgrade pip --quiet
pip install -r "$SCRIPT_DIR/requirements.txt"
playwright install chromium

# Check ffmpeg
if ! command -v ffmpeg &>/dev/null; then
    echo ""
    echo "WARNING: ffmpeg not found. Install it before recording:"
    echo "  sudo apt install ffmpeg    (Debian/Ubuntu)"
    echo "  brew install ffmpeg        (macOS)"
else
    echo "ffmpeg: $(ffmpeg -version 2>&1 | head -1)"
fi

echo ""
echo "Setup complete."
echo "Write a plan (see templates/demo_plan.yaml), then run:  ./run.sh --plan <your_plan.yaml>"
