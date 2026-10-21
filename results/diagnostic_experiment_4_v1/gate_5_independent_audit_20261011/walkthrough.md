# Experiment 4.5.9: Gate 5 Independent Results Audit Walkthrough

## Summary of Completed Work

This walkthrough summarizes the execution and findings of **Experiment 4.5.9: Gate 5 Independent Results Audit**, which independently audited the results of the Experiment 4.5.6 Phase 2 production-path confirmatory evaluation.

The audit was executed under strict read-only constraints:
- Zero modifications to production source code (`backend/src/precis/`, `backend/main.py`).
- Zero live model inference calls, Ollama daemon invocations, or network requests.
- Zero modifications or rewrites to frozen historical datasets or Gate 5 Phase 2 evaluation outputs.
- Bit-identical independent recomputations of all evaluation metrics and statistical tests.

---

## Audit Artifacts Directory

All audit code and findings are recorded in:
`results/diagnostic_experiment_4_v1/gate_5_independent_audit_20261011/`

Files created:
1. `audit_gate_5.py`: Python audit script performing SHA-256 verifications, canonical scoring, paired McNemar tests, strata reconstruction, and regression context inspection.
2. `independent_metrics.json`: Complete independent JSON output containing exact match, containment, paired contingency tables, confidence intervals, strata breakdowns, and telemetry statistics.
3. `regression_reaudit.jsonl`: Detailed record-by-record analysis of all 13 F-versus-D regression cases.
4. `integrity_report.json`: Cryptographic integrity record confirming identical input/source hashes and compliance with constraints.
5. `independent_audit_report.md`: Formal markdown audit report documenting all phases, findings, and required corrections.
6. `walkthrough.md`: This document.

---

## Key Verification Results

### 1. Data Integrity and Provenance
- All 6 frozen input files matched their SHA-256 digests bit-for-bit.
- All 4 production source files matched their pre-audit SHA-256 digests bit-for-bit.
- All 200 cases matched `sample_manifest.jsonl` table-bearing cases in 1-to-1 order without omission or duplication.
- All 1,000 historical predictions (Conditions A through E) matched historical frozen evaluation files with 0 discrepancies.

### 2. Metric Recomputation
- **Condition F Performance:**
  - Exact Match: **52.5%** (105/200)
  - Containment: **65.5%** (131/200)
- **Baseline Contrasts:**
  - vs Condition A (Plain RAG, 32.0% EM): **$+20.5$ pp net gain** ($p = 1.673 \times 10^{-7}$, 95% CI: $[+13.26\%, +27.74\%]$). Statistically significant.
  - vs Condition D (Pure SVOA, 49.5% EM): **$+3.0$ pp net gain** ($p = 0.377086$, 95% CI: $[-2.53\%, +8.53\%]$). Not statistically significant at $\alpha = 0.05$.
  - vs Condition E (Ideal Bound, 54.0% EM): **$-1.5$ pp net delta** ($p = 0.690038$, 95% CI: $[-6.40\%, +3.40\%]$). Not statistically significant at $\alpha = 0.05$.

### 3. Stratum Targets
- **Stratum 1 (Stage C Regressions, $N=47$):** Recovered 38/47 cases (80.85%), exceeding the pre-registered $\ge 80\%$ recovery threshold.
- **Gate 2 List Subset ($N=31$):** Achieved 11/31 (35.48%), restoring list capability from Condition D's 0/31 (0.0%) and exactly matching Condition E's 11/31 (35.48%).

---

## Required Corrections Identified

The quantitative findings are valid, but the qualitative report requires three mandatory corrections:
1. **Equivalence Claim:** Rephrase "Condition F achieves statistical parity and equivalence with Condition E ($p=0.690$)" to "no statistically significant difference was detected".
2. **Chunk Truncation Refutation:** The report's claim that 5 regressions were caused by "top-3 chunk truncation" is refuted; all 13 cases had evidence in context. Real causes are table distractor/column confusion (6), formatting variations (3), conversational preambles (2), premise ambiguity (1), and SVOA prose scrambling (1).
3. **Budget and Latency Scope:** Clarify that the 2,048 ceiling bounds Stage 4 estimated context tokens, whereas raw prompt tokens include prompt overhead and subword tokenizer expansion. Clarify that latency measures Ollama generation time, not ingestion.

---

## Final Audit Verdict

**`PASS WITH CORRECTIONS`**
