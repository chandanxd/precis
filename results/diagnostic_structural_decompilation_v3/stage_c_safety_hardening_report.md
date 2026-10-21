# Précis Experiment 3: Stage C Safety-Hardening Report

## 1. Summary of Changes
- **Target File**: `scripts/eval_structural_decompilation_v3.py`
- **Initial SHA-256**: `9b1edfff229307c32b1512bcfb3002f96dcd9af4474e7ed72d66ecafacb9384e`
- **Final SHA-256**: `f1b6de12f128a29483b65082f51117e6afcfe06f33064eacaf789ce13dc0592a`

### Hardening Measures Implemented:
1. **Direct Cohort Exclusion**:
   - `audit_and_generate_manifest()` explicitly scans `results/diagnostic_structural_decompilation_v3/sample_manifest_stage_b.jsonl`.
   - Manifest header record (`type == "manifest_header"`) is explicitly ignored; only `sample_record` sample IDs are added to exclusions.
   - Enforced uniqueness assertions: zero duplicate IDs permitted in confirmatory sample; zero intersection permitted with historical exclusions.
2. **Configuration-Safe Resume & Overwrite Protection**:
   - Implemented `compute_stage_c_config_fingerprint()` tracking model, decoding parameters, context ceiling, prompt template, condition implementation, scoring functions, and manifest hash.
   - Evaluates non-empty Stage C output paths (`sample_manifest.jsonl`, `eval_records_stage_c.jsonl`). Any attempt to write or append without `--resume` raises `FileExistsError`.
   - Under `--resume`, validates `run_header` config fingerprint. Rejects any mismatch with `ValueError` to prevent mixing configurations.
   - Per-case records record `config_fingerprint` in each JSON line.
3. **Prose-Only Upstream Invariance Diagnostics**:
   - For `stratum == "prose_only"`, evaluates and logs diagnostic fields per case:
     - `prose_byte_identical`: clean prose equals raw HTML.
     - `zero_structured_blocks`: zero structured blocks extracted.
     - `facts_identical`: extracted fact propositions match Condition A.
     - `context_tokens_identical`: context tokens used match Condition A.
     - `upstream_invariant`: boolean conjunction of all four invariant conditions.
   - Summarized in `aggregate_summary.json` under `upstream_invariance_all_passed` and counts.
   - Does not modify model inputs, prompts, conditions, or primary scoring outcomes.

---

## 2. Test Verification & Evidence

### Targeted Deterministic Test Suite: `scripts/test_stage_c_safety_hardening.py`
Command: `backend/venv/bin/python scripts/test_stage_c_safety_hardening.py`
Output: `Ran 6 tests in 0.029s - OK`

| Test Name | Verified Behavior | Result |
| :--- | :--- | :--- |
| `test_01_stage_b_manifest_direct_exclusion` | Scans `sample_manifest_stage_b.jsonl`, skips header, extracts all 59 sample IDs into exclusions. | **PASS** |
| `test_02_manifest_overlap_and_duplicate_assertion` | Verifies exclusion filter strips known IDs; validates uniqueness assertions. | **PASS** |
| `test_03_config_fingerprint_determinism_and_sensitivity` | Deterministic fingerprint; changes to model, temperature, or manifest hash alter fingerprint. | **PASS** |
| `test_04_manifest_overwrite_protection` | Non-empty manifest triggers `FileExistsError` when run without `--resume`. | **PASS** |
| `test_05_record_overwrite_and_resume_validation` | Non-empty records trigger `FileExistsError` without `--resume`; fingerprint mismatch triggers `ValueError`; matching header resumes cleanly. | **PASS** |
| `test_06_prose_only_upstream_invariance_diagnostics` | Proves byte identity and zero structured blocks on prose fixture; detects blocks on table fixture. | **PASS** |

### Stage A Deterministic Suite Verification
Command: `backend/venv/bin/python scripts/eval_structural_decompilation_v3.py --stage-a-only`
Output: `Stage A passed cleanly (15/15 tests passed). Halting.`
Hash Check: `stage_a_results.json` and `stage_a_results_corrected.json` remain byte-identical (`46ab963e6e327bef59b0bdb9c1714b266b942efa3977c4fda6ec35920e253a32`).

---

## 3. Operational Integrity
- **Zero LLM Inference Executed**: All tests were offline, deterministic, and isolated.
- **Zero Artifact Overwrites**: `eval_records_stage_b.jsonl`, `sample_manifest_stage_b.jsonl`, `stage_b_replay.json`, `stage_b_report.md` remain untouched and preserved.
- **Working Tree Integrity**: No changes made under `backend/src/precis/`. Pre-existing working tree state preserved.

---

## 4. Execution Command for Future Stage C Run
When explicitly authorized to run Stage C:
```bash
backend/venv/bin/python scripts/eval_structural_decompilation_v3.py --stage-c-only
```
If safely resuming an interrupted confirmatory run with identical configuration:
```bash
backend/venv/bin/python scripts/eval_structural_decompilation_v3.py --stage-c-only --resume
```
