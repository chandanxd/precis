# Independent Ranking Policy Audit

**Experiment 4.5.5 Independent Audit**  
**Date**: 2026-10-10  
**Target Under Audit**: `backend/src/precis/pipeline/structural.py::assemble_structural_query_context()` (Experiment 4.5.4 Remediation)

---

## 1. Exact Code-Level Eligibility Rules and Filter Ordering

Direct code inspection of lines 1299–1348 of `backend/src/precis/pipeline/structural.py` reveals the exact sequential pipeline:

```
[ChromaDB Structural Vector Search] (n_results=10)
                 │
                 ▼
      [Filter 1: General Relevance]
  sim >= 0.25 OR (has_kw_match AND sim >= 0.15)
                 │
                 ├── False ──> Dropped
                 ▼ True
            relevant_struct
                 │
                 ▼
  [Filter 2: Document Affinity Eligibility]
                 │
  ┌──────────────┴────────────────────────┐
  │ fact_docs is empty?                    │
  ├─ YES: All relevant_struct pass         │
  └─ NO:                                   │
       ├── item.source_doc in fact_docs?   │
       │     └─ YES: Pass                  │
       └── item.source_doc not in fact_docs?
             └─ sim >= 0.40?               │
                  ├── YES: Pass            │
                  └── NO:  Dropped         │
                 │
                 ▼
         eligible_candidates
                 │
                 ▼
     [Score Calculation & Ranking]
  affinity_mult = 1.0
  + 0.15 (if item.source_doc in fact_docs)
  + 0.10 (if item.source_doc == top_doc)
  score = sim * affinity_mult
  sort_key = (-round(score, 6), -round(sim, 6), item.id)
                 │
                 ▼
         selected_struct[:3]
```

### Exact Filter Order Details
1. **Filter 1 (General Query Relevance)**:
   - Applied to all top-10 vector candidates from `{collection_name}_structural`.
   - Criteria: $\text{sim} \ge 0.25 \lor (\text{has\_kw\_match} \land \text{sim} \ge 0.15)$.
   - Drops any candidate with $\text{sim} < 0.15$, or candidates with $0.15 \le \text{sim} < 0.25$ lacking 3+ character query words in `searchable_text`.
2. **Filter 2 (Cross-Document Eligibility)**:
   - Evaluated over `relevant_struct`.
   - Case A: `fact_docs` is empty $\rightarrow$ All candidates in `relevant_struct` pass unconditionally.
   - Case B: `fact_docs` is nonempty:
     - If candidate belongs to a document in `fact_docs`: passes without additional threshold (effective threshold: $\text{sim} \ge 0.25$, or $\text{sim} \ge 0.15$ with keyword).
     - If candidate belongs to an uncorroborated document ($\notin \text{fact\_docs}$): must satisfy $\text{sim} \ge 0.40$.

---

## 2. Comparison Against Documented Rules & Discrepancy Resolution

### Documented Specifications Comparison

| Document | Stated Eligibility Policy | Stated Ranking Formulation | Filter Order Explained? | Code Parity Assessment |
|---|---|---|---|---|
| **`ranking_strategy.md`** | 1. Base Relevance: $\text{sim} \ge 0.25 \lor (\text{kw} \land \text{sim} \ge 0.15)$.<br>2. Cross-Group: Corroborated pass; Uncorroborated $\text{sim} \ge 0.40$. | $\text{score} = \text{sim} \times (1.0 + 0.15 \times \mathbb{I}_{\text{fact}} + 0.10 \times \mathbb{I}_{\text{top}})$ | Yes, 2-phase pipeline explicitly partitioned. | **Exact match** with code. |
| **`implementation_report.md`** | "If `fact_docs` is empty: all items in `relevant_struct` are eligible. If nonempty: `fact_docs` items ($\ge 0.25$ / $\ge 0.15$ kw); non-`fact_docs` items ($\ge 0.40$)." | $\text{score} = \text{sim} \times (1.0 + 0.15 \times \mathbb{I}_{\text{fact}} + 0.10 \times \mathbb{I}_{\text{top}})$ | Condenses Filter 1 and 2 into effective criteria without detailing the 2-phase pipeline. | **Semantically equivalent**, minor structural omission in text. |
| **User Request (4.5.4)** | "Retain original structural similarity score... Candidates from documents with no retrieved SVOA facts must remain eligible when their structural similarity qualifies." | Specified soft document affinity without hard threshold mandates. | N/A | **Compliant**. |

### Audit Finding [DOC-01: Low Severity]: Descriptive Compression in `implementation_report.md`
`implementation_report.md` describes the eligibility rule as a single combined condition rather than explicitly illustrating that Filter 2 operates downstream of Filter 1. While mathematically and functionally identical (since $\text{sim} \ge 0.40$ strictly satisfies $\text{sim} \ge 0.25$), future maintainers should reference `ranking_strategy.md` for the explicit two-phase pipeline architecture.

---

## 3. Numerical Analysis of Affinity Multipliers & Ranking Reversals

Formula:
$$\text{score}(s) = \text{sim}(s, q) \times (1.0 + 0.15 \times \mathbb{I}_{s.\text{source\_doc} \in \text{fact\_docs}} + 0.10 \times \mathbb{I}_{s.\text{source\_doc} = \text{top\_doc}})$$

Multipliers by Document Affinity Tier:
1. **Tier 1 (Top SVOA Document)**: $M_{\text{top}} = 1.25$ ($+25\%$ affinity boost).
2. **Tier 2 (Secondary SVOA Document in `fact_docs`)**: $M_{\text{fact}} = 1.15$ ($+15\%$ affinity boost).
3. **Tier 3 (Uncorroborated Document $\notin \text{fact\_docs}$)**: $M_{\text{other}} = 1.00$ ($0\%$ affinity boost).

### Reversal Boundary Conditions

#### Condition 1: Tier 1 (Top SVOA) vs. Tier 3 (Uncorroborated)
A candidate from Tier 1 with lower similarity outranks a candidate from Tier 3 if and only if:
$$\text{sim}_{\text{top}} \times 1.25 > \text{sim}_{\text{other}} \times 1.00 \iff \frac{\text{sim}_{\text{top}}}{\text{sim}_{\text{other}}} > 0.80$$

- **Concrete Reversal Example**:
  - Candidate A (Top SVOA doc): $\text{sim}_A = 0.45 \implies \text{score}_A = 0.45 \times 1.25 = 0.5625$.
  - Candidate B (Uncorroborated doc): $\text{sim}_B = 0.55 \implies \text{score}_B = 0.55 \times 1.00 = 0.5500$.
  - **Outcome**: Candidate A outranks Candidate B despite being $0.10$ lower in raw cosine similarity ($0.45 < 0.55$).
- **Non-Reversal Example (Defect 1 Fixture)**:
  - Candidate A (`energy_summit.html`, Top SVOA): $\text{sim}_A = 0.3254 \implies \text{score}_A = 0.3254 \times 1.25 = 0.4068$.
  - Candidate B (`awards_data.html`, Uncorroborated): $\text{sim}_B = 0.5800 \implies \text{score}_B = 0.5800 \times 1.00 = 0.5800$.
  - Ratio: $0.3254 / 0.5800 \approx 0.561 < 0.80$.
  - **Outcome**: Candidate B decisively outranks Candidate A.

#### Condition 2: Tier 2 (Secondary SVOA) vs. Tier 3 (Uncorroborated)
Reversal occurs if:
$$\frac{\text{sim}_{\text{fact}}}{\text{sim}_{\text{other}}} > \frac{1.00}{1.15} \approx 0.8696$$
- Reversal occurs if the Tier 2 candidate is within $13\%$ of Tier 3 similarity.

#### Condition 3: Tier 1 (Top SVOA) vs. Tier 2 (Secondary SVOA)
Reversal occurs if:
$$\frac{\text{sim}_{\text{top}}}{\text{sim}_{\text{fact}}} > \frac{1.15}{1.25} = 0.9200$$
- The Top SVOA document maintains only an $8\%$ advantage over other SVOA-supported documents.

### Policy Assessment
The maximum inversion window is bounded at $20\%$ relative similarity deficit. If an uncorroborated document matches the query with substantially higher similarity (e.g., $\Delta \text{sim} \ge 0.15$ for moderate scores), it cannot be defeated by document affinity. This adheres strictly to the requirement that affinity provide a *modest* preference without monopolizing context.

---

## 4. Determinism, Provenance, Budget, and Deduplication Findings

### A. Determinism
- Tie-breaking key: `(-round(blended_score, 6), -round(sim, 6), item.id)`.
- Content-addressed SHA-256 chunk IDs (`item.id`) guarantee a strict total ordering.
- Empirically verified in Test C: 3 consecutive runs produced byte-for-byte identical assembled contexts.

### B. Provenance
- `item.source_doc` is preserved intact on all `StructuralEvidence` records throughout ChromaDB retrieval, scoring, and context packing.

### C. Hardware Token Budget Ceiling
- Separation overhead (`\n\n`) is deducted prior to packing structural chunks.
- Structural chunks are greedily packed until the remaining budget cannot accommodate the next chunk.
- Verified across hardware token ceilings from 100 to 2048 tokens.

### D. Audit Finding [ARCH-01: Medium Severity]: Cross-Document Structural Chunk Redundancy
- **Observation**: Deduplication in `structural.py` removes SVOA facts whose subject and object are captured by selected structural tables/lists (`lines 1352–1360`). Intra-document table-list overlap is also deduplicated during ingestion (`deduplicate_table_list_overlap`).
- **Gap**: There is **no cross-document table-to-table deduplication**. If multiple ingested documents contain identical or near-identical tables (e.g. syndication, mirrored specs, shared financial disclosures), multiple copies of the same table can consume up to 3 of the limited top-3 structural slots.
- **Risk**: In large corpora with duplicate documents, duplicate tables could push distinct, diverse evidence out of the top-3 slots.
