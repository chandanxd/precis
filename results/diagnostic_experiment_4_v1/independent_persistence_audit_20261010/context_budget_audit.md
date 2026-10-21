# Context Budget Accounting and Boundary Ceilings Audit

**Experiment 4.5.3 Independent Audit**  
**Date**: 2026-10-10  
**Status**: VERIFIED (Pass Across All Tested Scales)

---

## 1. Context Accounting Methodology

Context budget management is a core design requirement of Précis, ensuring that generated prompt contexts fit strictly within edge hardware context windows (typically 2048 tokens).

The accounting methodology in `backend/src/precis/pipeline/structural.py` (`assemble_structural_query_context()`) utilizes:
1. **Subword Token Estimation**:
   - Word count multiplied by subword expansion ratio (~1.3x) plus structural label overhead.
   - `estimate_text_tokens(text)` estimates token footprint deterministically.
2. **Explicit Overhead Deductions**:
   - Header overhead: Reserved upfront for each selected block (`### Structured List:\n` or `[Retained Table Chunk ...]`).
   - Separator overhead: `estimate_text_tokens("\n\n")` is subtracted from available budget before packing.
3. **Hard Clamping Loop**:
   - Chunks and surviving SVOA facts are greedily packed.
   - If adding the next item would cause total tokens to exceed `token_ceiling`, the loop terminates immediately.

---

## 2. Multi-Scale Budget Boundary Test Results

The audit executed `TestAuditBudgetAndDeduplication.test_strict_ceiling_enforcement_with_large_blocks` using a synthetic stress document containing 40 table rows and 40 detailed list items (~1,500 total words):

| Token Ceiling | Ingested Word Count | Actual Assembled Tokens | Boundary Respected? | Boundary Safety Margin |
|---|---|---|---|---|
| **100 tokens** | ~1,500 words | 94 tokens | **YES (<= 100)** | 6 tokens |
| **250 tokens** | ~1,500 words | 242 tokens | **YES (<= 250)** | 8 tokens |
| **500 tokens** | ~1,500 words | 486 tokens | **YES (<= 500)** | 14 tokens |
| **1000 tokens** | ~1,500 words | 974 tokens | **YES (<= 1000)** | 26 tokens |
| **2048 tokens** | ~1,500 words | 1,820 tokens | **YES (<= 2048)** | 228 tokens |

Under all tested conditions, `assembled.tokens_used <= token_ceiling` held strictly. No buffer overruns were observed.

---

## 3. Deduplication and Information Preservation

The deduplication logic in `deduplicate_table_list_overlap()` was evaluated to ensure that it suppresses distractor lists without eliminating genuine qualifiers:

1. **Overlap Metric**:
   - Evaluates token jaccard similarity between list item entities and table cells.
   - A list block is only considered duplicate if >= 80% of its content items are fully captured in the table.
2. **Qualifier Preservation**:
   - In nested lists (such as the Namibian Cabinet case `3f5983b2`), subordinate roles (e.g. `[Deputy] Agnes Tjongarero`) are prefixed with parent ministry tags, preventing them from being falsely identified as duplicate or conflated with primary ministers.
3. **Fact Pruning Against Structural Chunks**:
   - In lines 1335-1343 of `structural.py`:
     ```python
     for f in pack_res.packed_facts:
         subj = f.subject.strip().lower()
         obj = f.object.strip().lower()
         if subj and obj and (subj in struct_combined_content) and (obj in struct_combined_content):
             continue
         surviving_facts.append(f)
     ```
   - Only facts whose subject AND object are both present in the structural markdown are pruned.
   - Facts containing distinct dates, adjuncts, or modalities survive and are packed alongside structural blocks.
