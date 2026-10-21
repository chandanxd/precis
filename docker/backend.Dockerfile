FROM python:3.11-slim AS base

WORKDIR /app

# System dependencies for compilation and networking
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ git curl && \
    rm -rf /var/lib/apt/lists/*

# Install the package with its API and fast-coref extras. src/ must be present
# before pip runs so the package itself is installed, not just its dependencies.
COPY backend/pyproject.toml .
COPY backend/src/ src/
RUN pip install --no-cache-dir ".[api,coref-fast]"

# Bake spaCy en_core_web_lg model directly into the image
RUN python -m spacy download en_core_web_lg

# Bake Hugging Face models into the image (runtime is offline). Downloaded
# before the offline env vars below are set.
ENV HF_HOME=/opt/hf_cache
RUN python -c "from huggingface_hub import snapshot_download; \
snapshot_download('sentence-transformers/all-MiniLM-L6-v2'); \
snapshot_download('biu-nlp/f-coref')"

# Copy application entry point
COPY backend/main.py .

ENV PYTHONPATH=/app/src
ENV HF_HUB_OFFLINE=1
ENV TRANSFORMERS_OFFLINE=1

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--ws-max-size", "2097152"]
