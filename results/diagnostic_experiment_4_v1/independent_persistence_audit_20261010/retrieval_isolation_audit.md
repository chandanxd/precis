# Query-Time Retrieval and Document Isolation Audit

**Experiment 4.5.3 Independent Audit**  
**Date**: 2026-10-10  
**Verdict**: LIMITATIONS IDENTIFIED (Critical SVOA Dependency Defect)

---

## 1. Architectural Trace of Context Assembly

Context assembly in `backend/src/precis/pipeline/structural.py` (`assemble_structural_query_context()`) executes as follows:

1. **Stage 4 Fact Retrieval**:
   - Calls `pack_context()` to retrieve up to `top_k` SVOA facts from `{collection_name}` based on query similarity.
   - Computes `pack_score = SDH * similarity` and greedily packs facts.
2. **Structural Candidate Search**:
   - Calls `store.query_similar_structural(query, n_results=10)`.
   - Filters candidate chunks by similarity threshold (`sim >= 0.25` or keyword match with `sim >= 0.15`).
3. **Document Affinity Filtering**:
   - Extracts `fact_docs = {f.source_doc for f in pack_res.packed_facts if f.source_doc}`.
   - Extracts `top_doc = pack_res.packed_facts[0].source_doc if pack_res.packed_facts else None`.
   - Evaluates:
     ```python
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
4. **Context Construction & Dedup**:
   - Deduplicates facts whose subject and object are captured in selected structural chunks.
   - Enforces token ceiling with header reservation.

---

## 2. In-Depth Scrutiny: The `top_doc` SVOA Selection Flaw (DEFECT-01)

The audit specifically scrutinized the `top_doc` selection logic as requested:
> *"Specifically scrutinize the implementation's `top_doc` selection logic. Determine whether it creates a hidden dependency on successful SVOA retrieval that undermines structural retrieval in precisely the cases this feature is meant to fix."*

### Empirical Proof of Vulnerability
The audit test `TestAuditQueryRetrievalAndIsolationScrutiny.test_top_doc_defect_vulnerability_demonstration` deterministically reproduced this defect:

1. **Corpus Setup**:
   - `Document A` (`wrong_summit.html`): Contains prose about a renewable energy summit that has high lexical overlap with the query. Also contains a table listing summit nominees (e.g. `Frank Miller`).
   - `Document B` (`correct_awards.html`): Contains factual awards results with minimal SVOA prose, but contains the **actual final winner** in a table (`Dr. Elena Rostova`).
2. **Query**:
   - `"Who won the renewable energy innovation award at the energy summit?"`
3. **Observed System Execution**:
   - SVOA fact search returned facts from `Document A` (`The global energy leadership summit discussed renewable energy innovations`).
   - Consequently, `top_doc` was assigned to `Document A`.
   - `relevant_struct` contained both `Frank Miller` (sim ~0.50) from `Document A` and `Dr. Elena Rostova` (sim ~0.75) from `Document B`.
   - Because `top_doc == "wrong_summit.html"`, `top_items` was populated with `Frank Miller`.
   - **The system executed `selected_struct = top_items[:3]` and COMPLETELY DISCARDED Dr. Elena Rostova!**
4. **Output Verification**:
   - `Is Elena Rostova in context? False`
   - `Is Frank Miller in context? True`

### Root Cause Analysis
The structural persistence feature was designed precisely to resolve cases where **SVOA fact extraction is insufficient or misleading** because information resides in structured tables and lists.

By making structural evidence selection strictly subordinate to `top_doc` (the top SVOA fact document), the implementation created a **circular failure mode**:
- If SVOA extraction misidentifies the primary document, structural retrieval is forced into the wrong document as well, dropping genuine structural answers from the correct document even when they possess higher cosine similarity.

---

## 3. Secondary Retrieval Defects (DEFECT-02 & DEFECT-03)

### Defect 2: Rejection of Pure-Structural Knowledge Bases
- When an ingested document contains only tables/lists (zero prose), spaCy SVOA extraction extracts 0 facts.
- `store.count() == 0`.
- In `backend/main.py` (lines 272 and 550):
  `if active_store.count() == 0: raise HTTPException(400, "No documents ingested. Upload a document first.")`
- The system returns HTTP 400 Bad Request and refuses to execute the query, completely ignoring the fact that `store.count_structural_evidence() > 0`.

### Defect 3: Starvation of Non-`fact_docs` Candidates
- In line 1327: `selected_struct = (matched_items if matched_items else other_items)[:3]`.
- If `top_items` is empty, but `matched_items` contains any item from secondary documents in `fact_docs`, `other_items` is never consulted.
- Structural evidence from a document with zero retrieved SVOA facts is starved unless all documents in `fact_docs` lack structural chunks entirely.

---

## 4. Proposed Architectural Fixes (For Explicit User Approval)

To resolve these defects safely without breaking single-document isolation:

1. **Similarity-Dominant Blended Ranking**:
   Instead of hard `top_doc` filtering, rank structural candidates by a blended score:
   $$\text{score}(s) = \text{sim}(s, q) \times (1.0 + 0.25 \times \mathbb{I}_{s \in \text{fact\_docs}} + 0.15 \times \mathbb{I}_{s = \text{top\_doc}})$$
   This gives a moderate boost to documents with matching SVOA facts while allowing a high-similarity structural match (e.g. 0.75) from another document to decisively outrank a weak structural chunk (e.g. 0.30) from the SVOA top document.
2. **Unified Document Store Guard**:
   In `backend/main.py`:
   Replace `if active_store.count() == 0:` with:
   `if active_store.count() == 0 and not active_store.has_structural_evidence():`
   This allows pure-table or pure-list documents to be queried normally.
