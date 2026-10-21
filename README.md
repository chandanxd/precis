# Précis

**Keeping tables intact under a token budget: structure, simple baselines and answer format in local retrieval-augmented question answering.**

Précis is an offline RAG pipeline for local hardware. It keeps HTML tables and lists in native form and packs them under an
estimated-token ceiling with a guarded structural-priority rule (Candidate G). Any remaining budget is filled with
subject–verb–object–adjunct (SVOA) facts extracted from prose. Every model runs locally through Ollama; no stage calls a
cloud service.

This repository holds the system, the experiment protocols, the per-case records and the analysis scripts behind the paper
(manuscript: `paper/research-paper/`; Engineering Letters and J.UCS LaTeX versions: `paper/venues/`).

## What the experiments found

The findings cover table-bearing Wikipedia pages from Natural Questions, both MRQA's short extracts and full pages:

- **Keeping structure matters.** Rewriting tables as extracted sentences cut exact match to 14.0%, against 49.5% for native
  tables.
- **Simple structure-keeping baselines are as good as G on short pages.** On a fresh, protocol-first cohort, G (48.0% EM) was
  within 2 points of raw-markup chunks, table-aware chunks, whole-document Markdown and hybrid BM25 + dense retrieval, with
  each of three generators from three model families.
- **On long pages G is clearly worse.** On 200 full Wikipedia pages (median 7,093 words), where the 2,048-token ceiling
  binds, G scored 22.0% EM against 33.0–41.5% for every baseline. Structure-first packing with same-document suppression
  filled the context with lists and dropped every prose fact. Table-aware chunking was best.
- **The failure can be repaired.** Two changes (suppress only facts covered by the packed table, not every fact of the page;
  skip reference and external-link lists), tested on a fresh draw of 200 full pages, raised G from 17.5% to 33.5% EM
  (+16.0 points), non-inferior to table-aware chunking (`experiments/long_doc_fixed_g/`).
- **The fact-only configuration trailed plain chunks** wherever the two were compared, and its negation flag is unreliable
  (extractor audit, paper §6.8).
- **Answer format dominates exact match.** A short-answer prompt raised EM by 25–37 points, but an answer-equivalence judge
  saw gains of only 1.5–12 points.

See the paper's Limitations section before reusing these results.

## Repository layout

```text
backend/                 Python package `precis` (FastAPI service, pipeline, evaluation harness) and its tests
  src/precis/pipeline/   hardware profile, structural retention (structural.py), coreference, SVOA extraction,
                         SDH scoring, guarded packing (packer.py, orchestrator.py), routing, inference
  src/precis/graph/      fact schema and ChromaDB store
  src/precis/api/        request models, JWT auth, sanitisation, rate limiting
  src/precis/evaluation/ benchmark harness and the chunked baseline
  scripts/               MRQA conversion and failure-analysis tools
  tests/                 522 tests in 17 modules
frontend/                web interface (upload, ask, inspect the packed context and pipeline trace)
docker/, docker-compose.yml   containerised backend, frontend and nginx proxy
docs/architecture.md     system architecture and data flow
experiments/             protocol-first experiments: PROTOCOL.md (+ SHA-256 hash and timestamp written before the
                         runs), DEVIATIONS.md, manifests, per-case records and analysis outputs
results/                 earlier diagnostic runs and the paper-check outputs (results/paper_checks/)
scripts/                 experiment runners, analyses and paper checks; scripts/scoring.py is the single
                         exact-match/containment rule used in every table
paper/                   manuscript, venue LaTeX sources, figures and result tables
```

## Setup

Requirements: Python ≥ 3.11, [Ollama](https://ollama.com) and, for the interface, Node.js.

```bash
# backend
cd backend
python3 -m venv venv
venv/bin/pip install -e ".[api,eval,dev,coref-fast]"
venv/bin/python -m spacy download en_core_web_lg
venv/bin/python -m pytest -q          # 522 tests

# models used in the paper
ollama pull qwen2.5-coder:7b
ollama pull qwen3.5:4b                # prompt experiment
ollama pull qwen3.5:9b                # generator replay
ollama pull gemma4:12b                # answer-equivalence judge

# run the API (development)
venv/bin/uvicorn main:app --reload --port 8000

# frontend (second terminal)
cd ../frontend && npm install && npm run dev
```

Docker (production settings; the backend refuses to start without a signing secret):

```bash
export PRECIS_SECRET="$(openssl rand -hex 32)"
docker compose up --build             # interface on http://localhost:3000; Ollama must run on the host
```

Configuration is read from environment variables: `PRECIS_ENV`, `PRECIS_SECRET`, `PRECIS_DATA_DIR`,
`PRECIS_CORS_ORIGINS`, `PRECIS_OLLAMA_BASE_URL`, and the feature flag `PRECIS_ENABLE_LIST_EXTRACTION` (structural
retention). Outside production a development signing secret is used; never expose such an instance.

## Data

The experiments use the development split of the MRQA 2019 release of Natural Questions. It is not included in the
repository, because `backend/data/` is git-ignored. To rebuild `backend/data/nq_subset/nq_dev.jsonl`:

1. Download `NaturalQuestionsShort.jsonl.gz` (dev) from the
   [MRQA 2019 shared task](https://github.com/mrqa/MRQA-Shared-Task-2019).
2. Convert it with `backend/scripts/convert_mrqa_nq.py`.

The long-document cohort (`experiments/long_doc_cohort/`) uses the full Natural Questions dev pages from the
[Hugging Face release](https://huggingface.co/datasets/google-research-datasets/natural_questions). Its protocol states
how the documents are rebuilt.

The per-case records contain excerpts of Natural Questions / Wikipedia text (CC BY-SA 3.0).

## Reproducing the results

Every reported number is computed by a script from the stored per-case records. The analyses make no model calls and
regenerate the stored outputs byte for byte:

```bash
backend/venv/bin/python scripts/analyze_fresh_table_cohort.py     # fresh cohort, primary family
backend/venv/bin/python scripts/analyze_baseline_budget.py        # baseline adequacy, ceiling sweeps, thresholds
backend/venv/bin/python scripts/analyze_followup.py                # 2×2 answer format × abstention, judge
PYTHONPATH=backend/src backend/venv/bin/python scripts/r6_stage_loss.py   # where the answer is lost
backend/venv/bin/python scripts/r7_score_extractor.py              # extractor (negation/modality) audit
backend/venv/bin/python scripts/paper_checks_v4.py                 # non-inferiority margins, re-analyses
backend/venv/bin/python scripts/paper_checks_v5.py                 # abstention vs answerability, latency
backend/venv/bin/python scripts/analyze_generator_family.py      # three generators on the fresh cohort
backend/venv/bin/python scripts/analyze_long_doc_cohort.py       # long-document cohort (full pages)
backend/venv/bin/python scripts/analyze_long_doc_fixed_g.py      # repaired rule G2 on a fresh long-document draw
backend/venv/bin/python scripts/score_judge_validation_B.py      # second, independent judge labeller
```

To re-run the generation itself, use the runners (`scripts/run_fresh_table_cohort.py`, `scripts/run_baseline_budget.py`,
`scripts/run_generator_replay.py`, `scripts/run_long_doc_cohort.py`, `scripts/run_long_doc_fixed_g.py`, `experiments/prompt_validation/followup/run_followup.py`). They need Ollama, the
models above and the data. Decoding is greedy, but the local server is not perfectly deterministic: repeating identical
contexts changed 3 of 200 exact-match outcomes.

Each experiment folder documents its design in `PROTOCOL.md`. Check the protocols' integrity with:

```bash
sha256sum -c experiments/fresh_table_cohort/PROTOCOL.sha256 experiments/baseline_budget/PROTOCOL.sha256
(cd experiments/generator_family && sha256sum -c PROTOCOL.sha256)
(cd experiments/long_doc_cohort && sha256sum -c PROTOCOL.sha256)
(cd experiments/long_doc_fixed_g && sha256sum -c PROTOCOL.sha256)
(cd experiments/prompt_validation && sha256sum -c followup/PROTOCOL.sha256)
```

The protocols are author-held files, not entries in an external registry.

## Known limitations of the code

- **Negation scope.** The SVOA extractor attaches negation from other clauses of the same sentence to a fact (paper §6.8).
- **Table rendering.** The renderer names empty header cells `Col_n` and can leave row labels empty.
- **Budget estimate.** The token ceiling applies to a word-count estimate (1.3 tokens per word). It is not calibrated to the
  generator's tokenizer.
- **Routing and injection filtering.** The intent router is a set of English regular expressions. In the chat app, a
  question that matches no casual or general pattern goes to the documents only if a stored fact is similar enough
  (`PRECIS_CHAT_RELEVANCE_FLOOR`, default 0.27, MiniLM cosine); otherwise the model answers from its own knowledge and the
  answer is labelled "general knowledge". Follow-ups are rewritten by the generator before retrieval, and chat replies
  run with thinking off. The evaluated grounded prompt and the experiment scripts do not use this path. The
  prompt-injection filter is a basic pattern list.

## Licence

- **Code:** MIT (see `LICENSE`).
- **Manuscript text and figures:** CC BY 4.0.
- **Third-party files keep their own licences:**
  - `paper/venues/el/IAENGtran.cls` (LPPL 1.3)
  - `paper/venues/jucs/jucs2e.sty` (J.UCS author template)
  - Natural Questions excerpts in the records (CC BY-SA 3.0)

## Citation

If you use this work, cite the paper (details and archive DOI to be added on publication) and the tagged release
`paper-v1`.
