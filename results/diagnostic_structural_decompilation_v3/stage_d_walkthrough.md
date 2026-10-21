# Précis Experiment 3: Stage D Forensic Walkthrough

## Overview

This walkthrough documents the forensic investigation artifacts produced during Stage D of Précis Experiment 3 (Structural Document Decompilation Forensics). All analyses were conducted strictly read-only under frozen conditions without modifying production code, benchmark data, or running additional LLM inference.

---

## 1. Generated Forensic Artifacts & Hashes

All new artifacts are located under `results/diagnostic_structural_decompilation_v3/`:

| Artifact Path | SHA-256 Checksum | Size | Purpose |
| :--- | :--- | :--- | :--- |
| `stage_d_forensic_case_audit.jsonl` | `f31c828ca1e3a1f8197779f7ce2eb7756f70914d9b04fc4948a60ccdbef2ca13` | 134,228 bytes | Structured, 1-record-per-case forensic trace covering all 61 prioritized cases (47 regressions, 11 recoveries, 4 B-vs-C divergences). |
| `stage_d_root_cause_summary.json` | `5c7ef95a709087cf289cb83e584f933f6771d996cb28976b7724bc29bbd69784` | 3,291 bytes | Aggregated counts by root-cause category, evidence survival status, confidence, and Pattern 1 ablation metrics. |
| `stage_d_forensic_report.md` | `870ae3d735bbffb43d04410f5296163d3f53e9432914025c188b64525babd11e` | 34,247 bytes | Full forensic report answering questions A through H, auditing representative cases, and evaluating the decision gate. |
| `stage_d_walkthrough.md` | *(This file)* | — | Reproducible guide and verification commands for reviewers. |

---

## 2. Reproducible Verification Commands

All forensic findings can be independently reproduced using the following read-only CLI commands.

### 2.1 Verify Input Integrity & Hashes
```bash
sha256sum \
  results/diagnostic_structural_decompilation_v3/sample_manifest.jsonl \
  results/diagnostic_structural_decompilation_v3/eval_records_stage_c.jsonl \
  results/diagnostic_structural_decompilation_v3/historical_exclusions.json \
  results/diagnostic_structural_decompilation_v3/stage_c_final_results_report.md \
  scripts/eval_structural_decompilation_v3.py \
  backend/data/nq_subset/nq_dev.jsonl
```
*Expected*: All hashes match the Stage C preflight record exactly.

### 2.2 Verify Reconciled Cohort Metrics
```bash
python3 -c "
import json
with open('results/diagnostic_structural_decompilation_v3/eval_records_stage_c.jsonl') as f:
    recs = [json.loads(l) for l in f if l.strip() and json.loads(l).get('type') == 'sample_record' and json.loads(l).get('stratum') == 'table_bearing']

em_a = sum(1 for r in recs if r['cond_a']['exact_match'])
em_b = sum(1 for r in recs if r['cond_b']['exact_match'])
em_c = sum(1 for r in recs if r['cond_c']['exact_match'])
losses = sum(1 for r in recs if r['cond_a']['exact_match'] and not r['cond_b']['exact_match'])
wins = sum(1 for r in recs if not r['cond_a']['exact_match'] and r['cond_b']['exact_match'])
b_c_diff = sum(1 for r in recs if r['cond_b']['predicted_answer'] != r['cond_c']['predicted_answer'])

print(f'Table Stratum EM: A={em_a}/200 ({em_a/2:.1f}%), B={em_b}/200 ({em_b/2:.1f}%), C={em_c}/200 ({em_c/2:.1f}%)')
print(f'Discordant pairs: Losses={losses}, Wins={wins}')
print(f'B vs C prediction differences: {b_c_diff}')
"
```
*Expected*:
- EM: A = 64 (32.0%), B = 28 (14.0%), C = 28 (14.0%).
- Discordant: Losses = 47, Wins = 11.
- B vs C differences = 4.

### 2.3 Verify Root Cause Summary Distribution
```bash
python3 -c "
import json
with open('results/diagnostic_structural_decompilation_v3/stage_d_root_cause_summary.json') as f:
    s = json.load(f)
print('Primary Causes (P1 Regressions):')
for k, v in s['primary_root_cause_distribution_p1_regressions_only'].items():
    print(f'  - {k}: {v} ({v/47:.1%})')
print('\nMissing Evidence vs Present in Context:')
for k, v in s['regression_evidence_survival_breakdown_p1'].items():
    print(f'  - {k}: {v}')
"
```
*Expected*:
- Missing Evidence in Final Context: 44 (93.6%).
- Evidence Present in Final Context: 3 (6.4%).
- Row/fact selection failure: 24 (51.1%).
- Table/list extraction omission: 20 (42.6%).

### 2.4 Verify Pattern 1 Sortable-Name Ablation Reality
```bash
python3 -c "
import json
with open('results/diagnostic_structural_decompilation_v3/stage_d_root_cause_summary.json') as f:
    s = json.load(f)
p1 = s['pattern_1_ablation_forensics']
print('Cases with actual cell transformations:', p1['cases_with_actual_cell_text_transformation'])
print('Case IDs:', p1['case_ids_with_transformations'])
print('EM impact:', p1['em_impact_from_transformations'])
print('Prediction differences:', p1['cases_with_prediction_divergence_between_b_and_c'])
print('Cause of prediction differences:', p1['cause_of_prediction_divergence'])
"
```
*Expected*: Exactly 3 cases had text transformations, with 0 EM impact. The 4 prediction differences were caused by unconditional `(name_normalized: true)` prompt string injection.

### 2.5 Run Automated Quality Assertion Suite
```bash
python3 /home/chandan/.gemini/antigravity/brain/751ccd8a-25c4-4c51-851b-39357f417fbd/scratch/verify_quality_checks.py
```
*Expected*: All 6 checks pass with zero assertion errors.

---

## 3. Decision Gate Summary

**Decision**: `ROOT CAUSE SUFFICIENTLY ESTABLISHED`  
**Core Finding**: Stage C failed due to upstream context starvation: heuristic table selection and hard top-5 row pruning discarded 93.6% of answer-bearing evidence before language model inference.
