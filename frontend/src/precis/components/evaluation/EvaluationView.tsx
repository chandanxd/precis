// @ts-nocheck — static view; intentionally NOT connected to the backend.
import { useState } from "react";
import { FlaskConical, BarChart3, Layers } from "lucide-react";

// Mirrors backend/src/precis/evaluation (harness, metrics, naive_rag). Static sample data only.
const systems = [
  {
    name: "Précis (SVOA + SDH)",
    em: 0.412,
    f1: 0.538,
    rouge: 0.511,
    bert: 0.874,
    tokens: 612,
    latency: 1840,
  },
  {
    name: "SVOA similarity pack",
    em: 0.371,
    f1: 0.497,
    rouge: 0.472,
    bert: 0.861,
    tokens: 640,
    latency: 1710,
  },
  {
    name: "Naive RAG (chunked)",
    em: 0.334,
    f1: 0.461,
    rouge: 0.438,
    bert: 0.852,
    tokens: 1480,
    latency: 2630,
  },
];

const ablation = [
  { config: "Full pipeline", f1: 0.538, delta: 0 },
  { config: "− Coreference (Stage 1)", f1: 0.489, delta: -0.049 },
  { config: "− Negation / modality typing", f1: 0.502, delta: -0.036 },
  { config: "− SDH entity relatedness", f1: 0.517, delta: -0.021 },
  { config: "− SDH verb informativeness", f1: 0.524, delta: -0.014 },
  { config: "− SDH uniqueness", f1: 0.509, delta: -0.029 },
  { config: "− SDH adjunct density", f1: 0.528, delta: -0.01 },
  { config: "− Structural list extraction", f1: 0.521, delta: -0.017 },
];

const dataset = {
  name: "Natural Questions (MRQA)",
  samples: 500,
  avgDocTokens: 3120,
  avgAnswerTokens: 4.2,
  skipped: 7,
};

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

const Stat = ({ label, value }) => (
  <div className="border border-[var(--bd)] bg-[var(--bg-2)] p-[0.5rem] flex flex-col gap-[0.125rem]">
    <span className="text-[var(--tx-3)] text-[0.625rem]">{label}</span>
    <span className="text-[var(--tx)] font-bold text-[0.875rem]">{value}</span>
  </div>
);

export const EvaluationView = () => {
  const [metric, setMetric] = useState<"em" | "f1" | "rouge" | "bert">("f1");
  const labels = { em: "Exact Match", f1: "Token F1", rouge: "ROUGE-L", bert: "BERTScore" };

  return (
    <div className="flex-1 min-h-0 overflow-y-auto p-[1rem] font-mono">
      <div className="max-w-[72rem] mx-auto flex flex-col gap-[0.75rem]">
        <Card icon={FlaskConical} title="Evaluation Dataset" tag="HARNESS · OFFLINE">
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-[0.375rem] text-[0.75rem]">
            <Stat label="DATASET" value={dataset.name} />
            <Stat label="SAMPLES" value={dataset.samples} />
            <Stat label="AVG DOC TOKENS" value={dataset.avgDocTokens.toLocaleString()} />
            <Stat label="AVG ANSWER TOKENS" value={dataset.avgAnswerTokens} />
            <Stat label="SKIPPED" value={dataset.skipped} />
          </div>
        </Card>

        <Card icon={BarChart3} title="System Comparison" tag="PRÉCIS VS NAIVE RAG">
          <div className="flex flex-wrap gap-[0.375rem]">
            {Object.entries(labels).map(([k, l]) => (
              <button
                key={k}
                onClick={() => setMetric(k)}
                className={`px-[0.5rem] py-[0.25rem] text-[0.6875rem] border border-[var(--bd)] ${metric === k ? "bg-[var(--inv-bg)] text-[var(--inv-tx)]" : "bg-[var(--bg-2)] text-[var(--tx-2)]"}`}
              >
                {l}
              </button>
            ))}
          </div>
          <div className="flex flex-col gap-[0.5rem]">
            {systems.map((s) => (
              <div key={s.name} className="flex flex-col gap-[0.25rem] text-[0.6875rem]">
                <div className="flex justify-between">
                  <span className="text-[var(--tx)]">{s.name}</span>
                  <span className="font-bold text-[var(--tx)]">{s[metric].toFixed(3)}</span>
                </div>
                <div className="w-full h-[0.375rem] bg-[var(--bd)] overflow-hidden">
                  <div className="h-full bg-[var(--tx)]" style={{ width: `${s[metric] * 100}%` }} />
                </div>
              </div>
            ))}
          </div>
          <table className="w-full text-[0.6875rem] mt-[0.25rem]">
            <thead className="text-[var(--tx-3)]">
              <tr className="text-left border-b border-[var(--bd)]">
                <th className="py-[0.25rem]">SYSTEM</th>
                <th>EM</th>
                <th>F1</th>
                <th>ROUGE-L</th>
                <th>BERT</th>
                <th>CTX TOKENS</th>
                <th>LATENCY</th>
              </tr>
            </thead>
            <tbody className="text-[var(--tx)]">
              {systems.map((s) => (
                <tr key={s.name} className="border-b border-[var(--bd)]">
                  <td className="py-[0.25rem]">{s.name}</td>
                  <td>{s.em}</td>
                  <td>{s.f1}</td>
                  <td>{s.rouge}</td>
                  <td>{s.bert}</td>
                  <td>{s.tokens}</td>
                  <td>{s.latency} ms</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>

        <Card icon={Layers} title="Ablation Study" tag="TOKEN F1 DELTA">
          <div className="flex flex-col gap-[0.25rem] text-[0.6875rem]">
            {ablation.map((a) => (
              <div
                key={a.config}
                className="grid grid-cols-[1fr_4rem_4rem] gap-[0.5rem] border-b border-[var(--bd)] py-[0.25rem]"
              >
                <span className="text-[var(--tx)]">{a.config}</span>
                <span className="text-right text-[var(--tx)]">{a.f1.toFixed(3)}</span>
                <span className="text-right text-[var(--tx-3)]">
                  {a.delta === 0 ? "—" : a.delta.toFixed(3)}
                </span>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
};
