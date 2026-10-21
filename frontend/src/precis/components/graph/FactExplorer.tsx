import { useState, useMemo, useEffect } from "react";
import type { Fact, Modality } from "../../types/api";
import { fetchAllFacts } from "../../services/api";
import { FactCard } from "../chat/FactCard";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select";
import {
  Search,
  SlidersHorizontal,
  Table,
  Network,
  Slash,
  X,
  Filter,
  BarChart3,
  Layers,
  Share2,
  Loader2,
} from "lucide-react";

export const FactExplorer = () => {
  const [facts, setFacts] = useState<Fact[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isLive, setIsLive] = useState<boolean>(false);
  const [loadError, setLoadError] = useState<boolean>(false);
  const [totalFacts, setTotalFacts] = useState<number | null>(null);
  const [search, setSearch] = useState<string>("");
  const [modalityFilter, setModalityFilter] = useState<Modality | "all">("all");
  const [negatedOnly, setNegatedOnly] = useState<boolean>(false);
  const [minSdh, setMinSdh] = useState<number>(0.0);
  const [viewMode, setViewMode] = useState<"table" | "graph">("table");
  const [selectedFact, setSelectedFact] = useState<Fact | null>(null);

  useEffect(() => {
    let isMounted = true;
    setIsLoading(true);
    fetchAllFacts()
      .then(({ facts: loadedFacts, isLive: liveStatus, total }) => {
        if (isMounted) {
          setFacts(loadedFacts);
          setTotalFacts(total);
          setIsLive(liveStatus);
          setLoadError(false);
          if (loadedFacts.length > 0) setSelectedFact(loadedFacts[0] ?? null);
          setIsLoading(false);
        }
      })
      .catch(() => {
        if (isMounted) {
          setLoadError(true);
          setIsLoading(false);
        }
      });
    return () => {
      isMounted = false;
    };
  }, []);

  // Filter logic
  const filteredFacts = useMemo(() => {
    return facts.filter((f) => {
      if (modalityFilter !== "all" && f.modality !== modalityFilter) return false;
      if (negatedOnly && !f.negated) return false;
      if (f.sdh_score < minSdh) return false;

      if (search.trim()) {
        const q = search.toLowerCase();
        const matchSubject = f.subject.toLowerCase().includes(q);
        const matchVerb = f.verb.toLowerCase().includes(q);
        const matchObject = f.object.toLowerCase().includes(q);
        const matchAdjuncts = Object.values(f.adjuncts || {}).some((v) =>
          Array.isArray(v)
            ? v.some((item) => String(item).toLowerCase().includes(q))
            : String(v).toLowerCase().includes(q),
        );
        const matchAttr = f.attributed_to?.toLowerCase().includes(q);
        return matchSubject || matchVerb || matchObject || matchAdjuncts || matchAttr;
      }

      return true;
    });
  }, [facts, search, modalityFilter, negatedOnly, minSdh]);

  // Modality breakdown stats
  const stats = useMemo(() => {
    const total = facts.length;
    const asserted = facts.filter((f) => f.modality === "asserted").length;
    const conditional = facts.filter((f) => f.modality === "conditional").length;
    const attributed = facts.filter((f) => f.modality === "attributed").length;
    const hypothetical = facts.filter((f) => f.modality === "hypothetical").length;
    const negated = facts.filter((f) => f.negated).length;
    const avgSdh = facts.reduce((acc, f) => acc + f.sdh_score, 0) / (total || 1);

    return { total, asserted, conditional, attributed, hypothetical, negated, avgSdh };
  }, [facts]);
  // Share of the loaded facts, as a whole-number percentage (0 when none are loaded).
  const pct = (n: number) => (stats.total ? Math.round((n / stats.total) * 100) : 0);

  // Graph Data positioning
  const graphData = useMemo(() => {
    const nodeMap = new Map<
      string,
      { id: string; name: string; type: "subject" | "object"; count: number }
    >();
    const links: {
      source: string;
      target: string;
      verb: string;
      negated: boolean;
      modality: Modality;
      sdh: number;
      fact: Fact;
    }[] = [];

    filteredFacts.forEach((f) => {
      const sKey = `s_${f.subject}`;
      const oKey = `o_${f.object}`;

      if (!nodeMap.has(sKey)) {
        nodeMap.set(sKey, { id: sKey, name: f.subject, type: "subject", count: 1 });
      } else {
        nodeMap.get(sKey)!.count += 1;
      }

      if (!nodeMap.has(oKey)) {
        nodeMap.set(oKey, { id: oKey, name: f.object, type: "object", count: 1 });
      } else {
        nodeMap.get(oKey)!.count += 1;
      }

      links.push({
        source: sKey,
        target: oKey,
        verb: f.verb,
        negated: f.negated,
        modality: f.modality,
        sdh: f.sdh_score,
        fact: f,
      });
    });

    const nodes = Array.from(nodeMap.values());
    const total = nodes.length;
    const radius = Math.min(240, Math.max(150, total * 24));
    const centerX = 340;
    const centerY = 240;

    const positionedNodes = nodes.map((node, i) => {
      const angle = (i / (total || 1)) * 2 * Math.PI;
      return {
        ...node,
        x: centerX + radius * Math.cos(angle),
        y: centerY + radius * Math.sin(angle),
      };
    });

    const nodeLookup = new Map(positionedNodes.map((n) => [n.id, n]));

    const positionedLinks = links.map((link) => ({
      ...link,
      sourceNode: nodeLookup.get(link.source),
      targetNode: nodeLookup.get(link.target),
    }));

    return { nodes: positionedNodes, links: positionedLinks };
  }, [filteredFacts]);

  return (
    <div className="flex-1 min-h-0 w-full flex flex-col font-mono gap-[0.5rem] p-2 lg:p-3 overflow-hidden">
      {/* Top Toolbar */}
      <div className="border border-[var(--bd)] bg-[var(--bg-2)] p-[0.5rem] flex flex-col md:flex-row md:items-center justify-between gap-[0.5rem] text-[0.75rem] shrink-0">
        {/* Search Bar */}
        <div className="flex items-center gap-[0.5rem] flex-1 max-w-md border border-[var(--bd)] bg-[var(--bg)] px-[0.625rem] py-[0.3125rem]">
          <Search size={13} strokeWidth={1.5} className="text-[var(--tx-3)]" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search facts by subject, verb, object, adjunct..."
            className="w-full bg-transparent border-0 outline-none text-[0.75rem] text-[var(--tx)] placeholder:text-[var(--tx-3)]"
          />
          {search && (
            <button
              type="button"
              onClick={() => setSearch("")}
              className="text-[var(--tx-3)] hover:text-[var(--tx)]"
            >
              <X size={12} />
            </button>
          )}
        </div>

        {/* Filters */}
        <div className="flex items-center gap-[0.5rem] flex-wrap">
          <div className="flex items-center gap-[0.375rem] border border-[var(--bd)] px-[0.5rem] py-[0.25rem] bg-[var(--bg)]">
            <Filter size={12} strokeWidth={1.5} className="text-[var(--tx-3)]" />
            <span className="text-[var(--tx-2)] text-[0.6875rem]">MODALITY:</span>
            <Select
              value={modalityFilter}
              onValueChange={(value) => setModalityFilter(value as Modality | "all")}
            >
              <SelectTrigger
                aria-label="Filter facts by modality"
                className="precis-modality-trigger"
              >
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="precis-modality-menu">
                <SelectItem value="all">ALL</SelectItem>
                <SelectItem value="asserted">ASSERTED</SelectItem>
                <SelectItem value="conditional">CONDITIONAL</SelectItem>
                <SelectItem value="attributed">ATTRIBUTED</SelectItem>
                <SelectItem value="hypothetical">HYPOTHETICAL</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <button
            type="button"
            onClick={() => setNegatedOnly(!negatedOnly)}
            className={`flex items-center gap-[0.375rem] border px-[0.625rem] py-[0.25rem] transition-colors ${
              negatedOnly
                ? "bg-[var(--inv-bg)] text-[var(--inv-tx)] border-[var(--tx)] font-semibold"
                : "border-[var(--bd)] bg-[var(--bg)] text-[var(--tx-2)] hover:text-[var(--tx)]"
            }`}
          >
            <Slash size={11} strokeWidth={2} />
            <span>NEGATED ONLY</span>
          </button>

          <div className="flex items-center gap-[0.375rem] border border-[var(--bd)] px-[0.625rem] py-[0.25rem] bg-[var(--bg)]">
            <SlidersHorizontal size={12} strokeWidth={1.5} className="text-[var(--tx-3)]" />
            <span className="text-[var(--tx-3)] text-[0.6875rem]">MIN SDH:</span>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={minSdh}
              onChange={(e) => setMinSdh(parseFloat(e.target.value))}
              aria-label="Filter facts by minimum SDH score"
              className="w-[4rem] accent-[var(--tx)] cursor-pointer"
            />
            <span className="font-bold text-[var(--tx)]">{minSdh.toFixed(2)}</span>
          </div>

          {/* View Switcher */}
          <div className="flex items-center border border-[var(--bd)] bg-[var(--bg)] p-[0.125rem]">
            <button
              type="button"
              onClick={() => setViewMode("table")}
              className={`p-[0.25rem] flex items-center gap-[0.25rem] px-[0.5rem] text-[0.6875rem] ${
                viewMode === "table"
                  ? "bg-[var(--inv-bg)] text-[var(--inv-tx)] font-bold"
                  : "text-[var(--tx-2)] hover:text-[var(--tx)]"
              }`}
            >
              <Table size={12} strokeWidth={1.5} />
              <span>TABLE</span>
            </button>
            <button
              type="button"
              onClick={() => setViewMode("graph")}
              className={`p-[0.25rem] flex items-center gap-[0.25rem] px-[0.5rem] text-[0.6875rem] ${
                viewMode === "graph"
                  ? "bg-[var(--inv-bg)] text-[var(--inv-tx)] font-bold"
                  : "text-[var(--tx-2)] hover:text-[var(--tx)]"
              }`}
            >
              <Network size={12} strokeWidth={1.5} />
              <span>GRAPH</span>
            </button>
          </div>
        </div>
      </div>

      {/* Main Content Area: 2-Column Full-Height Split */}
      <div className="flex-1 min-h-0 w-full flex flex-col lg:flex-row gap-[0.75rem] overflow-hidden">
        {/* Left Stage: Table or Graph (Fills Height) */}
        <div className="flex-1 min-h-0 h-full border border-[var(--bd)] bg-[var(--bg)] overflow-hidden flex flex-col">
          {/* Subheader info bar */}
          <div className="h-[2rem] px-[0.75rem] border-b border-[var(--bd)] bg-[var(--bg-2)] flex items-center justify-between text-[0.6875rem] text-[var(--tx-3)] shrink-0 select-none">
            <div className="flex items-center gap-[0.5rem]">
              <span>
                INDEXED FACTS:{" "}
                <span className="font-bold text-[var(--tx)]">{filteredFacts.length}</span> /{" "}
                {totalFacts ?? facts.length}
              </span>
              <span
                className={`px-[0.375rem] py-[0.0625rem] text-[0.5625rem] border ${
                  isLive
                    ? "border-[var(--accent)] text-[var(--tx)] bg-[var(--bg-3)]"
                    : "border-[var(--bd)] text-[var(--tx-4)] bg-[var(--bg)]"
                }`}
              >
                {isLive ? "LIVE DATA" : loadError ? "BACKEND UNAVAILABLE" : "OFFLINE FIXTURE"}
              </span>
            </div>
            <div className="flex items-center gap-[0.5rem]">
              <span>CLICK ROW TO INSPECT SVOA TUPLE</span>
            </div>
          </div>

          {isLoading ? (
            <div className="flex-1 min-h-0 flex items-center justify-center gap-[0.5rem] text-[0.75rem] text-[var(--tx-3)]">
              <Loader2 size={14} className="animate-spin" />
              <span>Loading facts from knowledge store...</span>
            </div>
          ) : viewMode === "table" ? (
            <div className="flex-1 min-h-0 overflow-y-auto overflow-x-auto">
              <table className="w-full text-left text-[0.75rem] border-collapse">
                <thead>
                  <tr className="border-b border-[var(--bd)] bg-[var(--bg-2)] text-[var(--tx-3)] uppercase tracking-wider sticky top-0 z-10 text-[0.6875rem]">
                    <th className="p-[0.5rem] font-medium">Modality</th>
                    <th className="p-[0.5rem] font-medium">Subject</th>
                    <th className="p-[0.5rem] font-medium">Predicate</th>
                    <th className="p-[0.5rem] font-medium">Object</th>
                    <th className="p-[0.5rem] font-medium">Adjuncts</th>
                    <th className="p-[0.5rem] font-medium text-right">SDH Score</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--bd)]">
                  {filteredFacts.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="p-[2rem] text-center text-[var(--tx-3)] italic">
                        {facts.length === 0
                          ? "No facts indexed. Ingest a document in the Docs tab to extract propositions."
                          : "No facts match current filter parameters."}
                      </td>
                    </tr>
                  ) : (
                    filteredFacts.map((fact, index) => {
                      const isSelected = selectedFact === fact;
                      return (
                        <tr
                          key={index}
                          onClick={() => setSelectedFact(fact)}
                          className={`cursor-pointer transition-colors ${
                            isSelected
                              ? "bg-[var(--bg-3)] border-l-[0.1875rem] border-l-[var(--accent)]"
                              : "hover:bg-[var(--bg-2)]"
                          }`}
                        >
                          <td className="p-[0.5rem] whitespace-nowrap">
                            <span
                              className={`px-[0.375rem] py-[0.125rem] text-[0.625rem] uppercase font-mono ${
                                fact.modality === "asserted"
                                  ? "bg-[var(--inv-bg)] text-[var(--inv-tx)] font-semibold"
                                  : fact.modality === "conditional"
                                    ? "border border-[var(--tx-2)] text-[var(--tx)]"
                                    : fact.modality === "attributed"
                                      ? "border border-[var(--bd-3)] text-[var(--tx-2)]"
                                      : "border border-dashed border-[var(--tx-3)] text-[var(--tx-2)]"
                              }`}
                            >
                              {fact.modality}
                            </span>
                            {fact.negated && (
                              <span className="ml-[0.25rem] px-[0.25rem] py-[0.0625rem] text-[0.5625rem] border border-[var(--tx)] text-[var(--tx)] font-bold">
                                NEG
                              </span>
                            )}
                          </td>
                          <td className="p-[0.5rem] font-semibold text-[var(--tx)] whitespace-nowrap">
                            {fact.subject}
                          </td>
                          <td className="p-[0.5rem] text-[var(--tx-2)] whitespace-nowrap">
                            <span className="px-[0.375rem] py-[0.125rem] bg-[var(--bg-2)] border border-[var(--bd)] font-mono">
                              {fact.negated ? `¬ ${fact.verb}` : fact.verb}
                            </span>
                          </td>
                          <td className="p-[0.5rem] text-[var(--tx)] max-w-xs truncate">
                            {fact.object}
                          </td>
                          <td className="p-[0.5rem] text-[0.6875rem] text-[var(--tx-3)]">
                            {Object.keys(fact.adjuncts || {}).length > 0 ? (
                              <span className="truncate max-w-[12rem] block">
                                {Object.entries(fact.adjuncts)
                                  .map(([k, v]) => `${k}:${Array.isArray(v) ? v.join("/") : v}`)
                                  .join(", ")}
                              </span>
                            ) : (
                              <span className="text-[var(--tx-4)]">--</span>
                            )}
                          </td>
                          <td className="p-[0.5rem] text-right font-bold text-[var(--tx)] whitespace-nowrap">
                            {fact.sdh_score.toFixed(3)}
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          ) : (
            /* Epistemic Vector SVG Force Graph (Full-Height) */
            <div className="flex-1 min-h-0 relative bg-[var(--bg)] flex items-center justify-center overflow-hidden">
              <svg className="w-full h-full select-none" viewBox="0 0 680 480">
                <g className="links">
                  {graphData.links.map((link, idx) => {
                    if (!link.sourceNode || !link.targetNode) return null;
                    const midX = (link.sourceNode.x + link.targetNode.x) / 2;
                    const midY = (link.sourceNode.y + link.targetNode.y) / 2;

                    return (
                      <g
                        key={idx}
                        onClick={() => setSelectedFact(link.fact)}
                        className="cursor-pointer"
                      >
                        <line
                          x1={link.sourceNode.x}
                          y1={link.sourceNode.y}
                          x2={link.targetNode.x}
                          y2={link.targetNode.y}
                          stroke="var(--tx-3)"
                          strokeWidth={link.negated ? 1.5 : 1}
                          strokeDasharray={
                            link.modality === "conditional"
                              ? "4 4"
                              : link.modality === "hypothetical"
                                ? "2 2"
                                : link.negated
                                  ? "6 3"
                                  : undefined
                          }
                          opacity={0.65}
                        />
                        <rect
                          x={midX - 28}
                          y={midY - 8}
                          width={56}
                          height={16}
                          fill="var(--bg)"
                          stroke="var(--bd)"
                          strokeWidth={1}
                        />
                        <text
                          x={midX}
                          y={midY + 3}
                          fontSize={9}
                          fontFamily="monospace"
                          fill="var(--tx-2)"
                          textAnchor="middle"
                        >
                          {link.negated ? `¬ ${link.verb}` : link.verb}
                        </text>
                      </g>
                    );
                  })}
                </g>

                <g className="nodes">
                  {graphData.nodes.map((node) => {
                    const isSubject = node.type === "subject";
                    return (
                      <g
                        key={node.id}
                        transform={`translate(${node.x}, ${node.y})`}
                        className="cursor-pointer"
                      >
                        <circle
                          r={isSubject ? 8 : 6}
                          fill={isSubject ? "var(--inv-bg)" : "var(--bg)"}
                          stroke="var(--tx)"
                          strokeWidth={1.5}
                        />
                        <text
                          y={isSubject ? -12 : 16}
                          fontSize={10}
                          fontFamily="monospace"
                          fontWeight={isSubject ? "bold" : "normal"}
                          fill="var(--tx)"
                          textAnchor="middle"
                          className="pointer-events-none"
                        >
                          {node.name}
                        </text>
                      </g>
                    );
                  })}
                </g>
              </svg>

              <div className="absolute bottom-[0.5rem] left-[0.5rem] p-[0.5rem] border border-[var(--bd)] bg-[var(--bg-2)] text-[0.625rem] text-[var(--tx-3)] flex flex-col gap-[0.25rem]">
                <div className="flex items-center gap-[0.375rem]">
                  <span className="w-[0.625rem] h-[0.625rem] rounded-full bg-[var(--inv-bg)] border border-[var(--tx)] inline-block" />
                  <span>Subject Node</span>
                </div>
                <div className="flex items-center gap-[0.375rem]">
                  <span className="w-[0.5rem] h-[0.5rem] rounded-full bg-[var(--bg)] border border-[var(--tx)] inline-block" />
                  <span>Object Node</span>
                </div>
                <div className="flex items-center gap-[0.375rem]">
                  <span className="w-[1rem] border-b border-[var(--tx-3)] inline-block" />
                  <span>Solid: Asserted</span>
                </div>
                <div className="flex items-center gap-[0.375rem]">
                  <span className="w-[1rem] border-b border-dashed border-[var(--tx-3)] inline-block" />
                  <span>Dashed: Conditional/Negated</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Right Stage: Fact Inspector & Store Diagnostics Studio */}
        <div className="w-full lg:w-[26rem] xl:w-[28rem] h-full min-h-0 border border-[var(--bd)] bg-[var(--bg)] flex flex-col shrink-0 overflow-hidden">
          <div className="h-[2.5rem] border-b border-[var(--bd)] px-[0.75rem] flex items-center justify-between select-none shrink-0 bg-[var(--bg-2)]">
            <div className="flex items-center gap-[0.375rem] text-[0.75rem] font-bold text-[var(--tx)]">
              <Share2 size={13} strokeWidth={1.5} />
              <span>{selectedFact ? "FACT SCHEMA INSPECTOR" : "KNOWLEDGE METRICS"}</span>
            </div>
            {selectedFact && (
              <button
                type="button"
                onClick={() => setSelectedFact(null)}
                className="text-[0.6875rem] text-[var(--tx-3)] hover:text-[var(--tx)]"
              >
                DESELECT
              </button>
            )}
          </div>

          <div className="flex-1 min-h-0 overflow-y-auto p-[0.75rem] flex flex-col gap-[0.75rem]">
            {selectedFact ? (
              <>
                <FactCard fact={selectedFact} isSelected={true} />

                <div className="flex flex-col gap-[0.25rem]">
                  <span className="text-[0.6875rem] text-[var(--tx-3)] uppercase font-semibold">
                    Syntactic & Epistemic Schema
                  </span>
                  <pre className="p-[0.625rem] border border-[var(--bd)] bg-[var(--bg-2)] text-[var(--tx-2)] text-[0.625rem] overflow-x-auto leading-relaxed">
                    {JSON.stringify(selectedFact, null, 2)}
                  </pre>
                </div>
              </>
            ) : (
              /* Store Diagnostics and Modality Proportions (Never Empty) */
              <div className="flex flex-col gap-[0.75rem]">
                <div className="border border-[var(--bd)] bg-[var(--bg-2)] p-[0.75rem] flex flex-col gap-[0.5rem]">
                  <div className="flex items-center justify-between text-[0.75rem] font-bold text-[var(--tx)]">
                    <div className="flex items-center gap-[0.375rem]">
                      <BarChart3 size={13} />
                      <span>MODALITY BREAKDOWN</span>
                    </div>
                    <span>
                      {totalFacts !== null && totalFacts > stats.total
                        ? `FIRST ${stats.total} OF ${totalFacts}`
                        : `${stats.total} TOTAL`}
                    </span>
                  </div>

                  <div className="flex flex-col gap-[0.375rem] text-[0.6875rem] pt-[0.25rem]">
                    <div className="flex items-center justify-between">
                      <span className="text-[var(--tx-2)]">Asserted Claims:</span>
                      <span className="font-bold text-[var(--tx)]">
                        {stats.asserted} ({pct(stats.asserted)}%)
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-[var(--tx-2)]">Conditional Rules:</span>
                      <span className="font-bold text-[var(--tx)]">
                        {stats.conditional} ({pct(stats.conditional)}%)
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-[var(--tx-2)]">Attributed Quotes:</span>
                      <span className="font-bold text-[var(--tx)]">
                        {stats.attributed} ({pct(stats.attributed)}%)
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-[var(--tx-2)]">Hypothetical Forecasts:</span>
                      <span className="font-bold text-[var(--tx)]">
                        {stats.hypothetical} ({pct(stats.hypothetical)}%)
                      </span>
                    </div>
                    <div className="flex items-center justify-between border-t border-[var(--bd)] pt-[0.25rem]">
                      <span className="text-[var(--tx-2)]">Negated Statements:</span>
                      <span className="font-bold text-[var(--tx)]">{stats.negated}</span>
                    </div>
                  </div>
                </div>

                <div className="border border-[var(--bd)] bg-[var(--bg-2)] p-[0.75rem] flex flex-col gap-[0.375rem] text-[0.6875rem]">
                  <div className="flex items-center gap-[0.375rem] font-bold text-[var(--tx)]">
                    <Layers size={13} />
                    <span>SDH SALIENCE METRICS</span>
                  </div>
                  <div className="flex items-center justify-between pt-[0.25rem]">
                    <span className="text-[var(--tx-2)]">Average Salience Heuristic:</span>
                    <span className="font-bold text-[var(--tx)]">{stats.avgSdh.toFixed(3)}</span>
                  </div>
                  <p className="text-[0.625rem] text-[var(--tx-3)] leading-relaxed pt-[0.25rem]">
                    SDH weights frequency, entity distance, modality certainty, and query term
                    relevance to rank facts for edge context packing.
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
