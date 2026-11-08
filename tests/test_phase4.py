from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes import router
from app.services.rag_service import RAGService


def make_client(enable_ingest_path=False):
    app = FastAPI()
    app.include_router(router)
    app.state.settings = SimpleNamespace(enable_ingest_path=enable_ingest_path)
    app.state.rag = SimpleNamespace(ingest_folder=lambda path: (1, 0))
    return TestClient(app)


def test_health():
    response = make_client().get('/health')
    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}


def test_filesystem_ingestion_disabled_by_default():
    response = make_client().post('/ingest-path', json={'path': '/tmp/documents'})
    assert response.status_code == 403


def test_filesystem_ingestion_can_be_opted_in_for_local_dev():
    response = make_client(True).post('/ingest-path', json={'path': '/tmp/documents'})
    assert response.status_code == 200
    assert response.json() == {'ingested': 1, 'skipped': 0}


def test_prompt_uses_finetuning_format():
    prompt = RAGService._build_prompt('What is ORBIT-42?', '[1] notes.txt\nORBIT-42', True)
    assert prompt.startswith('### Instruction:')
    assert prompt.endswith('### Response:')
    assert 'ORBIT-42' in prompt
