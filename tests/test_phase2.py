from types import SimpleNamespace

from app.services.rag_service import RAGService


class FakeEmbeddings:
    def embed_texts(self, texts):
        return [[0.5, 0.5] for _ in texts]


class FakeQdrant:
    def __init__(self):
        self.saved = []
        self.calls = 0

    def replace_document(self, document_id, documents):
        self.saved = documents
        return len(documents)

    def search(self, vector, limit):
        self.calls += 1
        return [{'id': 'a', 'text': 'The secret code is ORBIT-42.', 'score': 0.8,
                 'metadata': {'path': 'notes.txt'}}]


class FakeLLM:
    def __init__(self):
        self.last_prompt = None

    def generate(self, prompt):
        self.last_prompt = prompt
        return 'The code is ORBIT-42.'


def make_service():
    cfg = SimpleNamespace(chunk_size_chars=1200, chunk_overlap_chars=200,
                          rag_enabled=True, top_k=5, min_score=0.25,
                          max_sources=2, max_context_chars=4000)
    qdrant, llm = FakeQdrant(), FakeLLM()
    return RAGService(cfg, FakeEmbeddings(), qdrant, llm), qdrant, llm


def test_upload_creates_chunks_and_reuses_document_id():
    rag, qdrant, _ = make_service()
    doc_id, count = rag.ingest_upload('notes.txt', b'Project code is ORBIT-42.')
    assert count == 1
    assert qdrant.saved[0]['metadata']['document_id'] == doc_id
    assert rag.ingest_upload('notes.txt', b'Updated content')[0] == doc_id


def test_retrieval_switch():
    rag, qdrant, llm = make_service()
    answer, sources = rag.answer('What is the secret code?', use_rag=True)
    assert sources and 'ORBIT-42' in llm.last_prompt
    assert '### Instruction:' in llm.last_prompt
    _, sources = rag.answer('What is the secret code?', use_rag=False)
    assert not sources
    assert qdrant.calls == 1


def test_rejects_unknown_file_type():
    rag, _, _ = make_service()
    try:
        rag.ingest_upload('script.exe', b'abc')
    except ValueError:
        pass
    else:
        assert False, 'Expected rejection'
