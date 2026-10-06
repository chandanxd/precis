"""
Interacts with locally served Ollama instances using a strict QA prompt
template grounded in packed SVOA facts.

Supports configurable local LLMs, streaming token generation, blocking
responses, and inference performance telemetry.
"""

import json
import os
import time
from collections.abc import Generator
from dataclasses import dataclass
from typing import Any, Literal, overload

import requests

OLLAMA_DEFAULT_BASE_URL = os.getenv(
    "PRECIS_OLLAMA_BASE_URL",
    "http://localhost:11434",
)

PROMPT_TEMPLATE = """You are a precise document question-answering assistant.

Answer the question using ONLY the facts provided below.
Do not use outside knowledge, assumptions, or unstated information.

GROUNDING RULES:
- Treat each fact as information extracted from the source document.
- A fact containing "NOT" represents a negated claim. Preserve that negation in your answer.
- [attributed to X] means the claim is attributed to X. Do not present it as independently established.
- [conditional] means the claim depends on a condition. Do not present it as unconditional.
- [hypothetical] means the claim is hypothetical. Do not present it as an established event.
- Do not infer missing relationships, causes, dates, identities, or conclusions.
- If the provided facts do not contain enough information to answer the question, say so explicitly.
- Be concise and answer the question directly.
- Do not repeat facts unnecessarily.

FACTS FROM DOCUMENT:
{context}

QUESTION:
{query}

ANSWER:"""


class OllamaConnectionError(Exception):
    """Raised when the local Ollama instance cannot be reached."""


class OllamaInferenceError(Exception):
    """Raised when Ollama fails to generate a response."""


@dataclass
class InferenceResult:
    """Result and performance telemetry from local LLM inference."""

    answer: str
    model: str
    latency_ms: int
    tokens_generated: int
    prompt_tokens: int = 0


def check_ollama(base_url: str = OLLAMA_DEFAULT_BASE_URL) -> bool:
    """Check if the local Ollama daemon is running and reachable."""
    try:
        resp = requests.get(f"{base_url}/api/tags", timeout=3)
        return resp.status_code == 200
    except (requests.ConnectionError, requests.Timeout):
        return False


def build_prompt(context: str, query: str) -> str:
    """Format the grounded QA prompt from packed facts and user query."""
    clean_query = query.strip()

    if not clean_query:
        raise ValueError("Query must not be empty.")

    clean_context = (
        context.strip()
        if context and context.strip()
        else "(No relevant facts retrieved)"
    )

    return PROMPT_TEMPLATE.format(
        context=clean_context,
        query=clean_query,
    )


def _stream_ollama(
    endpoint: str,
    payload: dict[str, Any],
) -> Generator[str, None, tuple[str, int, int]]:
    """Stream tokens from Ollama, returning
    (full_answer, eval_count, prompt_eval_count).
    """
    full_answer: list[str] = []
    eval_count = 0
    prompt_eval_count = 0

    try:
        resp = requests.post(
            endpoint,
            json=payload,
            stream=True,
            timeout=120,
        )
        resp.raise_for_status()
    except requests.ConnectionError as exc:
        raise OllamaConnectionError(
            f"Could not connect to Ollama at {endpoint}"
        ) from exc
    except requests.RequestException as exc:
        raise OllamaInferenceError(f"Ollama streaming request failed: {exc}") from exc

    for line in resp.iter_lines():
        if line:
            chunk = json.loads(
                line.decode("utf-8") if isinstance(line, bytes) else line
            )

            token = chunk.get("response", "")

            if token:
                full_answer.append(token)
                yield token

            if chunk.get("done", False):
                eval_count = chunk.get(
                    "eval_count",
                    len("".join(full_answer).split()),
                )
                prompt_eval_count = chunk.get(
                    "prompt_eval_count",
                    0,
                )
                break

    return (
        "".join(full_answer),
        eval_count,
        prompt_eval_count,
    )


@overload
def generate_answer(
    query: str,
    context: str,
    model: str | None = None,
    stream: Literal[False] = False,
    base_url: str = OLLAMA_DEFAULT_BASE_URL,
    temperature: float = 0.3,
    top_p: float = 0.9,
    max_tokens: int = 512,
) -> InferenceResult: ...


@overload
def generate_answer(
    query: str,
    context: str,
    model: str | None = None,
    stream: Literal[True] = True,
    base_url: str = OLLAMA_DEFAULT_BASE_URL,
    temperature: float = 0.3,
    top_p: float = 0.9,
    max_tokens: int = 512,
) -> Generator[str, None, InferenceResult]: ...


def generate_answer(
    query: str,
    context: str,
    model: str | None = None,
    stream: bool = False,
    base_url: str = OLLAMA_DEFAULT_BASE_URL,
    temperature: float = 0.3,
    top_p: float = 0.9,
    max_tokens: int = 512,
) -> InferenceResult | Generator[str, None, InferenceResult]:
    """
    Generate an answer using local Ollama LLM.

    Args:
        query: User question.
        context: Packed context from Stage 4.
        model: Model identifier in Ollama.
        stream: If True, yields tokens one at a time and returns InferenceResult.
        base_url: Ollama API base URL.
        temperature: Sampling temperature.
        top_p: Nucleus sampling probability.
        max_tokens: Maximum tokens to generate.

    Returns:
        InferenceResult or generator yielding tokens with final InferenceResult.
    """
    if model is None:
        model = os.getenv(
            "PRECIS_OLLAMA_MODEL",
            "qwen2.5-coder:7b",
        )

    if not 0.0 <= temperature <= 2.0:
        raise ValueError("temperature must be between 0.0 and 2.0")

    if not 0.0 < top_p <= 1.0:
        raise ValueError("top_p must be between 0.0 and 1.0")

    if max_tokens <= 0:
        raise ValueError("max_tokens must be greater than 0")

    base_url = base_url.rstrip("/")
    endpoint = f"{base_url}/api/generate"
    prompt = build_prompt(context, query)

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": stream,
        "options": {
            "temperature": temperature,
            "top_p": top_p,
            "num_predict": max_tokens,
        },
    }

    start_time = time.perf_counter()

    if stream:

        def stream_generator() -> Generator[str, None, InferenceResult]:
            tokens: list[str] = []
            gen = _stream_ollama(endpoint, payload)

            try:
                while True:
                    tok = next(gen)
                    tokens.append(tok)
                    yield tok
            except StopIteration as exc:
                full_text, eval_cnt, prompt_cnt = (
                    exc.value
                    if exc.value
                    else (
                        "".join(tokens),
                        len(tokens),
                        0,
                    )
                )

                elapsed = int((time.perf_counter() - start_time) * 1000)

                return InferenceResult(
                    answer=full_text,
                    model=model,
                    latency_ms=elapsed,
                    tokens_generated=eval_cnt or len(tokens),
                    prompt_tokens=prompt_cnt,
                )

        return stream_generator()

    try:
        resp = requests.post(
            endpoint,
            json=payload,
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()

    except requests.ConnectionError as exc:
        raise OllamaConnectionError(
            f"Could not connect to Ollama at {base_url}"
        ) from exc
    except requests.RequestException as exc:
        raise OllamaInferenceError(f"Ollama inference request failed: {exc}") from exc

    elapsed_ms = int((time.perf_counter() - start_time) * 1000)

    answer = data.get("response", "")
    tokens_generated = data.get(
        "eval_count",
        len(answer.split()),
    )
    prompt_tokens = data.get(
        "prompt_eval_count",
        0,
    )

    return InferenceResult(
        answer=answer,
        model=model,
        latency_ms=elapsed_ms,
        tokens_generated=tokens_generated,
        prompt_tokens=prompt_tokens,
    )
