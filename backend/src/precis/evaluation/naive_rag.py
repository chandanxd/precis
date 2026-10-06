"""
Naive RAG baseline for document question answering evaluation.

Splits source documents into 512-word overlapping chunks, embeds chunks,
retrieves top-k chunks by cosine similarity, and passes the retrieved
context verbatim to the local LLM.

Used as the comparative baseline in Précis research evaluation.
"""

from precis.pipeline.inference import (
    OLLAMA_DEFAULT_BASE_URL,
    generate_answer,
)
from precis.pipeline.sdh import (
    cosine_similarity,
    embed_text,
    embed_texts,
)

DEFAULT_MODEL = "qwen2.5-coder:7b"
DEFAULT_TOP_K = 5
DEFAULT_CHUNK_SIZE = 512
DEFAULT_OVERLAP = 128


def chunk_document(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> list[str]:
    """
    Split text into overlapping word-level chunks.

    Args:
        text: Source document content.
        chunk_size: Target number of words per chunk.
        overlap: Number of overlapping words between adjacent chunks.

    Returns:
        List of chunk strings.

    Raises:
        ValueError: If chunk_size is invalid or overlap is not smaller
            than chunk_size.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero.")

    if overlap < 0:
        raise ValueError("overlap must not be negative.")

    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size.")

    if not text or not text.strip():
        return []

    words = text.strip().split()

    if not words:
        return []

    if len(words) <= chunk_size:
        return [" ".join(words)]

    chunks: list[str] = []
    step = chunk_size - overlap
    start = 0

    while start < len(words):
        end = min(
            start + chunk_size,
            len(words),
        )

        chunks.append(" ".join(words[start:end]))

        if end >= len(words):
            break

        start += step

    return chunks


def naive_rag_retrieve(
    document: str,
    query: str,
    top_k: int = DEFAULT_TOP_K,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> tuple[list[str], int]:
    """
    Retrieve the top-k chunks from a document by cosine similarity.

    Args:
        document: Source document content.
        query: User question.
        top_k: Maximum number of chunks to retrieve.
        chunk_size: Number of words per chunk.
        overlap: Number of overlapping words between adjacent chunks.

    Returns:
        A tuple containing:
        - retrieved chunks
        - total retrieved context word count

    Raises:
        ValueError: If top_k is invalid.
    """
    if top_k <= 0:
        raise ValueError("top_k must be greater than zero.")

    chunks = chunk_document(
        document,
        chunk_size=chunk_size,
        overlap=overlap,
    )

    if not chunks:
        return [], 0

    query_embedding = embed_text(query)
    chunk_embeddings = embed_texts(chunks)

    scored: list[tuple[str, float]] = []

    for chunk, embedding in zip(
        chunks,
        chunk_embeddings,
    ):
        similarity = cosine_similarity(
            query_embedding,
            embedding,
        )

        scored.append((chunk, similarity))

    scored.sort(
        key=lambda item: item[1],
        reverse=True,
    )

    top_chunks = [chunk for chunk, _ in scored[:top_k]]

    context_words = sum(len(chunk.split()) for chunk in top_chunks)

    return top_chunks, context_words


def naive_rag_answer(
    document: str,
    query: str,
    model_name: str = DEFAULT_MODEL,
    top_k: int = DEFAULT_TOP_K,
    base_url: str = OLLAMA_DEFAULT_BASE_URL,
) -> tuple[str, int]:
    """
    Execute the Naive RAG baseline:

        Chunk -> Embed -> Top-k Retrieval -> Generate

    Args:
        document: Source document content.
        query: User question.
        model_name: Ollama model identifier.
        top_k: Maximum number of chunks to retrieve.
        base_url: Ollama server URL.

    Returns:
        A tuple containing:
        - generated answer
        - retrieved context word count
    """
    top_chunks, context_words = naive_rag_retrieve(
        document=document,
        query=query,
        top_k=top_k,
    )

    context = "\n\n".join(top_chunks) if top_chunks else "(No context retrieved)"

    result = generate_answer(
        query=query,
        context=context,
        model=model_name,
        stream=False,
        base_url=base_url,
    )

    return result.answer, context_words
