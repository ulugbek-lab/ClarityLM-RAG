# ClarityLM RAG — Frontend (Phase 3)

React + TypeScript + Vite + Tailwind frontend for the existing FastAPI backend.

## Run locally

Start FastAPI from the repository root (Conda environment):

```bash
conda activate claritylm_env
uvicorn app.main:app --reload
```

Then open another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open **http://127.0.0.1:5173**.

Vite proxies `/api/*` to `http://127.0.0.1:8000/*`, so no FastAPI CORS changes are required for local development. Do not directly expose the development server publicly.

## What works

- Submit questions to `POST /query` with the `use_rag` flag.
- Upload PDF/TXT/MD documents to `POST /upload` (5 MiB maximum per file).
- Display answers and expandable source passages.
- Toggle RAG on/off and reset the visible conversation.
- Show basic API connection status.

## Limitations

- Chat history and uploaded-file list are in-memory frontend state, cleared by refresh. Qdrant documents persist in your selected collection.
- The UI has no authentication or multi-user document separation. Use only in a trusted local portfolio demo until a secure multi-user design is implemented.
- Requests are non-streaming: model responses appear after generation completes.
- The FastAPI backend must be updated to Phase 2 first (`/upload`, `/query` `use_rag`).

## Build verification

```bash
npm run build
```
