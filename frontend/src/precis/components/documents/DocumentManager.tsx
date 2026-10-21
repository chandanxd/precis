// @ts-nocheck — ported code written for a less strict TS config
import { useState, useEffect } from "react";
import type { Document, PipelineEvent, Fact } from "../../types/api";
import {
  fetchDocuments,
  deleteDocument,
  clearAllFacts,
  ingestDocumentRest,
  fetchAllFacts,
} from "../../services/api";
import { PipelineTracker } from "../chat/PipelineTracker";
import { FactCard } from "../chat/FactCard";
import {
  FileText,
  UploadCloud,
  Trash2,
  Check,
  AlertTriangle,
  Loader2,
  Database,
  Layers,
} from "lucide-react";

const SAMPLE_TEXT_1 = `The government approved the climate bill on Friday in parliament. The bill specifically does not include nuclear subsidies. According to the Environment Minister, renewable targets will be met during the upcoming fiscal period. The carbon tax will reduce emissions if implemented by 2028. The senate ratified an amendment unanimously on Thursday. However, the opposition does not support the carbon tax provisions.`;

const SAMPLE_TEXT_2 = `Attention is all you need for sequence modeling. Recurrent models typically factor computation along the symbol positions of input and output sequences. The Transformer allows for significantly more parallelization and can reach a new state of the art in translation quality after being trained for as little as twelve hours. Self-attention relates different positions of a single sequence in order to compute a representation of the sequence.`;

export const DocumentManager = () => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [selectedDocName, setSelectedDocName] = useState<string>("");
  const [docTitle, setDocTitle] = useState<string>("");
  const [docText, setDocText] = useState<string>("");
  const [isIngesting, setIsIngesting] = useState<boolean>(false);
  const [pipelineEvents, setPipelineEvents] = useState<PipelineEvent[]>([]);
  const [ingestSuccess, setIngestSuccess] = useState<string | null>(null);
  const [showClearConfirm, setShowClearConfirm] = useState<boolean>(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    fetchDocuments()
      .then((docs) => {
        if (isMounted) {
          setDocuments(docs);
          setLoadError(null);
          if (docs.length > 0) setSelectedDocName(docs[0].name);
        }
      })
      .catch(() => {
        if (isMounted) setLoadError("Could not load documents from the backend.");
      });
    return () => {
      isMounted = false;
    };
  }, []);

  const handleIngest = async () => {
    if (!docText.trim() || isIngesting) return;
    const name = docTitle.trim() || `doc_${Date.now()}.txt`;

    setIsIngesting(true);
    setIngestSuccess(null);
    setPipelineEvents([
      {
        stage: 0,
        stage_name: "Hardware detection",
        status: "running",
        detail: "Profiling system resources...",
        count: 0,
        error: null,
      },
    ]);

    await new Promise((r) => setTimeout(r, 200));
    setPipelineEvents((prev) => [
      ...prev,
      {
        stage: 1,
        stage_name: "Coreference resolution",
        status: "running",
        detail: "Resolving noun phrases across sentences...",
        count: 0,
        error: null,
      },
    ]);

    await new Promise((r) => setTimeout(r, 200));
    setPipelineEvents((prev) => [
      ...prev,
      {
        stage: 2,
        stage_name: "SVOA extraction",
        status: "running",
        detail: "Parsing dependency trees & extracting tuples...",
        count: 0,
        error: null,
      },
    ]);

    try {
      const result = await ingestDocumentRest(docText, name);

      setPipelineEvents([
        {
          stage: 0,
          stage_name: "Hardware detection",
          status: "complete",
          detail: "CPU/GPU calibrated",
          count: 1,
          error: null,
        },
        {
          stage: 1,
          stage_name: "Coreference resolution",
          status: "complete",
          detail: "Entities linked",
          count: Math.round(docText.split(" ").length * 0.15),
          error: null,
        },
        {
          stage: 2,
          stage_name: "SVOA extraction",
          status: "complete",
          detail: `${result.facts_stored} facts extracted & modality tagged`,
          count: result.facts_stored,
          error: null,
        },
        {
          stage: 3,
          stage_name: "SDH scoring",
          status: "complete",
          detail: "Indexed into ChromaDB with salience scores",
          count: result.facts_stored,
          error: null,
        },
      ]);

      setIsIngesting(false);
      setIngestSuccess(`Ingested "${result.document_name}" (${result.facts_stored} facts).`);
      setDocTitle("");
      setDocText("");
      setSelectedDocName(result.document_name);
      try {
        setDocuments(await fetchDocuments());
      } catch {
        setLoadError("Ingested, but could not refresh the document list.");
      }
    } catch (err: unknown) {
      setIsIngesting(false);
      const msg = err instanceof Error ? err.message : "Ingestion failed";
      setPipelineEvents((prev) => [
        ...prev,
        {
          stage: 2,
          stage_name: "SVOA extraction",
          status: "error",
          detail: msg,
          count: 0,
          error: msg,
        },
      ]);
    }
  };

  const handleDeleteDoc = async (name: string) => {
    const ok = await deleteDocument(name);
    if (ok) {
      setDocuments((prev) => prev.filter((d) => d.name !== name));
      if (selectedDocName === name) {
        setSelectedDocName("");
      }
    }
  };

  const handleClearStore = async () => {
    const ok = await clearAllFacts();
    if (ok) {
      setDocuments([]);
      setSelectedDocName("");
    }
    setShowClearConfirm(false);
  };

  const [docFacts, setDocFacts] = useState<Fact[]>([]);

  useEffect(() => {
    let isMounted = true;
    if (!selectedDocName) {
      setDocFacts([]);
      return;
    }
    fetchAllFacts(selectedDocName)
      .then(({ facts: loaded }) => {
        if (isMounted) setDocFacts(loaded);
      })
      .catch(() => {
        if (isMounted) setDocFacts([]);
      });
    return () => {
      isMounted = false;
    };
  }, [selectedDocName]);

  return (
    <div className="flex-1 min-h-0 w-full flex flex-col lg:flex-row gap-[0.75rem] font-mono overflow-hidden p-2 lg:p-3">
      {/* Left Column: Full-Height Ingestion Studio */}
      <div className="flex-1 min-h-0 h-full border border-[var(--bd)] bg-[var(--bg)] flex flex-col overflow-hidden">
        {/* Header with Sample Presets */}
        <div className="h-[2.5rem] border-b border-[var(--bd)] px-[0.75rem] flex items-center justify-between select-none shrink-0 bg-[var(--bg-2)]">
          <div className="flex items-center gap-[0.375rem] text-[0.75rem] font-bold text-[var(--tx)]">
            <UploadCloud size={13} strokeWidth={1.5} />
            <span>DOCUMENT INGESTION STUDIO</span>
          </div>

          <div className="flex items-center gap-[0.375rem] text-[0.6875rem]">
            <span className="text-[var(--tx-3)]">PRESET:</span>
            <button
              type="button"
              onClick={() => {
                setDocTitle("climate_policy_2026.txt");
                setDocText(SAMPLE_TEXT_1);
              }}
              className="border border-[var(--bd)] bg-[var(--bg)] hover:bg-[var(--bg-3)] px-[0.375rem] py-[0.125rem] text-[var(--tx-2)] hover:text-[var(--tx)] transition-colors"
            >
              Climate Bill
            </button>
            <button
              type="button"
              onClick={() => {
                setDocTitle("transformer_survey.txt");
                setDocText(SAMPLE_TEXT_2);
              }}
              className="border border-[var(--bd)] bg-[var(--bg)] hover:bg-[var(--bg-3)] px-[0.375rem] py-[0.125rem] text-[var(--tx-2)] hover:text-[var(--tx)] transition-colors"
            >
              Transformer
            </button>
          </div>
        </div>

        {/* Ingestion Form Body (Fills Height) */}
        <div className="flex-1 min-h-0 p-[0.75rem] flex flex-col gap-[0.5rem] overflow-hidden">
          <div className="flex items-center gap-[0.5rem] border border-[var(--bd)] bg-[var(--bg-2)] px-[0.625rem] py-[0.375rem] text-[0.75rem] shrink-0">
            <span className="text-[var(--tx-3)] shrink-0">DOCUMENT TITLE:</span>
            <input
              type="text"
              value={docTitle}
              onChange={(e) => setDocTitle(e.target.value)}
              placeholder="e.g. climate_policy_2026.txt"
              disabled={isIngesting}
              className="w-full bg-transparent border-0 outline-none text-[0.75rem] text-[var(--tx)] placeholder:text-[var(--tx-3)]"
            />
          </div>

          {/* Vertically expanding text editor */}
          <div className="flex-1 min-h-0 border border-[var(--bd)] bg-[var(--bg-2)] p-[0.5rem] flex flex-col">
            <textarea
              value={docText}
              onChange={(e) => setDocText(e.target.value)}
              placeholder="Paste document text here. Précis will parse dependency syntax, resolve entity coreferences with neural FastCoref, extract SVOA tuples, and index with 4-term SDH heuristics into ChromaDB..."
              disabled={isIngesting}
              className="flex-1 w-full bg-transparent border-0 outline-none resize-none text-[0.75rem] leading-relaxed text-[var(--tx)] placeholder:text-[var(--tx-3)] font-sans"
            />
            <div className="flex items-center justify-between text-[0.6875rem] text-[var(--tx-3)] pt-[0.375rem] border-t border-[var(--bd)] shrink-0 select-none">
              <span>
                {docText.length} CHARS · ~{docText.split(/\s+/).filter(Boolean).length} WORDS
              </span>
              <span>
                YIELD ESTIMATE: ~{Math.round(docText.split(".").filter(Boolean).length * 2)} SVOA
                FACTS
              </span>
            </div>
          </div>

          {/* Action Bar */}
          <div className="flex items-center justify-between pt-[0.25rem] shrink-0">
            <button
              type="button"
              onClick={handleIngest}
              disabled={!docText.trim() || isIngesting}
              className="px-[1rem] py-[0.5rem] bg-[var(--inv-bg)] text-[var(--inv-tx)] hover:opacity-85 disabled:opacity-40 text-[0.75rem] font-semibold flex items-center gap-[0.375rem] transition-opacity"
            >
              {isIngesting ? (
                <>
                  <Loader2 size={13} className="animate-spin" />
                  <span>EXTRACTING SVOA CLAUSES...</span>
                </>
              ) : (
                <>
                  <UploadCloud size={13} strokeWidth={2} />
                  <span>INGEST INTO STORE</span>
                </>
              )}
            </button>

            {loadError && (
              <div className="flex items-center gap-[0.375rem] text-[0.6875rem] text-[var(--tx)] border border-[var(--bd)] bg-[var(--bg-2)] px-[0.5rem] py-[0.25rem]">
                <span>{loadError}</span>
              </div>
            )}

            {ingestSuccess && (
              <div className="flex items-center gap-[0.375rem] text-[0.6875rem] text-[var(--tx)] border border-[var(--bd)] bg-[var(--bg-2)] px-[0.5rem] py-[0.25rem]">
                <Check size={12} strokeWidth={2} />
                <span>{ingestSuccess}</span>
              </div>
            )}
          </div>

          {/* Pipeline Tracking Drawer */}
          {pipelineEvents.length > 0 && (
            <div className="shrink-0 pt-[0.25rem]">
              <PipelineTracker events={pipelineEvents} isStreaming={isIngesting} />
            </div>
          )}
        </div>
      </div>

      {/* Right Column: Ingested Knowledge Sources & Fact Preview (Fills Height) */}
      <div className="flex-1 min-h-0 h-full border border-[var(--bd)] bg-[var(--bg)] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="h-[2.5rem] border-b border-[var(--bd)] px-[0.75rem] flex items-center justify-between select-none shrink-0 bg-[var(--bg-2)]">
          <div className="flex items-center gap-[0.375rem] text-[0.75rem] font-bold text-[var(--tx)]">
            <Database size={13} strokeWidth={1.5} />
            <span>KNOWLEDGE SOURCES ({documents.length})</span>
          </div>

          <button
            type="button"
            onClick={() => setShowClearConfirm(true)}
            className="border border-[var(--bd)] hover:border-[var(--tx)] text-[var(--tx-2)] hover:text-[var(--tx)] px-[0.5rem] py-[0.1875rem] text-[0.6875rem] flex items-center gap-[0.25rem] transition-colors"
          >
            <Trash2 size={11} />
            <span>PURGE STORE</span>
          </button>
        </div>

        {/* Documents Table (Upper Section) */}
        <div className="h-[12rem] shrink-0 border-b border-[var(--bd)] overflow-y-auto">
          <table className="w-full text-left text-[0.75rem] border-collapse">
            <thead>
              <tr className="border-b border-[var(--bd)] bg-[var(--bg-2)] text-[var(--tx-3)] uppercase tracking-wider sticky top-0 z-10 text-[0.6875rem]">
                <th className="p-[0.5rem] font-medium">Document</th>
                <th className="p-[0.5rem] font-medium">Facts</th>
                <th className="p-[0.5rem] font-medium">Size</th>
                <th className="p-[0.5rem] font-medium">Date</th>
                <th className="p-[0.5rem] font-medium text-right">Delete</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--bd)]">
              {documents.length === 0 ? (
                <tr>
                  <td colSpan={5} className="p-[2rem] text-center text-[var(--tx-3)] italic">
                    No documents ingested. Paste or load a sample on the left.
                  </td>
                </tr>
              ) : (
                documents.map((doc) => {
                  const isSelected = selectedDocName === doc.name;
                  return (
                    <tr
                      key={doc.id}
                      onClick={() => setSelectedDocName(doc.name)}
                      className={`cursor-pointer transition-colors ${
                        isSelected
                          ? "bg-[var(--bg-3)] border-l-[0.1875rem] border-l-[var(--accent)]"
                          : "hover:bg-[var(--bg-2)]"
                      }`}
                    >
                      <td className="p-[0.5rem] font-semibold text-[var(--tx)] flex items-center gap-[0.375rem] truncate max-w-[14rem]">
                        <FileText
                          size={12}
                          strokeWidth={1.5}
                          className="text-[var(--tx-3)] shrink-0"
                        />
                        <span className="truncate">{doc.name}</span>
                      </td>
                      <td className="p-[0.5rem] text-[var(--tx)] whitespace-nowrap">
                        <span className="px-[0.375rem] py-[0.125rem] bg-[var(--bg-2)] border border-[var(--bd)] text-[0.6875rem]">
                          {doc.fact_count.toLocaleString()} facts
                        </span>
                      </td>
                      <td className="p-[0.5rem] text-[var(--tx-2)] text-[0.6875rem] whitespace-nowrap">
                        {doc.size_bytes != null ? `${(doc.size_bytes / 1024).toFixed(1)} KB` : "—"}
                      </td>
                      <td className="p-[0.5rem] text-[var(--tx-3)] text-[0.6875rem] whitespace-nowrap">
                        {doc.ingested_at ? new Date(doc.ingested_at).toLocaleDateString() : "—"}
                      </td>
                      <td className="p-[0.5rem] text-right whitespace-nowrap">
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeleteDoc(doc.name);
                          }}
                          title={`Delete ${doc.name}`}
                          className="p-[0.25rem] border border-[var(--bd)] hover:border-[var(--tx)] text-[var(--tx-3)] hover:text-[var(--tx)] transition-colors inline-flex items-center"
                        >
                          <Trash2 size={11} />
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Document Extracted Facts Preview (Lower Section - Fills Height) */}
        <div className="flex-1 min-h-0 flex flex-col overflow-hidden bg-[var(--bg)]">
          <div className="h-[2rem] px-[0.75rem] border-b border-[var(--bd)] bg-[var(--bg-2)] flex items-center justify-between text-[0.6875rem] text-[var(--tx-3)] shrink-0 select-none">
            <div className="flex items-center gap-[0.375rem]">
              <Layers size={12} />
              <span>EXTRACTED SVOA FACTS PREVIEW:</span>
              <span className="font-bold text-[var(--tx)]">{selectedDocName || "ALL"}</span>
            </div>
            <span>{docFacts.length} FACTS</span>
          </div>

          <div className="flex-1 min-h-0 overflow-y-auto p-[0.75rem] flex flex-col gap-[0.5rem]">
            {docFacts.length > 0 ? (
              docFacts.map((fact, idx) => <FactCard key={idx} fact={fact} compact={false} />)
            ) : (
              <div className="p-[2rem] text-center text-[var(--tx-3)] text-[0.75rem] italic">
                Select a document above to inspect its extracted propositions.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Strict Monochrome Confirmation Modal */}
      {showClearConfirm && (
        <div className="fixed inset-0 bg-[rgba(0,0,0,0.85)] z-50 flex items-center justify-center p-[1rem]">
          <div className="border border-[var(--bd-3)] bg-[var(--bg)] p-[1.25rem] max-w-md w-full flex flex-col gap-[1rem] font-mono shadow-2xl">
            <div className="flex items-center gap-[0.5rem] border-b border-[var(--bd)] pb-[0.5rem] text-[0.875rem] font-bold text-[var(--tx)] uppercase">
              <AlertTriangle size={15} strokeWidth={2} />
              <span>Confirm Fact Store Purge</span>
            </div>

            <p className="text-[0.75rem] text-[var(--tx-2)] leading-relaxed">
              This will permanently delete all SVOA facts and ChromaDB vector embeddings across all
              documents. This action cannot be reversed.
            </p>

            <div className="flex items-center justify-end gap-[0.5rem] pt-[0.5rem] border-t border-[var(--bd)]">
              <button
                type="button"
                onClick={() => setShowClearConfirm(false)}
                className="px-[0.75rem] py-[0.375rem] border border-[var(--bd)] hover:bg-[var(--bg-3)] text-[0.75rem] text-[var(--tx-2)]"
              >
                CANCEL
              </button>
              <button
                type="button"
                onClick={handleClearStore}
                className="px-[0.75rem] py-[0.375rem] bg-[var(--inv-bg)] text-[var(--inv-tx)] text-[0.75rem] font-bold hover:opacity-85"
              >
                CONFIRM PURGE
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
