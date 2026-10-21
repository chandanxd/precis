# Gate 5 Evaluation Plan: Canary Deployment & Shadow Rollout

## Objective

Define the controlled validation protocol before promoting `PRECIS_ENABLE_LIST_EXTRACTION` to default-on in production.

## Prerequisites for Gate 5

1. [x] Implementation completed under `backend/src/precis/pipeline/structural.py`.
2. [x] Feature flag defaults to `False`.
3. [x] Disabled mode verified byte-identical to Condition D.
4. [x] Budget accounting defect fixed; zero ceiling violations.
5. [x] Conservative deduplication active; regression safeguards verified.
6. [x] Full test suite (468 tests) passing with zero failures.
7. [ ] User review and approval of disabled-mode PR.

## Canary Rollout Stages

### Stage 1: Disabled-Mode Telemetry Canary (0% traffic enabled)
- Deploy to staging with `PRECIS_ENABLE_LIST_EXTRACTION=0`.
- Verify telemetry latency and zero memory/CPU regression over 1,000 synthetic queries.
- Invariant: Zero list extraction calls, byte parity with pre-integration baseline.

### Stage 2: Shadow Evaluation (100% traffic shadow)
- Execute dual context construction asynchronously on live traffic:
  - Primary path: `enable_list_extraction=False` (serves user).
  - Shadow path: `enable_list_extraction=True` (logged to analytics).
- Compare latency differential (target: $< 2.5\text{ ms}$).
- Verify zero ceiling violations across live web pages.

### Stage 3: Controlled 10% Canary (A/B Test)
- Enable `PRECIS_ENABLE_LIST_EXTRACTION=1` for 10% of queries.
- Measure user satisfaction, answer containment, and exact match against gold benchmarks.
- Automated rollback trigger: any unhandled exception or latency $> 20\text{ ms}$.

### Stage 4: Promotion to Default-On
- Update default in `structural.py` from `False` to `True`.
- Retain feature flag as emergency kill-switch.
