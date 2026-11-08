# ClarityLM RAG

A portfolio-focused, full-stack retrieval-augmented generation (RAG) application built with **React + TypeScript**, **FastAPI**, **Qdrant**, and a **TinyLlama 1.1B Chat model fine-tuned with LoRA**.

> Educational / local demonstration project. The model may produce inaccurate answers; verify responses against the cited source passages.

## Features

- React/TypeScript chat UI, responsive layout, loading and error feedback
- Upload PDF, TXT, or Markdown (up to 5 MiB); text is chunked and embedded
- Qdrant vector similarity search with source excerpts and scores
- Optional RAG toggle for comparing retrieved-context answers with model-only answers
- Fine-tuned ClarityLM LoRA adapter loaded through Hugging Face PEFT
- No authentication or persistent chat history (single-user local portfolio demo)

## Architecture

```text
Browser (React + TypeScript, Vite)
           | /api/* development proxy
           v
FastAPI: /health, /upload, /query
           |
         RAGService
          /      \
MiniLM embeddings  TinyLlama 1.1B + ClarityLM LoRA adapter
          |
        Qdrant Cloud
```

## Project layout

```text
app/
  api/routes.py
  core/config.py
  dto/Rag.py
  services/{embeddings_service,llm_service,qdrant_service,rag_service}.py
  main.py
utils/source_formatting.py
frontend/                # Vite + React + TypeScript
clarityLM/               # Local adapter; git-ignored
requirements.txt
.env.example
```

## Requirements

- Python 3.11, Node.js and npm
- A running Qdrant Cloud collection (or compatible Qdrant instance)
- Internet access on first run to download the TinyLlama and MiniLM base weights
- Local LoRA adapter files from your ClarityLM fine-tuning notebook, including `adapter_config.json` and `adapter_model.safetensors`

## Local setup

From repository root:

```bash
conda create -n claritylm_env python=3.11 -y
conda activate claritylm_env
python -m pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` with your **own** `QDRANT_URL` and `QDRANT_API_KEY`. Put your adapter inside `clarityLM/` or set `LLM_ADAPTER_PATH` to its location. **Do not commit model weights or `.env`.** The PEFT adapter is not the full model; the backend also loads the TinyLlama base model.

Start backend:

```bash
uvicorn app.main:app --reload
```

API docs: http://127.0.0.1:8000/docs

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Frontend: http://127.0.0.1:5173. The Vite proxy maps `/api/*` to FastAPI at `127.0.0.1:8000` and strips `/api`. To change backend host/port, adjust `frontend/vite.config.ts`.

## API

| Endpoint | Method | Purpose |
| --- | --- | --- |
| `/health` | GET | Process health |
| `/upload` | POST | Multipart `file` (PDF/TXT/MD, max 5 MiB) |
| `/query` | POST | JSON `{"question":"...","use_rag":true}` |
| `/ingest-path` | POST | Local filesystem ingestion; **disabled by default** |

`/query` responds with `answer` and `sources` containing text, score and metadata. A score is **similarity**, not an accuracy/confidence probability. Scanned PDFs with no extractable text are not supported. Uploading a file with the same filename replaces its earlier indexed chunks in this single-user demo.

For local development only, enable folder ingestion with `ENABLE_INGEST_PATH=true` in `.env`. Do **not** enable it on a publicly accessible server.

## Test / verify

```bash
conda activate claritylm_env
python -m pytest -q
python -m compileall -q app utils
cd frontend && npm run build
```

For the full integration test, start both servers, upload a TXT file containing `The project code is ORBIT-42.`, and ask `What is the project code?` with RAG enabled. The response should include a source matching your uploaded file. Repeat with RAG off (zero retrieved sources). See `PHASE4_CHECKLIST.md`.

## Deployment limitations

This repository is designed primarily for **local portfolio demonstrations**, not an unrestricted public service. A public deployment would require authentication, abuse controls / rate limits, upload isolation, privacy / retention policy, and a model inference host with sufficient RAM (and preferably GPU). A static frontend by itself cannot perform inference if the backend is offline. Chat history and displayed upload list exist only in browser memory, while indexed documents persist in Qdrant.

## Related work

ClarityLM fine-tuning notebook: https://github.com/ulugbek-lab/ClarityLM

This project adapts the architecture of the earlier `jaydari_rag` learning project and adds document uploads, a RAG toggle, and a TypeScript chat interface.
