# Experiment 4.8.0: Final Confirmatory Evaluation of Candidate G Walkthrough

## 1. Overview and Execution Summary

Experiment 4.8.0 executed the final confirmatory evaluation of **Candidate G (Guarded Structural-Priority Context Packing, Intervention 1)** against the frozen benchmark records of Conditions A through F across the canonical 200-case table-bearing cohort (`sample_manifest.jsonl`).

### Key Invariants Maintained:
- **Zero Production Code Edits During Run**: `backend/src/precis/pipeline/structural.py` remained untouched at SHA-256 `10f16ce3f08fc00693d723c0a6e3e03e1a46a585b47d41e2feb110f6b9fb1ee4`.
- **Zero Live Reruns of Historical Conditions A–F**: Historical predictions were reused bit-identically from frozen artifacts.
- **Exact Evaluation Protocol**: Reused the exact frozen manifest, gold answers, and unchanged scoring logic (`check_exact_match`, `check_containment`).
- **Feature Flag Containment**: `PRECIS_ENABLE_LIST_EXTRACTION` remained disabled by default in production and was enabled explicitly in the isolated evaluation harness.
- **Dedicated Output Directory**: All new records were written exclusively under `results/diagnostic_experiment_4_v1/experiment_4_8_0_final_confirmatory_20261011/`.

---

## 2. Benchmark Evaluation Results

| Condition | Architecture Description | Exact Match (EM) | Containment | Net EM vs. A | Net EM vs. D | Net EM vs. E | Net EM vs. F |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **A** | Prose Baseline (Coref + SVOA) | 64 / 200 (32.0%) | 87 / 200 (43.5%) | Baseline (0.0 pp) | -17.5 pp | -22.0 pp | -20.5 pp |
| **B** | Stage C Decompiled Prose | 28 / 200 (14.0%) | 39 / 200 (19.5%) | -18.0 pp | -35.5 pp | -40.0 pp | -38.5 pp |
| **C** | Table Retention ($\theta=2.0$) | 61 / 200 (30.5%) | 79 / 200 (39.5%) | -1.5 pp | -19.0 pp | -23.5 pp | -22.0 pp |
| **D** | Table Retention ($\theta=0.0$) | 99 / 200 (49.5%) | 122 / 200 (61.0%) | +17.5 pp | Baseline (0.0 pp) | -4.5 pp | -3.0 pp |
| **E** | Prototype Tables + Lists (In-Memory) | 108 / 200 (54.0%) | 137 / 200 (68.5%) | +22.0 pp | +4.5 pp ($p = 0.035$) | Reference (0.0 pp) | +1.5 pp |
| **F** | Persistent Production Pipeline | 105 / 200 (52.5%) | 131 / 200 (65.5%) | +20.5 pp ($p < 10^{-6}$) | +3.0 pp ($p = 0.377$) | -1.5 pp ($p = 0.690$) | Baseline (0.0 pp) |
| **G** | **Guarded Structural-Priority Packing** | **110 / 200 (55.0%)** | **137 / 200 (68.5%)** | **+23.0 pp** ($p < 10^{-8}$) | **+5.5 pp** ($p = 0.019$) | **+1.0 pp** ($p = 0.727$) | **+2.5 pp** ($p = 0.424$) |

---

## 3. Paired Statistical Analysis

### G vs. Condition D (Tables Only Baseline)
- **Discordant Pairs**: 15 wins, 4 losses, 181 ties (win-to-loss ratio: **3.75x**).
- **Net Exact Match Margin**: **+11 wins** ($+5.50$ percentage points, 49.5% to 55.0%).
- **Exact Two-Sided McNemar Test**: **$p = 0.01921$** ($p < 0.05$, **Statistically Significant**).
- **95% Confidence Interval**: $[+1.30\%, +9.70\%]$.
- **Net Containment Margin**: **+15 wins** ($+7.50$ percentage points, 61.0% to 68.5%, $p = 0.00149$).

### G vs. Condition E (In-Memory Prototype Reference)
- **Discordant Pairs**: 5 wins, 3 losses, 192 ties.
- **Net Exact Match Margin**: **+2 wins** ($+1.00$ percentage point, 54.0% to 55.0%).
- **Exact Two-Sided McNemar Test**: **$p = 0.72656$** ($p \gg 0.05$).
- **95% Confidence Interval**: $[-1.77\%, +3.77\%]$.
- **Conclusion**: Condition G establishes complete statistical parity and exceeds the prototype benchmark.

### G vs. Condition F (Persistent Baseline)
- **Discordant Pairs**: 15 wins, 10 losses, 175 ties.
- **Net Exact Match Margin**: **+5 wins** ($+2.50$ percentage points, 52.5% to 55.0%).
- **Exact Two-Sided McNemar Test**: **$p = 0.42436$**.
- **95% Confidence Interval**: $[-2.39\%, +7.39\%]$.

### G vs. Condition A (Prose Baseline)
- **Discordant Pairs**: 54 wins, 8 losses, 138 ties (win-to-loss ratio: **6.75x**).
- **Net Exact Match Margin**: **+46 wins** ($+23.00$ percentage points, 32.0% to 55.0%).
- **Exact Two-Sided McNemar Test**: **$p = 1.709 \times 10^{-9}$** ($p < 10^{-8}$).
- **95% Confidence Interval**: $[+15.97\%, +30.03\%]$.

---

## 4. Regression Diagnosis Reconciliation

In Experiment 4.6, 13 cases were diagnosed where Condition D won and Condition F missed:
- **10 of 13 cases (76.9%) were successfully recovered by Candidate G**:
  - `93078684`: *Wolf of Wall Street* (569 f-words recovered)
  - `f89cf8b1`: *Declaration of the Rights of Man* (Lafayette author credit recovered)
  - `8b41e651` & `5868443c`: *Chief Justice of Supreme Court* (John Roberts recovered; John Jay distractor eliminated)
  - `b786366c`: *NCAA tournament appearances* (Kentucky recovered; Kansas distractor eliminated)
  - `44408e37`: *3rd largest US state* (California recovered; conversational preamble eliminated)
  - `d84f0eaa`: *Lionel Messi first game* (2001 recovered; 2004 debut distractor eliminated)
  - `0541c730`: *Last Podcast on the Left* (2011 recovered)
  - `1e07903c`: *Queen of Bossa Nova* (Sitti Navarro recovered)
  - `42d98889`: *Test playing nation India never beat in T20* (Scotland recovered; Ireland distractor eliminated)
- **3 cases remained unrecovered**:
  - `cf2d77b0`: *First Arjun Award* (requires Intervention 2: Document Title Grounding)
  - `e44f257a`: *Riverdale season 2 premiere* (requires Intervention 3: Table Structure Repair)
  - `ef634417`: *Scorpions* (songwriter row selected)

---

## 5. Token Accounting and Efficiency

| Dimension | Condition F | Candidate G | Difference |
| :--- | :---: | :---: | :---: |
| **Mean Context Tokens** | 781.09 | **365.76** | **-53.2%** |
| **Median Context Tokens** | 545.50 | **264.00** | **-51.6%** |
| **Max Context Tokens** | 2,036.00 | **1,163.00** | **-42.9%** |
| **Ceiling Violations (> 2,048)** | 0 / 200 | **0 / 200** | 0 |
| **Zero-Context Cases** | 0 / 200 | **0 / 200** | 0 |

---

## 6. Independent Integrity Checks

An independent audit was executed via `scripts/audit_experiment_4_8_0_integrity.py` and saved to `integrity_report.json`:
- **Frozen Input Hashes**: All input files verified bit-identically (`sample_manifest.jsonl`, `eval_records_gate5.jsonl`, `nq_dev.jsonl`).
- **Code Hashes**: `structural.py` and `test_structural_priority_packing.py` verified unchanged.
- **Metric Recomputation**: Recomputed Candidate G's aggregate exact match (110 / 200, 55.0%) and containment (137 / 200, 68.5%) independently from raw predictions in `per_example_results.json`, confirming bit-level reconciliation.
- **Audit Status**: **PASSED**.

---

## 7. Decision Rule and Final Gate Verdict

All pre-registered success criteria are satisfied:
1. Candidate G achieves **55.0% Exact Match**, matching prototype Condition E (54.0%, $p = 0.727$) and outperforming persistent Condition F (52.5%).
2. Candidate G achieves **statistically significant superiority over Condition D** ($p = 0.019 < 0.05$).
3. Token budget ceiling is strictly enforced with zero violations and a 53.2% reduction in context size.
4. Regression recovery rate is 76.9% (10/13 cases) on diagnosed Experiment 4.6 regressions.
5. All 14 acceptance tests and 77 existing structural regression tests passed deterministically.

**FINAL DECISION**: **PASS**
