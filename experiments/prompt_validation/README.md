# Précis: Confirmatory Answer-Formatting Experiment

## 1. Overview & Research Objective

In Stage C of the model-selection investigation (`experiments/model_comparison/`), substituting an exploratory concise-answer prompt for the standard document QA prompt increased Exact Match (EM) for `qwen3.5:4b` under Précis v3 from **7/100 to 33/100** ($p < 10^{-7}$), while answer containment declined from **61% to 48%**.

This experiment provides an **independent, confirmatory evaluation** on a freshly sampled, deduplicated cohort of 100 question-document pairs drawn from the Natural Questions development data (`backend/data/nq_subset/nq_dev.jsonl`).

### Preregistered Hypotheses:
1. **Primary Hypothesis ($H_1$):** The concise prompt increases Précis Exact Match on the new cohort for `qwen3.5:4b` compared with the standard prompt ($p < 0.05$ under one-sided paired McNemar test).
   - **Containment Degradation Guardrail:** Supported **if and only if** containment drop does not exceed 25 percentage points ($\Delta_{\text{cont}} \ge -0.2500$) and absolute containment remains $\ge 0.4000$.
2. **Secondary Prompt-Effect Family ($H_2$):**
   - $H_{2a}$: Concise prompt improves Naive RAG EM for `qwen3.5:4b`.
   - $H_{2b}$: Concise prompt improves Précis EM for `qwen2.5-coder:7b`.
   - $H_{2c}$: Concise prompt improves Naive RAG EM for `qwen2.5-coder:7b`.
   - *Multiplicity Policy:* Holm-Bonferroni step-down correction at FWER $\alpha = 0.05$.
3. **Retrieval $\times$ Prompt Interaction ($H_3$):**
   - Evaluated separately per model via 10,000 paired bootstrap resamples (seed 42).
   - $\Delta_{\text{prompt-diff}} = (\text{EM}_{\text{concise, Précis}} - \text{EM}_{\text{standard, Précis}}) - (\text{EM}_{\text{concise, Naive}} - \text{EM}_{\text{standard, Naive}})$.
4. **Cross-Model Testing Family ($H_4$):**
   - Four pairwise comparisons of `qwen3.5:4b` vs `qwen2.5-coder:7b` across retrieval $\times$ prompt combinations.
   - *Multiplicity Policy:* Two-sided McNemar exact tests with Holm-Bonferroni step-down correction ($\alpha = 0.05$).

---

## 2. Factorial Experimental Matrix ($2 \times 2 \times 2 = 8$ Conditions)

For each question in the 100-sample cohort:
- **Models ($M=2$):** `qwen2.5-coder:7b` (Reference), `qwen3.5:4b` (Candidate).
- **Retrieval ($R=2$):** Naive RAG (512-word chunk, 128 overlap, top-5), Précis v3 (OpenIE SVOA, SDH deduplication, hierarchical packing to 2048 tokens).
- **Prompts ($P=2$):** Standard Prompt vs Concise Prompt.
- Total evaluations: $100 \times 8 = 800$.

### Context Parity & Integrity
Both prompt variants and both models receive bit-for-bit identical evidence text from `cached_contexts.jsonl` with verified SHA-256 checksums.

---

## 3. Exact Reproducibility Metadata

### Prompt Hashes
- **Standard Prompt SHA-256:** `dc584bb87b846fc60945b3c351ee8c405a980a1147aa63114eec67b3e2b3f4a5`
- **Concise Prompt SHA-256:** `3dc0137b82902e56840b6a27df6afeffe4b72cec027a06e08f69c24b734fc426`

### Model Digests
- **`qwen2.5-coder:7b`:** `dae161e27b0e90dd1856c8bb3209201fd6736d8eb66298e75ed87571486f4364`
- **`qwen3.5:4b`:** `d8b0f5e9760cd1682034f292d7ef72ec46f432149be0df7574bf2d6e92e38c04`

### Decoding Parameters
- API: `/api/chat` with `"think": false`
- `temperature = 0.0`
- `top_p = 0.9`
- `seed = 42`
- `num_predict = 512`

---

## 4. Cohort Audit Summary
- Entire NQ development dataset: **12,836 raw records**.
- Total excluded: **8,932** (canonical v3 IDs/questions/docs, Stage A/B/C IDs/questions/docs, within-pool duplicates).
- Remaining strictly eligible pool: **3,904 records**.
- Reconciled audit report: `experiments/prompt_validation/audit_report.json`.
- Selected cohort: First 100 records sorted by `SHA256(normalized_question)`.

---

## 5. Execution & Reproduction
```bash
./experiments/prompt_validation/reproduce.sh
```
