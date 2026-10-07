#!/usr/bin/env bash
# setup.sh — one-shot setup for the hybrid origami pipeline
#
# Run from the anveshan repo root:
#   bash research/origami_hybrid/setup.sh
#
# What it does:
#   1. Initialises + updates git submodules (FoldingAgent + FoldingAgentSimulator)
#   2. Installs FoldingAgentSimulator in editable mode
#   3. Installs FoldingAgent in editable mode (picks up local simulator)
#   4. Installs hybrid pipeline Python dependencies
#   5. Prints next steps

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "=== Hybrid Origami Pipeline Setup ==="
echo "Repo root: $REPO_ROOT"
echo ""

# 1. Submodules
echo "[1/4] Initialising git submodules..."
cd "$REPO_ROOT"
git submodule update --init --recursive research/origami_hybrid/vendor/FoldingAgent
git submodule update --init --recursive research/origami_hybrid/vendor/FoldingAgentSimulator
echo "      Done."

# 2. Install simulator
echo "[2/4] Installing FoldingAgentSimulator (editable)..."
pip install -e "$SCRIPT_DIR/vendor/FoldingAgentSimulator" --quiet
echo "      Done."

# 3. Install FoldingAgent
echo "[3/4] Installing FoldingAgent (editable)..."
pip install -e "$SCRIPT_DIR/vendor/FoldingAgent" --quiet
echo "      Done."

# 4. Hybrid pipeline deps
echo "[4/4] Installing hybrid pipeline dependencies..."
pip install "av>=13.0" pillow numpy pydantic python-dotenv "google-genai>=0.3" --quiet
echo "      Done."

echo ""
echo "=== Setup complete ==="
echo ""
echo "Next steps:"
echo "  1. Copy .env.example to .env and fill in your API keys:"
echo "     cp $SCRIPT_DIR/.env.example $SCRIPT_DIR/.env"
echo ""
echo "  2. Set HYBRID_MODEL in .env (default: gemini-3.8-flash)"
echo "     For FoldingAgent, set ANTHROPIC_API_KEY and export it in your shell:"
echo "       export ANTHROPIC_API_KEY=your-key"
echo ""
echo "  3. Drop your origami video somewhere and run:"
echo "     python $SCRIPT_DIR/pipeline.py extract-frames --video <video> --output data/origami/"
