"""
Showcases the 6-stage offline pipeline:
Hardware calibration, Coreference resolution, SVOA extraction,
4-term SDH scoring, Query-adaptive context packing, and Local LLM inference.
"""

import argparse
import time

from precis.graph.store import FactStore
from precis.pipeline.coref import resolve_coreferences
from precis.pipeline.hardware import profile_hardware
from precis.pipeline.inference import (
    OllamaConnectionError,
    OllamaInferenceError,
    generate_answer,
)
from precis.pipeline.packer import pack_context, render_context
from precis.pipeline.sdh import score_facts
from precis.pipeline.svoa import extract_facts

DEFAULT_DEMO_TEXT = (
    "The European Council approved the climate transition framework in Brussels on Friday. "
    "Dr. Elena Vance testified that regional renewable capacity will double by 2030. "
    "The framework does NOT subsidize fossil fuel extraction or legacy nuclear facilities. "
    "Some industrial representatives hypothesized that emergency gas reserves might run out by December. "
    "The transition plan provides targeted economic grants to coal-dependent communities in Silesia."
)


def _print_header(title: str) -> None:
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)


def _print_stage(num: int, name: str, desc: str) -> None:
    print(f"\n[Stage {num}: {name}] | {desc}")


def run_demo(
    text: str = DEFAULT_DEMO_TEXT,
    questions: list[str] | None = None,
    interactive: bool = False,
) -> None:
    if questions is None:
        questions = [
            "What does the framework exclude or not subsidize?",
            "Who testified about renewable capacity?",
        ]

    _print_header("Précis - SVOA Semantic Density Compression for Edge RAG")
    print("Offline, zero-cloud fact extraction & context packing on consumer CPU.")

    # Stage 0: Hardware Detection
    _print_stage(
        0,
        "Hardware Calibration",
        "Profiling host environment and setting token ceiling",
    )
    hw = profile_hardware()
    print(f"  CPU Cores:          {hw.cpu_cores} ({hw.cpu_model})")
    print(f"  System RAM:         {hw.ram_gb:.1f} GB")
    print(f"  GPU Available:      {hw.has_gpu} ({hw.gpu_name or 'None'})")
    print(f"  Recommended LLM:    {hw.recommended_model}")
    print(f"  Adaptive Ceiling:   {hw.token_ceiling} tokens")

    # Stage 1: Coreference Resolution
    _print_stage(
        1,
        "Neural Coreference Resolution",
        "Resolving pronoun antecedents",
    )
    t0 = time.perf_counter()
    resolved_text = resolve_coreferences(text)
    coref_ms = int((time.perf_counter() - t0) * 1000)
    print(f"  Input length:       {len(text)} chars")
    print(f"  Resolution time:    {coref_ms} ms")

    # Stage 2: SVOA Fact Extraction
    _print_stage(
        2,
        "SVOA Extraction",
        "Parsing subject-verb-object-adjunct tuples with modality",
    )
    t0 = time.perf_counter()
    facts = extract_facts(
        resolved_text,
        source_doc="climate_framework.txt",
    )
    svoa_ms = int((time.perf_counter() - t0) * 1000)
    print(f"  Facts extracted:    {len(facts)} in {svoa_ms} ms\n")

    for idx, fact in enumerate(facts, 1):
        neg_str = " [NOT]" if fact.negated else ""
        mod_str = f" [{fact.modality.upper()}]" if fact.modality != "asserted" else ""
        adj_str = f" | adjuncts: {list(fact.adjuncts.keys())}" if fact.adjuncts else ""
        print(
            f"    ({idx}) {fact.subject} -> "
            f"{fact.verb}{neg_str} -> {fact.object}"
            f"{mod_str}{adj_str}"
        )

    # Stage 3: SDH Scoring & Fact Storage
    _print_stage(
        3,
        "Semantic Density Heuristic (SDH)",
        "Scoring 4 terms: E(s,o) + I(v) + U(t,G) + A(t)",
    )
    t0 = time.perf_counter()
    store = FactStore(
        in_memory=True,
        collection_name="demo_store",
    )
    scored_facts = score_facts(facts)
    store.add_facts(scored_facts)
    sdh_ms = int((time.perf_counter() - t0) * 1000)

    print(f"  Scored and indexed {len(scored_facts)} facts in {sdh_ms} ms")
    avg_sdh = (
        sum(fact.sdh_score for fact in scored_facts) / len(scored_facts)
        if scored_facts
        else 0.0
    )
    print(f"  Average SDH Score:  {avg_sdh:.3f}\n")

    for idx, fact in enumerate(scored_facts, 1):
        print(
            f"    Fact {idx:02d}: SDH = {fact.sdh_score:.3f} | "
            f"{fact.subject} {fact.verb} {fact.object}"
        )

    # Stage 4 & 5: Query Answering
    for q_idx, question in enumerate(questions, 1):
        _print_header(f'Query {q_idx}: "{question}"')

        # Stage 4: Packing
        _print_stage(
            4,
            "Query-Adaptive Context Packing",
            "Re-ranking by SDH x query similarity & modality pruning",
        )
        t0 = time.perf_counter()
        pack = pack_context(
            question,
            store,
            token_ceiling=hw.token_ceiling,
        )
        context = render_context(pack.packed_facts)
        pack_ms = int((time.perf_counter() - t0) * 1000)

        print(
            f"  Facts considered:   {pack.facts_considered} "
            "(hypothetical facts filtered)"
        )
        print(f"  Facts packed:       {pack.facts_packed}")
        print(f"  Packing budget:     {pack.tokens_used} tokens")
        print(f"  Naive RAG context:  ~{pack.naive_rag_tokens} words")
        print(f"  Compression rate:   {pack.compression_rate:.1%}")
        print(f"  Packing latency:    {pack_ms} ms\n")

        print("  --- Rendered Packed Context for LLM ---")
        for line in context.split("\n"):
            print(f"    {line}")
        print("  ---------------------------------------\n")

        # Stage 5: Inference
        _print_stage(
            5,
            "Local LLM Inference",
            f"Prompting {hw.recommended_model}",
        )
        t0 = time.perf_counter()

        try:
            print("  Answer: ", end="", flush=True)

            stream_gen = generate_answer(
                query=question,
                context=context,
                model=hw.recommended_model,
                stream=True,
            )

            while True:
                try:
                    token = next(stream_gen)
                    print(token, end="", flush=True)
                except StopIteration as exc:
                    inference_result = exc.value
                    break

            print()

            if inference_result is not None:
                print(f"  Generated tokens:  {inference_result.tokens_generated}")
                print(f"  Prompt tokens:     {inference_result.prompt_tokens}")

        except (OllamaConnectionError, OllamaInferenceError) as exc:
            print(f"\n  [Local LLM unavailable: {exc}]")
            print("  Simulated answering from packed context:")

            for fact in pack.packed_facts:
                if fact.negated:
                    print(
                        f"  -> Explicit exclusion: "
                        f"{fact.subject} does NOT "
                        f"{fact.verb} {fact.object}"
                    )
                else:
                    print(f"  -> Assertion: {fact.subject} {fact.verb} {fact.object}")

        inf_ms = int((time.perf_counter() - t0) * 1000)
        print(f"  Inference latency:  {inf_ms} ms")

    if interactive:
        _print_header("Interactive Query Mode")
        print("Type your questions (or 'exit' to quit):")

        while True:
            try:
                user_q = input("\n[Question] > ").strip()

                if not user_q or user_q.lower() in ("exit", "quit", "q"):
                    break

                pack = pack_context(
                    user_q,
                    store,
                    token_ceiling=hw.token_ceiling,
                )
                context = render_context(pack.packed_facts)

                print(
                    f"  Packed {pack.facts_packed} facts | "
                    f"{pack.tokens_used} tokens | "
                    f"{pack.compression_rate:.1%} compression"
                )

                try:
                    stream_gen = generate_answer(
                        query=user_q,
                        context=context,
                        model=hw.recommended_model,
                        stream=True,
                    )

                    print("  Answer: ", end="", flush=True)

                    while True:
                        try:
                            token = next(stream_gen)
                            print(token, end="", flush=True)
                        except StopIteration:
                            break

                    print()

                except (OllamaConnectionError, OllamaInferenceError) as exc:
                    print(f"  [Local LLM unavailable: {exc}]")
                    print(f"  Answer (context): {context}")

            except (KeyboardInterrupt, EOFError):
                break

    _print_header("Demo Completed Successfully")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Précis CLI Demonstration",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Launch interactive query prompt after demo",
    )
    args = parser.parse_args()
    run_demo(interactive=args.interactive)


if __name__ == "__main__":
    main()
