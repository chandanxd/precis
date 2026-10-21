# Independent Test Accounting Audit

**Experiment 4.5.5 Independent Audit**  
**Date**: 2026-10-10  
**Target Metric Under Audit**: Claimed 476 Unique Non-Overlapping Tests

---

## 1. Independently Collected Test Counts

Test counts were verified by direct invocation of `./backend/venv/bin/pytest --collect-only` across all relevant test directories and files:

| Suite Name | Target Path | Collected Test Items | Execution Time (s) | Pass Rate |
|---|---|---|---|---|
| **Full Backend Suite** | `backend/tests/` | 418 | 203.48 | 100% (418/418) |
| **Persistence Remediation Audit** | `scripts/test_experiment_4_5_persistence_audit.py` | 25 | 86.27 | 100% (25/25) |
| **Experiment 4.2 Integrity Suite** | `scripts/test_experiment_4_2_integrity.py` | 13 | 0.58 | 100% (13/13) |
| **Experiment 4.3 Fixtures Suite** | `scripts/test_experiment_4_3_fixtures.py` | 5 | 0.32 | 100% (5/5) |
| **Experiment 4.4 Extractor Audit** | `scripts/test_experiment_4_4_audit_extractor.py` | 15 | 3.03 | 100% (15/15) |
| **Sum of Collected Tests** | | **476** | **293.68** | **100% (476/476)** |

---

## 2. Granular Breakdown by Module

### A. Backend Modules (`backend/tests/`): 418 Tests
- `test_svoa.py`: 107
- `test_structural_integration.py`: 47
- `test_evaluation.py`: 39
- `test_inference.py`: 27
- `test_packer.py`: 26
- `test_sdh.py`: 25
- `test_coref.py`: 24
- `test_structural_persistence.py`: 21
- `test_hardware.py`: 20
- `test_security.py`: 20
- `test_api.py`: 19
- `test_failure_analysis.py`: 17
- `test_store.py`: 17
- `test_production_wiring.py`: 9
- **Subtotal**: $107 + 47 + 39 + 27 + 26 + 25 + 24 + 21 + 20 + 20 + 19 + 17 + 17 + 9 = 418$.

### B. Script Modules (`scripts/`): 58 Tests
- `test_experiment_4_5_persistence_audit.py`: 25
- `test_experiment_4_4_audit_extractor.py`: 15
- `test_experiment_4_2_integrity.py`: 13
- `test_experiment_4_3_fixtures.py`: 5
- **Subtotal**: $25 + 15 + 13 + 5 = 58$.

$$\text{Aggregate Total} = 418 + 58 = 476$$

---

## 3. Evidence for Test-Item Non-Overlap

1. **Disjoint Filesystems**: All 14 modules in the backend suite reside in `backend/tests/`. All 4 modules in the script suite reside in `scripts/`.
2. **Zero Duplicate Node IDs**: Pytest node ID extraction confirmed 0 intersecting test node IDs between any pair of suites.
3. **No Double-Counting of Subsets**: In Experiment 4.5.2, an earlier report erroneously summed the 418 backend total with subsets of itself (e.g. adding 21 from `test_structural_persistence.py` to the total). This double-counting was resolved in 4.5.3 and remains absent in 4.5.4.

---

## 4. Assessment of the "Unique" Claim

### Semantic Overlap vs. Test-Node Uniqueness
While all 476 test functions are distinct code entities with unique pytest node identifiers:
- `test_structural_persistence.py` (in `backend/tests/`) and `test_experiment_4_5_persistence_audit.py` (in `scripts/`) both test features like `is_list_extraction_enabled()` defaults, multi-document persistence, and token budget ceilings.
- However, their test implementations differ: the audit suite in `scripts/` uses specialized multi-document regression fixtures and asserts specific defect behaviors (Tests A–G), whereas `backend/tests/test_structural_persistence.py` focuses on component-level lifecycle and schema validation.

### Corrected Formal Accounting Characterization
To avoid overstating semantic orthogonal independence:
> **Audited Characterization**: **476 distinct test functions collected across 5 non-overlapping test files/directories; zero duplicate pytest executions.**
