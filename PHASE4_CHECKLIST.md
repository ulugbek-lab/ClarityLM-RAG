# Phase 4 — Final verification checklist

1. Activate `claritylm_env`, run `python -m pip install -r requirements.txt`.
2. `python -m pytest -q` — all Phase 2 and Phase 4 tests must pass.
3. `python -m compileall -q app utils` — no syntax errors.
4. `cd frontend && npm install && npm run build` — TypeScript and production build must succeed.
5. Start FastAPI (`uvicorn app.main:app --reload`) and Vite (`cd frontend && npm run dev`) in separate terminals.
6. Open `http://127.0.0.1:8000/health`; expect `{"status":"ok"}`.
7. Upload a TXT file: `The project code is ORBIT-42.` through frontend. Confirm chunk count and document listing.
8. Ask `What is the project code?` with RAG **on**. Confirm at least one source refers to your uploaded file; evaluate answer against the source.
9. Turn RAG **off**, ask again; expect response without retrieved source cards.
10. Upload a same-name TXT with different content; confirm current answer corresponds to new version.
11. Try unsupported extension and file over 5 MiB; confirm sensible errors.
12. Test responsive layout on a narrow browser window and loading/empty/error states.
13. Check `git diff --cached --name-only` before commit; ensure no `.env`, `clarityLM/`, model weights, `.DS_Store` or Python caches.
14. Commit and push only after tests and full local flow succeed.

## Known limitations / boundaries

- `/ingest-path` is now disabled unless `ENABLE_INGEST_PATH=true` (local development only).
- Uploads persist in Qdrant, but sidebar document listing and chat history reset on refresh.
- No account isolation, authentication, rate limiting, or document deletion UI. Avoid a public multi-user deployment.
- Native PDF text extraction only; scanned images require OCR not included in this project.
- The generated output depends on the LoRA adapter and local hardware; test real answers rather than assuming correctness from HTTP 200.
