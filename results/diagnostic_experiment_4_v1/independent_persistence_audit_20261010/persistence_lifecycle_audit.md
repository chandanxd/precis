# Persistence and Lifecycle Audit

**Experiment 4.5.3 Independent Audit**  
**Date**: 2026-10-10  
**Status**: VERIFIED (Pass with Full Provenance Integrity)

---

## 1. Extraction Determinism and HTML Safety

Extraction of tables and lists was tested across well-formed and malformed inputs:

1. **Table Extraction**:
   - Decompiles HTML tables into GitHub Flavored Markdown (GFM) tables.
   - Preserves column headers (`<th>`), captions, and row alignment.
   - Chunks tables deterministically when row counts exceed default token thresholds.
2. **List Extraction**:
   - Parses unordered (`<ul>`) and ordered (`<ol>`) lists.
   - Annotates nested items with parent hierarchy prefixes (`[Parent: Child]`).
   - Filters navigation menus and footer boilerplate via `is_nav_or_boilerplate_list()`.
3. **Resilience to Malformed Markup**:
   - Unclosed tags (`<p>`, `<li>`, `<div>`), empty tags, and deep nesting (depth >= 4) are parsed safely without exceptions or loss of valid sibling/ancestor text.

---

## 2. Provenance and Content-Addressed Identification

Every persisted `StructuralEvidence` record retains unambiguous provenance:
- **`id`**: Formatted as `{doc_slug}_struct_{structure_type}_{block_id}_{chunk_idx}_{content_hash}`.
  - `doc_slug`: Sanitized alphanumeric document name.
  - `content_hash`: First 12 characters of SHA-256 over chunk text.
  - Guaranteed deterministic: Identical source text yields identical IDs across repeated ingestions.
- **`source_doc`**: Uniquely associates each chunk with its source document name.
- **`structure_type`**: Distinct discriminator (`"table"` or `"list"`).
- **`metadata`**: Preserves block indices, row counts, nesting booleans, and captions for downstream inspection.

---

## 3. Document Lifecycle Semantics

### Re-Ingestion (Stale Record Eviction)
In `backend/src/precis/graph/store.py`:
```python
def add_structural_evidence(self, items: list[StructuralEvidence], ...) -> int:
    ...
    docs = {it.source_doc for it in items if it.source_doc}
    for doc in docs:
        self.delete_structural_evidence(doc)
```
- **Audit Verification**:
  - Ingested version 1 of `spec.html` (items: Old 1, Old 2). Stored count = 1.
  - Re-ingested version 2 of `spec.html` (items: New A, New B). Stored count remains 1.
  - Inspected collection: Old items were completely evicted; only New items exist.
  - Zero duplicate chunk accumulation observed.

### Deletion and Clearing
- `delete_document(doc_name)`:
  - Deletes all atomic SVOA facts for `doc_name` from `{collection_name}`.
  - Deletes all structural chunks for `doc_name` from `{collection_name}_structural`.
  - Unrelated documents remain completely untouched.
- `clear()`:
  - Synchronously purges both primary facts collection and secondary structural collection.
  - Store counts drop to 0 across both modalities.

---

## 4. Embedding Compatibility and Metric Verification

Direct code execution of `embed_text()` and inspection of `store.structural_collection` confirmed:

| Property | Configured Requirement | Actual Measured Value | Verification Method |
|---|---|---|---|
| Model Name | `all-MiniLM-L6-v2` | `all-MiniLM-L6-v2` | Loaded via `SentenceTransformer` |
| Output Dimensions | 384 dimensions | 384 float values | `len(embed_text(...))` |
| Value Range | Normalized `[-1.0, 1.0]` | L2-normalized float32 | Cosine norm verified |
| Chroma Distance Space | `cosine` | `cosine` | `coll.metadata["hnsw:space"]` |
| Similarity Mapping | `max(0, 1 - distance)` | `max(0, 1 - distance)` | `store.py:568` |

Zero secondary embedding models were introduced. Embedding operations utilize the exact same model and cache as the atomic SVOA pipeline.

---

## 5. Store Behavior Under Edge Conditions

- **Empty Structural Collection**: `query_similar_structural()` returns `[]` safely without error.
- **Non-Existent Document**: `count_structural_evidence("missing.txt")` returns `0`.
- **Unavailable Collection**: Gracefully handled by `hasattr(store, "has_structural_evidence")` checks in orchestrator.
