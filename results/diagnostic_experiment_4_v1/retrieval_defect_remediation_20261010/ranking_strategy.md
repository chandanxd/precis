# Similarity-Dominant Structural Ranking Strategy

**Experiment 4.5.4 Remediation Design**  
**Date**: 2026-10-10  
**Target**: `backend/src/precis/pipeline/structural.py::assemble_structural_query_context()`

---

## 1. Background & Defect Mechanisms

In Experiment 4.5.2, multi-document structural retrieval was governed by a hard document preference rule:
```python
fact_docs = {f.source_doc for f in pack_res.packed_facts if f.source_doc}
if fact_docs:
    top_doc = pack_res.packed_facts[0].source_doc if pack_res.packed_facts else None
    top_items = [it for it in relevant_struct if it[0].source_doc == top_doc]
    if top_items:
        selected_struct = top_items[:3]
    else:
        matched_items = [it for it in relevant_struct if it[0].source_doc in fact_docs]
        other_items = [it for it in relevant_struct if it[0].source_doc not in fact_docs and it[1] >= 0.40]
        selected_struct = (matched_items if matched_items else other_items)[:3]
else:
    selected_struct = relevant_struct[:3]
```

### Root Causes
1. **DEFECT-01 (Hard `top_doc` Bias)**: If prose from Document A produced the top SVOA fact, `top_items` selected structural records strictly from Document A if any item met the base threshold ($sim \ge 0.25$). If Document B contained the true answer in a table with high cosine similarity ($sim = 0.58$), Document B was completely discarded because Document A monopolized the selection.
2. **DEFECT-03 (Candidate Starvation)**: In the fallback branch, `(matched_items if matched_items else other_items)` selected `matched_items` whenever nonempty, entirely starving `other_items` even if `other_items` contained a candidate with $sim = 0.85$ and `matched_items` contained a candidate with $sim = 0.26$.

---

## 2. Corrected Ranking Policy Formulation

The replacement ranking policy is **similarity-dominant, cross-group, and deterministically tie-broken**.

### A. Candidate Relevance & Eligibility
Given raw structural candidates from ChromaDB cosine search (`struct_candidates`):
1. **Base Relevance Filter**:
   $$\text{relevant}(s, q) \iff \text{sim}(s, q) \ge 0.25 \lor (\text{has\_keyword\_match}(s, q) \land \text{sim}(s, q) \ge 0.15)$$
2. **Cross-Group Eligibility**:
   - If `fact_docs` is empty (e.g. pure-structural corpus or 0 SVOA facts retrieved): all candidates in `relevant_struct` are eligible.
   - If `fact_docs` is nonempty:
     - Candidates from documents corroborated by retrieved SVOA facts ($s.\text{source\_doc} \in \text{fact\_docs}$) are eligible.
     - Candidates from uncorroborated documents ($s.\text{source\_doc} \notin \text{fact\_docs}$) are eligible if $\text{sim}(s, q) \ge 0.40$. This prevents low-similarity cross-document noise while enabling clear structural matches to participate.

### B. Similarity-Dominant Blended Score
For each eligible candidate $s = (\text{item}, \text{sim})$:
$$\text{affinity\_mult}(s) = 1.0 + 0.15 \times \mathbb{I}_{s.\text{source\_doc} \in \text{fact\_docs}} + 0.10 \times \mathbb{I}_{s.\text{source\_doc} = \text{top\_doc}}$$
$$\text{blended\_score}(s) = \text{sim}(s, q) \times \text{affinity\_mult}(s)$$

- Maximum affinity boost is $+25\%$ (for candidates belonging to the top SVOA document).
- Secondary affinity boost is $+15\%$ (for candidates belonging to other SVOA-retrieved documents).
- Uncorroborated documents receive a multiplier of $1.00$.

### C. Deterministic Tie-Breaking
Candidates are sorted using the 3-tuple sort key:
$$\text{key}(s) = (-\text{round}(\text{blended\_score}(s), 6), -\text{round}(\text{sim}(s), 6), s.\text{item}.\text{id})$$

1. **Primary**: Highest blended score first.
2. **Secondary**: Highest raw cosine similarity first.
3. **Tertiary**: Content-addressed SHA-256 chunk ID (`item.id`) in alphanumeric ascending order.

### D. Budget & Chunk Limit
$$\text{selected\_struct} = \text{ranked\_candidates}[:3]$$
Preserves the chunk limit of at most 3 structural records before packing into the hardware token ceiling.

---

## 3. Mathematical Validation

| Scenario | Candidate A (from `top_doc`) | Candidate B (from other doc) | Score A | Score B | Winner |
|---|---|---|---|---|---|
| **DEFECT-01 Case** | $sim = 0.3254$ (Frank Miller) | $sim = 0.5800$ (Elena Rostova) | $0.3254 \times 1.25 = 0.4068$ | $0.5800 \times 1.00 = 0.5800$ | **Candidate B (Elena Rostova)** |
| **DEFECT-03 Case** | $sim = 0.2800$ (Speaker Brown) | $sim = 0.6500$ (0.42 ms latency) | $0.2800 \times 1.15 = 0.3220$ | $0.6500 \times 1.00 = 0.6500$ | **Candidate B (Latency metric)** |
| **Close Tie Case** | $sim = 0.5000$ (Corroborated) | $sim = 0.5200$ (Uncorroborated) | $0.5000 \times 1.25 = 0.6250$ | $0.5200 \times 1.00 = 0.5200$ | **Candidate A (Corroborated)** |
| **Pure Structural** | $sim = 0.7000$ (Doc 1, 0 facts) | $sim = 0.6000$ (Doc 2, 0 facts) | $0.7000 \times 1.00 = 0.7000$ | $0.6000 \times 1.00 = 0.6000$ | **Candidate A** |
