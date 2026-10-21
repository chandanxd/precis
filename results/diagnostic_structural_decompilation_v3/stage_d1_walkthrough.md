# Diagnostic Probe D.1: Walkthrough & Verification Guide

This guide provides reproducible verification commands for reviewing the findings of **Diagnostic Probe D.1: Oracle Context Sufficiency and Retrieval Recall**.

---

## 1. Executive Summary & Decision Gate

- **Cohort**: 200 frozen table/list confirmatory cases from Précis Experiment 3.
- **Decision Gate Determination**: **`PARTIALLY SUPPORTED`**
- **Core Results**:
  - Relaxing table selection threshold ($\theta=2.0 \to 0.0$) and row budget ($K=5 \to 15$) substantially improves answer retrieval recall from **31.0% (62/200)** to **56.5% (113/200)**.
  - Recovers 15 of 47 Stage C regressions (jumping regression recall from 6.4% to 38.3%).
  - Average context length increases moderately from 155.4 to 266.3 tokens (still -56.9% below Condition A's 618.8 tokens; zero cases exceed the 2048 ceiling).
  - **However, 29 of the 47 regressions (61.7%) remain unrecovered**: 26 cases due to deep row truncation in large tables (lexical overlap fails to rank target rows into the top 15 budget), and 3 cases due to list extractor regex failure.
  - Threshold relaxation is necessary but insufficient on its own.

---

## 2. Artifact Inventory & Cryptographic Hashes

All artifacts were generated in `results/diagnostic_structural_decompilation_v3/`:

| Artifact Path | SHA-256 Checksum | Description |
| :--- | :--- | :--- |
| `stage_d1_evidence_audit.jsonl` | `916d9ae633fba042c464ad7739f619ce38be733ef6c79b828b88a74ab5c673b7` | Case-level evidence audit (200 records; 100% source support verified) |
| `stage_d1_retrieval_sweep.jsonl` | `9885b3a5b9fdf2466aba6609e9f940d4046a32fe091ddd05f42abf36f865b2b5` | Full 16-configuration sweep results (3,200 records) |
| `stage_d1_summary.json` | `c312cb9aaac80e6ea56f6d90410a9e521dfedc18015f64c51b532c0d63b0e73b` | Reconciled metrics, token percentiles, and cohort breakdowns |
| `stage_d1_report.md` | `63f926e61cf27166335bdec24eec5ab32ba3fc6da7cf26437cba5b5ee74da335` | Full forensic diagnostic report |
| `stage_d1_walkthrough.md` | *(This file)* | Reviewer verification guide and reproducible commands |

---

## 3. Verification Commands

### Step 1: Verify Input Hashes (Strict Isolation & Provenance)
Ensure all frozen inputs match preflight checksums:

```bash
sha256sum \
  results/diagnostic_structural_decompilation_v3/sample_manifest.jsonl \
  results/diagnostic_structural_decompilation_v3/eval_records_stage_c.jsonl \
  scripts/eval_structural_decompilation_v3.py \
  backend/data/nq_subset/nq_dev.jsonl \
  results/diagnostic_structural_decompilation_v3/stage_d_forensic_case_audit.jsonl \
  results/diagnostic_structural_decompilation_v3/stage_d_forensic_report.md
```

Expected output:
```
011553c0725621b7dda73aad12254d100e6fc15f49a5f80f4524156eb4e25db7  .../sample_manifest.jsonl
e10ea38f7cc7cfa9a98d494851de8c41c322b5f148dfff653077193917933687  .../eval_records_stage_c.jsonl
ad56761db55fc9693526fe5c51d0db58c482c288525838d0b93fd240c21ac0e4  scripts/eval_structural_decompilation_v3.py
14efc255a596433d6bf10dd853a1915474a5d3f6b47c593f77911ab4bb8eb491  backend/data/nq_subset/nq_dev.jsonl
8d3e21144f8cd6662a071de278745aac8542cf5f61f149a4796f8a3cfd9c7321  .../stage_d_forensic_case_audit.jsonl
870ae3d735bbffb43d04410f5296163d3f53e9432914025c188b64525babd11e  .../stage_d_forensic_report.md
```

### Step 2: Verify Baseline Replay Fidelity
Confirm that the baseline configuration ($\theta=2.0, K=5$) matched 200 of 200 cases:

```bash
python3 -c "
import json
with open('results/diagnostic_structural_decompilation_v3/stage_d1_summary.json') as f:
    d = json.load(f)
rf = d['replay_fidelity_validation']
print(f'Cases: {rf[\"cases_evaluated\"]}')
print(f'Token Matches: {rf[\"token_matches\"]} / 200')
print(f'Structured Fact Matches: {rf[\"struct_fact_matches\"]} / 200')
print(f'Discrepancies: {rf[\"discrepancies_count\"]}')
"
```

Expected output:
```
Cases: 200
Token Matches: 200 / 200
Structured Fact Matches: 200 / 200
Discrepancies: 0
```

### Step 3: Inspect the 16-Configuration Sweep Comparison
Print the summary table comparing baseline vs. relaxed configurations:

```bash
python3 -c "
import json
with open('results/diagnostic_structural_decompilation_v3/stage_d1_summary.json') as f:
    d = json.load(f)
print(f'{\"Config ID\":<22} | {\"Recall\":<7} | {\"Mean Tok\":<8} | {\"P95 Tok\":<7} | {\"P1 Rec (47)\":<11} | {\"P2 Rec (11)\":<11}')
print('-' * 78)
for cid, c in d['configurations'].items():
    p1 = c['cohort_breakdowns']['p1_regressions']
    p2 = c['cohort_breakdowns']['p2_recoveries']
    print(f'{cid:<22} | {c[\"answer_evidence_recall_all_cases\"]*100:>5.1f}%  | {c[\"tokens_mean\"]:>8.1f} | {c[\"tokens_p95\"]:>7} | {p1[\"evidence_in_context_count\"]:>2}/47 ({p1[\"recall\"]*100:>4.1f}%) | {p2[\"evidence_in_context_count\"]:>2}/11 ({p2[\"recall\"]*100:>5.1f}%)')
"
```

### Step 4: Inspect the Root Cause Breakdown of the 29 Unrecovered Regressions
Verify why 29 regressions remain unrecovered at $\theta=0.0, K=15$:

```bash
python3 -c "
import json

case_info = {}
with open('results/diagnostic_structural_decompilation_v3/stage_d_forensic_case_audit.jsonl') as f:
    for line in f:
        r = json.loads(line)
        case_info[r['case_id']] = r

sweep = {}
with open('results/diagnostic_structural_decompilation_v3/stage_d1_retrieval_sweep.jsonl') as f:
    for line in f:
        r = json.loads(line)
        sweep.setdefault(r['config_id'], {})[r['case_id']] = r

best_config = sweep['thresh_0.0_rows_15']
p1_unrec = [best_config[cid] for cid, cdata in case_info.items() if cdata['priority_group'] == 'P1_A_correct_B_incorrect' and not best_config[cid]['answer_in_packed_context']]

deep_row_truncation = [x for x in p1_unrec if x['answer_table_selected'] and not x['answer_row_selected']]
list_regex_omissions = [x for x in p1_unrec if not x['answer_table_selected']]

print(f'Total Unrecovered Regressions: {len(p1_unrec)}')
print(f'  - Deep Row Truncation (Table selected, row >15): {len(deep_row_truncation)}')
print(f'  - List Extractor Regex Omission (Cast/narrative lists): {len(list_regex_omissions)}')
"
```

Expected output:
```
Total Unrecovered Regressions: 29
  - Deep Row Truncation (Table selected, row >15): 26
  - List Extractor Regex Omission (Cast/narrative lists): 3
```

### Step 5: Verify Non-Destructive Invariants & Git Status
Confirm that zero production code or frozen experiment files were modified:

```bash
git status --short
```

Ensure no changes exist in `backend/src/precis/`.
