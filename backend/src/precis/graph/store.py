import hashlib
import json
import os
import re
from collections.abc import Sequence
from typing import Any, cast

import chromadb
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection
from chromadb.api.types import Embedding, Metadata

from precis.graph.schema import Fact
from precis.pipeline.sdh import canonical_fact_text, embed_text, embed_texts

EMBEDDING_DIMENSION = 384


def _generate_fact_id(
    fact: Fact,
    occurrence: int = 0,
) -> str:
    """Generate a deterministic, filesystem-safe unique ID for a fact."""
    doc_prefix = (
        re.sub(r"[^a-zA-Z0-9_-]", "_", fact.source_doc) if fact.source_doc else "doc"
    )
    content = (
        f"{fact.source_doc}|{fact.sentence_id}|{canonical_fact_text(fact)}|{occurrence}"
    )
    hash_suffix = hashlib.sha256(content.encode("utf-8")).hexdigest()[:12]
    return f"{doc_prefix}_{fact.sentence_id}_{hash_suffix}"


def _fact_to_metadata(fact: Fact) -> dict[str, Any]:
    """Convert Fact dataclass fields to ChromaDB-compatible primitive metadata."""
    adjuncts_count = 0
    if isinstance(fact.adjuncts, dict):
        for v in fact.adjuncts.values():
            adjuncts_count += len(v) if isinstance(v, list) else 1
    return {
        "subject": fact.subject or "",
        "verb": fact.verb or "",
        "object": fact.object or "",
        "negated": bool(fact.negated),
        "modality": fact.modality or "asserted",
        "attributed_to": fact.attributed_to or "",
        "disjunctive": bool(fact.disjunctive),
        "sdh_score": float(fact.sdh_score),
        "source_doc": fact.source_doc or "",
        "sentence_id": int(fact.sentence_id),
        "raw_sentence": fact.raw_sentence or "",
        "adjunct_count": int(adjuncts_count),
        "adjuncts_json": json.dumps(fact.adjuncts) if fact.adjuncts else "{}",
    }


def _metadata_to_fact(meta: Metadata, embedding: Sequence[float] | None = None) -> Fact:
    """Reconstruct a typed Fact instance from ChromaDB metadata and embedding."""
    adjuncts: dict[str, Any] = {}
    adjuncts_json = meta.get("adjuncts_json")
    if isinstance(adjuncts_json, str) and adjuncts_json:
        try:
            parsed_adjuncts = json.loads(adjuncts_json)
        except (json.JSONDecodeError, TypeError):
            parsed_adjuncts = {}
        if isinstance(parsed_adjuncts, dict):
            adjuncts = parsed_adjuncts
    attributed_to_value = meta.get("attributed_to", "")
    attributed_to: str | None = (
        attributed_to_value if isinstance(attributed_to_value, str) and attributed_to_value else None
    )
    sdh_score_value = meta.get("sdh_score", 0.0)
    sdh_score = (
        float(sdh_score_value) if isinstance(sdh_score_value, (int, float)) else 0.0
    )
    sentence_id_value = meta.get("sentence_id", 0)
    sentence_id = (
        int(sentence_id_value) if isinstance(sentence_id_value, (int, float)) else 0
    )
    return Fact(
        subject=str(meta.get("subject", "")),
        verb=str(meta.get("verb", "")),
        object=str(meta.get("object", "")),
        adjuncts=adjuncts,
        negated=bool(meta.get("negated", False)),
        modality=str(meta.get("modality", "asserted")),
        attributed_to=attributed_to,
        disjunctive=bool(meta.get("disjunctive", False)),
        sdh_score=sdh_score,
        embedding=list(embedding) if embedding is not None else [],
        source_doc=str(meta.get("source_doc", "")),
        sentence_id=sentence_id,
        raw_sentence=str(meta.get("raw_sentence", "")),
    )


class FactStore:
    """
    Persistent or in-memory vector fact store backed by ChromaDB.
    Indexes extracted facts using 384-dimensional cosine embeddings.
    """

    def __init__(
        self,
        persist_dir: str = "./chroma_data",
        collection_name: str = "facts",
        in_memory: bool = False,
    ) -> None:
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        self.in_memory = in_memory
        if in_memory:
            self._client: ClientAPI = chromadb.Client()
        else:
            os.makedirs(persist_dir, exist_ok=True)
            self._client = chromadb.PersistentClient(path=persist_dir)
        self._collection: Collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    @property
    def collection(self) -> Collection:
        """Return the underlying ChromaDB collection."""
        return self._collection

    def count(self) -> int:
        """Return total number of facts currently in the store."""
        return self._collection.count()

    def add_facts(self, facts: list[Fact], batch_size: int = 64) -> int:
        """
        Ingest a batch of Fact objects into the vector store.
        Reuses fact.embedding if pre-computed by SDH, otherwise computes embeddings.
        Returns the number of facts added.
        """
        if not facts:
            return 0
        # Identify facts needing embeddings
        missing_indices: list[int] = []
        texts_to_embed: list[str] = []
        for i, f in enumerate(facts):
            if not f.embedding or len(f.embedding) != EMBEDDING_DIMENSION:
                missing_indices.append(i)
                texts_to_embed.append(canonical_fact_text(f))
        if texts_to_embed:
            computed_embeddings = embed_texts(texts_to_embed, batch_size=batch_size)
            for idx, emb in zip(missing_indices, computed_embeddings):
                facts[idx].embedding = emb
        ids: list[str] = []
        documents: list[str] = []
        embeddings: list[Embedding] = []
        metadatas: list[Metadata] = []
        occurrence_counts: dict[str, int] = {}
        for f in facts:
            canonical_text = canonical_fact_text(f)
            occurrence_key = f"{f.source_doc}|{f.sentence_id}|{canonical_text}"
            occurrence = occurrence_counts.get(occurrence_key, 0)
            occurrence_counts[occurrence_key] = occurrence + 1
            ids.append(_generate_fact_id(f, occurrence))
            documents.append(canonical_text)
            embeddings.append(cast(Embedding, f.embedding))
            metadatas.append(_fact_to_metadata(f))
        # Use upsert to be safe against re-ingestion
        self._collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )
        return len(facts)

    def query_similar(
        self,
        query: str,
        n_results: int = 20,
        modality_filter: str | Sequence[str] | None = None,
        source_doc: str | None = None,
    ) -> list[tuple[Fact, float]]:
        """
        Retrieve facts most similar to the query string by cosine similarity.
        Args:
            query: Query text (question or keyword phrase).
            n_results: Maximum candidate facts to return.
            modality_filter: Single modality or collection of modalities to include.
            source_doc: Restrict search to a specific source document.
        Returns:
            List of (Fact, cosine_similarity) tuples sorted descending by similarity.
        """
        if not query or not query.strip() or self._collection.count() == 0:
            return []
        query_emb = embed_text(query)
        # Build where clause
        where_clauses: list[dict[str, Any]] = []
        if modality_filter:
            if isinstance(modality_filter, str):
                where_clauses.append({"modality": modality_filter})
            elif len(modality_filter) == 1:
                where_clauses.append({"modality": next(iter(modality_filter))})
            elif len(modality_filter) > 1:
                where_clauses.append({"modality": {"$in": list(modality_filter)}})
        if source_doc:
            where_clauses.append({"source_doc": source_doc})
        where_filter: dict[str, Any] | None = None
        if len(where_clauses) == 1:
            where_filter = where_clauses[0]
        elif len(where_clauses) > 1:
            where_filter = {"$and": where_clauses}
        actual_k = min(n_results, self._collection.count())
        if actual_k <= 0:
            return []
        results = self._collection.query(
            query_embeddings=[query_emb],
            n_results=actual_k,
            where=where_filter,
            include=["metadatas", "distances", "embeddings"],
        )
        if not results or not results.get("ids") or not results["ids"][0]:
            return []
        ids = results["ids"][0]
        metadatas_result = results.get("metadatas")
        metadatas: list[Metadata] = (
            cast(list[Metadata], metadatas_result[0])
            if metadatas_result and metadatas_result[0] is not None
            else []
        )

        distances_result = results.get("distances")
        distances: list[float] = (
            cast(list[float], distances_result[0])
            if distances_result and distances_result[0] is not None
            else []
        )

        embeddings_result = results.get("embeddings")
        embeddings: list[Sequence[float]] = (
            cast(list[Sequence[float]], embeddings_result[0])
            if embeddings_result and embeddings_result[0] is not None
            else []
        )
        ranked_facts: list[tuple[Fact, float]] = []
        for i in range(len(ids)):
            meta = metadatas[i] if i < len(metadatas) else {}
            dist = distances[i] if i < len(distances) else 1.0
            emb = embeddings[i] if i < len(embeddings) else None
            fact = _metadata_to_fact(meta, embedding=emb)
            # For cosine space in ChromaDB: distance = 1 - cosine_similarity
            similarity = max(0.0, min(1.0, 1.0 - float(dist)))
            ranked_facts.append((fact, round(similarity, 4)))
        # Sort descending by similarity
        ranked_facts.sort(key=lambda x: x[1], reverse=True)
        return ranked_facts

    def get_by_modality(self, modality: str, limit: int | None = None) -> list[Fact]:
        """Retrieve stored facts matching a given modality tier."""
        if self._collection.count() == 0:
            return []
        get_kwargs: dict[str, Any] = {
            "where": {"modality": modality},
            "include": ["metadatas", "embeddings"],
        }
        if limit is not None:
            get_kwargs["limit"] = limit
        results = self._collection.get(**get_kwargs)
        if not results or not results.get("metadatas"):
            return []
        metadatas = results.get("metadatas")
        if metadatas is None:
            return []

        embeddings = results.get("embeddings")
        facts: list[Fact] = []

        for i, meta in enumerate(metadatas):
            emb = (
                embeddings[i]
                if embeddings is not None and i < len(embeddings)
                else None
            )
            embedding: Sequence[float] | None = list(emb) if emb is not None else None
            facts.append(_metadata_to_fact(meta, embedding=embedding))

        return facts

    def get_by_document(self, source_doc: str, limit: int | None = None) -> list[Fact]:
        """Retrieve all stored facts originating from a specific source document."""
        if self._collection.count() == 0:
            return []
        get_kwargs: dict[str, Any] = {
            "where": {"source_doc": source_doc},
            "include": ["metadatas", "embeddings"],
        }
        if limit is not None:
            get_kwargs["limit"] = limit
        results = self._collection.get(**get_kwargs)
        if not results or not results.get("metadatas"):
            return []
        metadatas = results.get("metadatas")
        if metadatas is None:
            return []

        embeddings = results.get("embeddings")
        facts: list[Fact] = []

        for i, meta in enumerate(metadatas):
            emb = (
                embeddings[i]
                if embeddings is not None and i < len(embeddings)
                else None
            )
            embedding: Sequence[float] | None = list(emb) if emb is not None else None
            facts.append(_metadata_to_fact(meta, embedding=embedding))

        return facts

    def get_all_embeddings(self) -> list[list[float]]:
        """
        Return all stored fact embeddings as a list of float vectors.
        Used for U(t,G) uniqueness calculations during SDH scoring.
        """
        if self._collection.count() == 0:
            return []
        results = self._collection.get(include=["embeddings"])
        embeddings = results.get("embeddings")
        if embeddings is None:
            return []

        embedding_vectors = cast(list[Sequence[float]], embeddings)
        return [list(e) for e in embedding_vectors]

    def get_all_documents(self) -> list[str]:
        """Return a sorted list of unique source document names currently stored."""
        if self._collection.count() == 0:
            return []
        results = self._collection.get(include=["metadatas"])
        metadatas = results.get("metadatas")
        if metadatas is None:
            return []
        docs: set[str] = set()
        for metadata in metadatas:
            doc = metadata.get("source_doc")
            if isinstance(doc, str) and doc:
                docs.add(doc)
        return sorted(docs)

    def stats(self) -> dict[str, Any]:
        """Return comprehensive summary metrics regarding stored facts."""
        total = self._collection.count()
        if total == 0:
            return {
                "total_facts": 0,
                "negated_count": 0,
                "modality_breakdown": {},
                "avg_sdh_score": 0.0,
                "document_count": 0,
                "documents": [],
            }
        results = self._collection.get(include=["metadatas"])

        metadatas = results.get("metadatas")
        if metadatas is None:
            return {
                "total_facts": total,
                "negated_count": 0,
                "modality_breakdown": {},
                "avg_sdh_score": 0.0,
                "document_count": 0,
                "documents": [],
            }

        negated = 0
        modalities: dict[str, int] = {}
        sdh_total = 0.0
        docs: set[str] = set()

        for m in metadatas:
            if m.get("negated", False):
                negated += 1

            mod = str(m.get("modality", "asserted"))
            modalities[mod] = modalities.get(mod, 0) + 1

            sdh_score = m.get("sdh_score", 0.0)
            if isinstance(sdh_score, (int, float)):
                sdh_total += float(sdh_score)

            doc = m.get("source_doc")
            if isinstance(doc, str) and doc:
                docs.add(doc)
        return {
            "total_facts": total,
            "negated_count": negated,
            "modality_breakdown": modalities,
            "avg_sdh_score": round(sdh_total / total, 4) if total > 0 else 0.0,
            "document_count": len(docs),
            "documents": sorted(docs),
        }

    def delete_document(self, source_doc: str) -> int:
        """
        Delete all facts originating from a specific source document.
        Returns the number of deleted facts.
        """
        if not source_doc or self._collection.count() == 0:
            return 0
        results = self._collection.get(
            where={"source_doc": source_doc},
        )
        ids = results.get("ids", [])
        if ids:
            self._collection.delete(ids=ids)
        return len(ids)

    def clear(self) -> int:
        """Delete all facts from the collection. Returns count of deleted facts."""
        count = self._collection.count()
        if count > 0:
            all_data = self._collection.get()
            ids = all_data.get("ids", [])
            if ids:
                self._collection.delete(ids=ids)
        return count
