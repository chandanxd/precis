# Diagnostic Probe D.2: Walkthrough & Verification Guide

This guide provides reproducible commands for reviewing and verifying the results of **Diagnostic Probe D.2: Markdown Table Retention with Header Preservation**.

---

## 1. Executive Summary & Decision Gate

- **Cohort**: 200 frozen table/list confirmatory cases from Précis Experiment 3.
- **Decision Gate Determination**: **`STRUCTURE RETENTION IMPROVES EVIDENCE RECALL`**
- **Core Results**:
  - **Representation Isolation (Primary $\theta=2.0$)**: GFM Markdown table representation jumps answer retrieval recall from **31.0% (62/200)** in Condition B to **54.0% (108/200)** (+23.0 pp gain) under the **identical** table-selection threshold ($\theta=2.0$).
  - **Regression Recovery**: Recovers **27 of 47 Stage C regressions (57.4%)** in Condition D2 Primary (vs. 6.4% in Condition B and 38.3% in D.1 best).
  - **Deep Row Truncation Resolved**: 100% of rows in selected tables are preserved within the 500-token cap (2,830 / 2,830 source rows rendered).
  - **Token Efficiency**: Mean context length is **227.9 tokens**, which is **63.2% lower** than Condition A (618.8 tokens). Maximum context length was 1,215 tokens; zero cases exceeded the 2048-token context ceiling.
  - **Upper-Bound Potential ($\theta=0.0$ + Lists)**: Achieves **200 / 200 (100.0%)** total evidence recall and **47 / 47 (100.0%)** regression recovery at **429.6 mean tokens** (-30.6% below Condition A).

---

## 2. Artifact Inventory & Cryptographic Hashes

All diagnostic artifacts generated in `results/diagnostic_structural_decompilation_v3/`:

| Artifact Path | SHA-256 Checksum | Description |
| :--- | :--- | :--- |
| `stage_d2_case_audit.jsonl` | `2e13ccec907f7e5db2d0e5c229dbc283db00c2cc2c68e85e6a793858c03af470` | Case-level audit (200 records; all 4 conditions audited) |
| `stage_d2_table_conversion_audit.jsonl` | `05414212fa8b7a571512a1282a9530de32b7bdf9a5e59cfbf022ecf84341d430` | Table-level audit (164 source tables; 100% conversion verified) |
| `stage_d2_summary.json` | `00b97c858c346691282bb29c482deb1a13461b80ebfb43f95fd002a872fea6a8` | Reconciled summary metrics, token distributions, and cohort breakdowns |
| `stage_d2_report.md` | `c1fcbe78e9f7352b21cc4ee02263c08462774124ec265d64643515d033619f28` | Comprehensive forensic diagnostic report |
| `stage_d2_walkthrough.md` | *(This file)* | Reviewer walkthrough and reproducible verification guide |

---

## 3. Verification Commands

### Step 1: Verify Input Hashes (Strict Provenance)
Ensure all frozen baseline inputs match preflight checksums:

```bash
sha256sum \
  results/diagnostic_structural_decompilation_v3/sample_manifest.jsonl \
  results/diagnostic_structural_decompilation_v3/eval_records_stage_c.jsonl \
  results/diagnostic_structural_decompilation_v3/stage_d1_evidence_audit.jsonl \
  results/diagnostic_structural_decompilation_v3/stage_d1_retrieval_sweep.jsonl \
  results/diagnostic_structural_decompilation_v3/stage_d1_summary.json \
  scripts/eval_structural_decompilation_v3.py \
  backend/data/nq_subset/nq_dev.jsonl
```

Expected output:
```
011553c0725621b7dda73aad12254d100e6fc15f49a5f80f4524156eb4e25db7  .../sample_manifest.jsonl
e10ea38f7cc7cfa9a98d494851de8c41c322b5f148dfff653077193917933687  .../eval_records_stage_c.jsonl
916d9ae633fba042c464ad7739f619ce38be733ef6c79b828b88a74ab5c673b7  .../stage_d1_evidence_audit.jsonl
9885b3a5b9fdf2466aba6609e9f940d4046a32fe091ddd05f42abf36f865b2b5  .../stage_d1_retrieval_sweep.jsonl
c312cb9aaac80e6ea56f6d90410a9e521dfedc18015f64c51b532c0d63b0e73b  .../stage_d1_summary.json
ad56761db55fc9693526fe5c51d0db58c482c288525838d0b93fd240c21ac0e4  scripts/eval_structural_decompilation_v3.py
14efc255a596433d6bf10dd853a1915474a5d3f6b47c593f77911ab4bb8eb491  backend/data/nq_subset/nq_dev.jsonl
```

### Step 2: Programmatic Quality Checks
Verify dataset invariants, unique table mappings, and row preservation:

```bash
python3 -c "
import json

with open('results/diagnostic_structural_decompilation_v3/stage_d2_case_audit.jsonl') as f:
    cases = [json.loads(line) for line in f]
with open('results/diagnostic_structural_decompilation_v3/stage_d2_table_conversion_audit.jsonl') as f:
    tables = [json.loads(line) for line in f]

print(f'Total Cases Audited: {len(cases)} (Unique IDs: {len(set(c[\"case_id\"] for c in cases))})')
print(f'Total Tables Audited: {len(tables)}')
print(f'Source Rows vs. Rendered Rows: {sum(t[\"original_row_count\"] for t in tables)} vs. {sum(t[\"rendered_row_count\"] for t in tables)}')
print(f'Conversion Failures: {sum(1 for t in tables if t[\"conversion_status\"] != \"SUCCESS\")}')
"
```

Expected output:
```
Total Cases Audited: 200 (Unique IDs: 200)
Total Tables Audited: 164
Source Rows vs. Rendered Rows: 2830 vs. 2830
Conversion Failures: 0
```

### Step 3: Comparative Performance Table
Print the summary table comparing Baseline A, Baseline B, Probe D.1, and Condition D2:

```bash
python3 -c "
import json
with open('results/diagnostic_structural_decompilation_v3/stage_d2_summary.json') as f:
    d = json.load(f)

conds = d['conditions_evaluated']
print(f'{\"Condition\":<35} | {\"Recall\":<8} | {\"Mean Tok\":<9} | {\"P1 Rec (47)\":<12} | {\"P2 Rec (11)\":<12}')
print('-' * 85)
print(f'{\"Condition A (Reference)\":<35} | {\"43.5%*\":<8} | {conds[\"condition_a_reference\"][\"tokens_mean\"]:>9.1f} | {\"47/47 (100%)\":<12} | {\"0/11 (0.0%)\":<12}')
print(f'{\"Condition B Baseline (theta=2.0)\":<35} | {conds[\"condition_b_baseline_theta2\"][\"answer_recall\"]*100:>6.1f}%  | {conds[\"condition_b_baseline_theta2\"][\"tokens_mean\"]:>9.1f} | {int(conds[\"condition_b_baseline_theta2\"][\"p1_recall_rate\"]*47):>2}/47 ({conds[\"condition_b_baseline_theta2\"][\"p1_recall_rate\"]*100:>4.1f}%) | {int(conds[\"condition_b_baseline_theta2\"][\"p2_recall_rate\"]*11):>2}/11 ({conds[\"condition_b_baseline_theta2\"][\"p2_recall_rate\"]*100:>5.1f}%)')
print(f'{\"Probe D.1 Best (theta=0.0, K=15)\":<35} | {conds[\"condition_d1_best_theta0_rows15\"][\"answer_recall\"]*100:>6.1f}%  | {conds[\"condition_d1_best_theta0_rows15\"][\"tokens_mean\"]:>9.1f} | {int(conds[\"condition_d1_best_theta0_rows15\"][\"p1_recall_rate\"]*47):>2}/47 ({conds[\"condition_d1_best_theta0_rows15\"][\"p1_recall_rate\"]*100:>4.1f}%) | {int(conds[\"condition_d1_best_theta0_rows15\"][\"p2_recall_rate\"]*11):>2}/11 ({conds[\"condition_d1_best_theta0_rows15\"][\"p2_recall_rate\"]*100:>5.1f}%)')
for k, label in [
    ('condition_d2_primary_theta2', 'Condition D2 Primary (theta=2.0)'),
    ('condition_d2_with_lists_theta2', 'Condition D2 + Lists (theta=2.0)'),
    ('condition_d2_relaxed_theta0', 'Condition D2 Relaxed (theta=0.0)'),
    ('condition_d2_relaxed_with_lists_theta0', 'Condition D2 Relaxed + Lists'):
]:
    c = conds[k]
    p1 = c['p1_regressions_recall']
    p2 = c['p2_recoveries_recall']
    print(f'{label:<35} | {c[\"answer_recall\"]*100:>6.1f}%  | {c[\"tokens_mean\"]:>9.1f} | {p1[\"recalled\"]:>2}/47 ({p1[\"rate\"]*100:>4.1f}%) | {p2[\"recalled\"]:>2}/11 ({p2[\"rate\"]*100:>5.1f}%)')
"
```

### Step 4: Verify the 27 Recovered P1 Regressions under Condition D2 Primary
Print representative regressions recovered under Condition D2 Primary ($\theta=2.0$):

```bash
python3 -c "
import json
with open('results/diagnostic_structural_decompilation_v3/stage_d2_case_audit.jsonl') as f:
    cases = [json.loads(line) for line in f]

p1_recovered = [c for c in cases if c['priority_cohort'] == 'P1_A_correct_B_incorrect' and c['condition_d2_primary']['answer_in_packed_context']]
print(f'Total P1 Regressions Recovered in D2 Primary: {len(p1_recovered)} / 47')
for c in p1_recovered[:5]:
    print(f\"  [{c['case_id'][:8]}] Q: {c['question'][:40]} | Gold: {c['gold_answer']} | Tok: {c['condition_d2_primary']['context_tokens']}\")
"
```

### Step 5: Verify the 3 Isolated List Regressions
Confirm that the 3 narrative cast / county list failures from D.1 are 100% recovered when raw list items are retained:

```bash
python3 -c "
import json
with open('results/diagnostic_structural_decompilation_v3/stage_d2_case_audit.jsonl') as f:
    cases = [json.loads(line) for line in f]

target_list_cids = {'363edbaa51694fedbd2a264c881f23a1', '3d3088e34ece49d8b9850f44ff05c029', 'c530f07f4ff040f5925b9a3599d9fb19'}
for c in cases:
    if c['case_id'] in target_list_cids:
        in_prim = c['condition_d2_primary']['answer_in_packed_context']
        in_lists = c['condition_d2_with_lists']['answer_in_packed_context']
        print(f\"Case {c['case_id'][:8]}: Q: {c['question'][:40]} | Table-Only: {in_prim} | With-Lists: {in_lists}\")
"
```

Expected output:
```
Case 363edbaa: Q: what part of maryland is close to washin | Table-Only: False | With-Lists: True
Case 3d3088e3: Q: who plays big momma in big mommas house | Table-Only: False | With-Lists: True
Case c530f07f: Q: who plays the queen in victoria and abdu | Table-Only: False | With-Lists: True
```

### Step 6: Verify Non-Destructive Invariants
Confirm that zero production code under `backend/src/precis/` was modified:

```bash
git status --short
```
