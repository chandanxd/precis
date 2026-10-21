// @ts-nocheck — static view; intentionally NOT connected to the backend.
import { FlaskConical, ListChecks, FolderTree } from "lucide-react";

// The findings are the README's "What the experiments found" section, word for
// word; keep the two in step. Every number in them is computed by the analysis
// scripts below from the stored per-case records (see the paper for the tables).
const FINDINGS = [
  {
    head: "Keeping structure matters.",
    body: "Rewriting tables as extracted sentences cut exact match to 14.0%, against 49.5% for native tables.",
  },
  {
    head: "Simple structure-keeping baselines are as good as G on short pages.",
    body: "On a fresh, protocol-first cohort, G (48.0% EM) was within 2 points of raw-markup chunks, table-aware chunks, whole-document Markdown and hybrid BM25 + dense retrieval, with each of three generators from three model families.",
  },
  {
    head: "On long pages G is clearly worse.",
    body: "On 200 full Wikipedia pages (median 7,093 words), where the 2,048-token ceiling binds, G scored 22.0% EM against 33.0–41.5% for every baseline. Structure-first packing with same-document suppression filled the context with lists and dropped every prose fact. Table-aware chunking was best.",
  },
  {
    head: "The failure can be repaired.",
    body: "Two changes (suppress only facts covered by the packed table, not every fact of the page; skip reference and external-link lists), tested on a fresh draw of 200 full pages, raised G from 17.5% to 33.5% EM (+16.0 points), non-inferior to table-aware chunking (experiments/long_doc_fixed_g/).",
  },
  {
    head: "The fact-only configuration trailed plain chunks",
    body: "wherever the two were compared, and its negation flag is unreliable (extractor audit, paper §6.8).",
  },
  {
    head: "Answer format dominates exact match.",
    body: "A short-answer prompt raised EM by 25–37 points, but an answer-equivalence judge saw gains of only 1.5–12 points.",
  },
];

const EXPERIMENTS = [
  {
    name: "Fresh table cohort (protocol-first)",
    folder: "experiments/fresh_table_cohort/",
    script: "scripts/analyze_fresh_table_cohort.py",
  },
  {
    name: "Baseline adequacy, ceiling sweeps, thresholds",
    folder: "experiments/baseline_budget/",
    script: "scripts/analyze_baseline_budget.py",
  },
  {
    name: "Three generators from three model families",
    folder: "experiments/generator_family/",
    script: "scripts/analyze_generator_family.py",
  },
  {
    name: "Long-document cohort (full pages)",
    folder: "experiments/long_doc_cohort/",
    script: "scripts/analyze_long_doc_cohort.py",
  },
  {
    name: "Repaired rule G2 on a fresh long-document draw",
    folder: "experiments/long_doc_fixed_g/",
    script: "scripts/analyze_long_doc_fixed_g.py",
  },
  {
    name: "Answer format × abstention (2×2) and judge",
    folder: "experiments/prompt_validation/",
    script: "scripts/analyze_followup.py",
  },
  {
    name: "Extractor audit (negation and modality)",
    folder: "experiments/extractor_eval/",
    script: "scripts/r7_score_extractor.py",
  },
  {
    name: "Generator selection (earlier study)",
    folder: "experiments/model_comparison/",
    script: "experiments/model_comparison/analyze_results.py",
  },
];

const Card = ({ icon: Icon, title, tag, children }) => (
  <div className="border border-[var(--bd)] bg-[var(--bg)] p-[0.75rem] flex flex-col gap-[0.5rem]">
    <div className="flex items-center justify-between border-b border-[var(--bd)] pb-[0.375rem]">
      <div className="flex items-center gap-[0.375rem]">
        <Icon size={14} strokeWidth={1.5} />
        <span className="font-bold text-[0.75rem] uppercase text-[var(--tx)]">{title}</span>
      </div>
      <span className="text-[0.6875rem] text-[var(--tx-3)]">{tag}</span>
    </div>
    {children}
  </div>
);

export const EvaluationView = () => (
  <div className="flex-1 min-h-0 overflow-y-auto p-[1rem] font-mono">
    <div className="max-w-[72rem] mx-auto flex flex-col gap-[0.75rem]">
      <Card icon={FlaskConical} title="Evaluation" tag="OFFLINE · NOT RUN FROM THIS APP">
        <p className="text-[0.75rem] text-[var(--tx-2)] leading-relaxed">
          The experiments were run offline with the scripts in this repository, on table-bearing
          Wikipedia pages from Natural Questions (MRQA short extracts and full pages). This page
          summarises what they found and where each one lives; the paper has the full tables,
          intervals and limitations. Nothing here is computed live.
        </p>
      </Card>

      <Card icon={ListChecks} title="What the experiments found" tag="FROM THE README">
        <ul className="flex flex-col gap-[0.5rem] text-[0.75rem] leading-relaxed">
          {FINDINGS.map((f) => (
            <li key={f.head} className="text-[var(--tx-2)]">
              <span className="font-bold text-[var(--tx)]">{f.head}</span> {f.body}
            </li>
          ))}
        </ul>
        <p className="text-[0.6875rem] text-[var(--tx-3)]">
          Read the paper&apos;s Limitations section before reusing these results.
        </p>
      </Card>

      <Card icon={FolderTree} title="Experiments" tag="PROTOCOL · RECORDS · ANALYSIS">
        <p className="text-[0.6875rem] text-[var(--tx-3)]">
          Each folder holds the protocol (PROTOCOL.md with its SHA-256 hash, where protocol-first),
          deviations, per-case records and analysis outputs. The analysis scripts make no model
          calls and regenerate the stored outputs.
        </p>
        <div className="flex flex-col text-[0.6875rem]">
          {EXPERIMENTS.map((e) => (
            <div
              key={e.folder}
              className="grid grid-cols-1 md:grid-cols-[1.2fr_1fr_1.2fr] gap-[0.25rem] md:gap-[0.75rem] border-b border-[var(--bd)] py-[0.375rem]"
            >
              <span className="text-[var(--tx)]">{e.name}</span>
              <code className="text-[var(--tx-2)] break-all">{e.folder}</code>
              <code className="text-[var(--tx-3)] break-all">{e.script}</code>
            </div>
          ))}
        </div>
      </Card>
    </div>
  </div>
);
