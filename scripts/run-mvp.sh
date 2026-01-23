#!/usr/bin/env bash
set -euo pipefail

echo "[MVP] Activating conda environment: f5-tts" 
if command -v conda >/dev/null 2>&1; then
  . "$(conda info --base)/etc/profile.d/conda.sh" >/dev/null 2>&1 || true
  conda activate f5-tts || { echo "Failed to activate conda env 'f5-tts'"; exit 1; }
else
  echo "Conda not found in PATH. Ensure you activate the environment manually before running.";
fi

echo "[MVP] Running tts_article_generator with python interpreter: $(which python)"
python -m tts_article_generator "$@"
