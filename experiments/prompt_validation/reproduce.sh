#!/usr/bin/env bash
# Reproduction script for Précis Confirmatory Answer-Formatting Experiment
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

cd "${PROJECT_ROOT}"

echo "=========================================================="
echo "Précis Confirmatory Answer-Formatting Experiment Reproduction"
echo "=========================================================="

export PYTHONPATH="${PROJECT_ROOT}/backend/src"
export MPLCONFIGDIR="/tmp/matplotlib"
export TRANSFORMERS_OFFLINE="1"
export HF_HUB_OFFLINE="1"
PYTHON="${PROJECT_ROOT}/backend/venv/bin/python"

# 1. Cohort selection and context caching
if [ ! -f "experiments/prompt_validation/cached_contexts.jsonl" ]; then
    echo "[Step 1] Preparing cohort and caching contexts..."
    ${PYTHON} experiments/prompt_validation/prepare_data.py
else
    echo "[Step 1] Cached contexts already exist. Skipping context generation."
fi

# 2. Factorial execution across all 8 conditions (800 evaluations)
echo "[Step 2] Executing factorial model evaluations..."
${PYTHON} experiments/prompt_validation/run_experiment.py

# 3. Statistical analysis and error report generation
echo "[Step 3] Running statistical analysis and hypothesis tests..."
${PYTHON} experiments/prompt_validation/analyze_results.py

echo "=========================================================="
echo "Reproduction complete. Results written to experiments/prompt_validation/results.json"
echo "=========================================================="
