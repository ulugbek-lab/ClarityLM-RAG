from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile

from app.dto.Rag import (
    IngestPathRequest, IngestPathResponse, QueryRequest, QueryResponse,
    SourceItem, UploadResponse,
)
from app.services.rag_service import RAGService
from utils.source_formatting import format_source

router = APIRouter()
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
ALLOWED_SUFFIXES = {'.pdf', '.txt', '.md'}


@router.get('/health')
def health_check():
    return {'status': 'ok'}


def get_rag_service(request: Request) -> RAGService:
    return request.app.state.rag


@router.post('/upload', response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...), rag: RAGService = Depends(get_rag_service)) -> UploadResponse:
    filename = Path(file.filename or '').name
    if not filename or Path(filename).suffix.lower() not in ALLOWED_SUFFIXES:
        raise HTTPException(status_code=400, detail='Upload a PDF, TXT, or MD file.')
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    await file.close()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail='Maximum file size is 5 MiB.')
    try:
        document_id, chunks = rag.ingest_upload(filename, content)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return UploadResponse(filename=filename, chunks=chunks, document_id=document_id)


@router.post('/ingest-path', response_model=IngestPathResponse)
def ingest_path(payload: IngestPathRequest, request: Request,
                rag: RAGService = Depends(get_rag_service)) -> IngestPathResponse:
    # Local-only development tool. Disabled by default even if /docs lists it.
    if not request.app.state.settings.enable_ingest_path:
        raise HTTPException(status_code=403, detail='Filesystem ingestion is disabled.')
    try:
        ingested, skipped = rag.ingest_folder(payload.path)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return IngestPathResponse(ingested=ingested, skipped=skipped)


@router.post('/query', response_model=QueryResponse)
def query(payload: QueryRequest, rag: RAGService = Depends(get_rag_service)) -> QueryResponse:
    answer, sources = rag.answer(payload.question, use_rag=payload.use_rag)
    formatted_sources = [format_source(source) for source in sources]
    return QueryResponse(answer=answer, sources=[SourceItem(**source) for source in formatted_sources])
