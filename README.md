# Précis

> Epistemically-typed SVOA compression for CPU-viable edge RAG.

**Status:** Under development

## Overview
Précis decomposes documents into structured facts (Subject-Verb-Object-Adjunct),
scores them using the SDH heuristic, and packs the most salient facts into a
Token-budgeted context window for local LLM inference.

## Stack
- **Backend:** Python 3.11, FastAPI, spaCy, ChromaDB, Ollama
- **Frontend:** React, Vite, 3d-force-graph

## Structure
- `/pipeline` - 6-stage NLP pipeline (hardware -> co-reference -> SVOA -> SDH -> pack -> inference)
- `/graph` - Fact schema and ChromaDB store
- `/evaluation` - NaturalQuestions benchmark harness
- `/demo` - Quick demo scripts
- `/tests` - Unit and integration tests

## Setup
Coming soon.
