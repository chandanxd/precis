#!/usr/bin/env bash
# Reproduction script for Précis Model-Selection Experiments
# Reproduces: Data preparation, Stage A screening, Stage B evaluation, Stage C prompt ablation, and Statistical analysis.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

cd "${PROJECT_ROOT}"

echo "=========================================================="
echo "Précis Model Selection Experiment Suite Reproduction"
echo "=========================================================="

export PYTHONPATH="${PROJECT_ROOT}/backend/src"
export MPLCONFIGDIR="/tmp/matplotlib"
export TRANSFORMERS_OFFLINE="1"
export HF_HUB_OFFLINE="1"
PYTHON="${PROJECT_ROOT}/backend/venv/bin/python"

# 1. Data Preparation and Context Caching
if [ ! -f "experiments/model_comparison/cached_contexts.jsonl" ]; then
    echo "[Step 1] Preparing cohorts and caching contexts..."
    ${PYTHON} experiments/model_comparison/prepare_data.py
else
    echo "[Step 1] Cached contexts already present. Skipping."
fi

# 2. Stage A: Development Screening
echo "[Step 2] Executing Stage A Development Screening..."
${PYTHON} experiments/model_comparison/run_experiment.py --stage a

# 3. Intermediate Analysis & Candidate Selection
echo "[Step 3] Running Stage A analysis..."
${PYTHON} experiments/model_comparison/analyze_results.py

# 4. Stage B: Held-out Evaluation
# Read selected candidate from results.json
SELECTED_CANDIDATE=$(${PYTHON} -c "import json; data=json.load(open('experiments/model_comparison/results.json')); print(data.get('stage_a', {}).get('selected_candidate') or '')")

if [ -n "${SELECTED_CANDIDATE}" ]; then
    echo "[Step 4] Running Stage B for Reference Model (qwen2.5-coder:7b)..."
    ${PYTHON} experiments/model_comparison/run_experiment.py --stage b --model qwen2.5-coder:7b

    echo "[Step 4] Running Stage B for Selected Candidate (${SELECTED_CANDIDATE})..."
    ${PYTHON} experiments/model_comparison/run_experiment.py --stage b --model "${SELECTED_CANDIDATE}"

    # 5. Stage C: Prompt Ablation
    echo "[Step 5] Running Stage C Concise Prompt on (${SELECTED_CANDIDATE})..."
    ${PYTHON} experiments/model_comparison/run_experiment.py --stage c --model "${SELECTED_CANDIDATE}"

    # 6. Final Statistical Analysis
    echo "[Step 6] Running final statistical analysis..."
    ${PYTHON} experiments/model_comparison/analyze_results.py
else
    echo "[Step 4] No candidate selected from Stage A. Running Reference Model control only."
    ${PYTHON} experiments/model_comparison/run_experiment.py --stage b --model qwen2.5-coder:7b
    ${PYTHON} experiments/model_comparison/analyze_results.py
fi

echo "=========================================================="
echo "Reproduction complete. Results written to experiments/model_comparison/results.json"
echo "=========================================================="
