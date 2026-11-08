from pathlib import Path
import hashlib
import uuid

from app.core.config import Settings
from app.services.embeddings_service import EmbeddingService
from app.services.llm_service import LocalLLM
from app.services.qdrant_service import QdrantService

# orchestrator 
class RAGService:
    def __init__(
        self,
        settings: Settings,
        embeddings: EmbeddingService,
        qdrant: QdrantService,
        llm: LocalLLM,
    ) -> None:
        self._settings = settings
        self._embeddings = embeddings
        self._qdrant = qdrant
        self._llm = llm

    def ingest(self, documents: list[dict]) -> int:
        return self._qdrant.upsert_documents(documents) # pass docs to qdrant

    def ingest_folder(self, path: str) -> tuple[int, int]:
        root = Path(path).expanduser() # OS 
        documents: list[dict] = [] 
        skipped = 0
        ignore_dirs = {'.git', '.venv', '__pycache__', 'node_modules'}
        for file_path in root.rglob('*'):
            if not file_path.is_file():
                continue
            if any(part in ignore_dirs for part in file_path.parts):
                continue
            try:
                text = file_path.read_text(encoding='utf-8')
            except (OSError, UnicodeDecodeError):
                skipped += 1
                continue
            if not text.strip():
                skipped += 1
                continue
            if file_path.suffix.lower() == '.py':
                chunks = self._chunk_python(text)
            else:
                chunks = self._chunk_text(text)
            if not chunks:
                skipped += 1
                continue
            for index, chunk in enumerate(chunks):
                doc_id = self._stable_id(file_path, chunk, index)
                documents.append(
                    {
                        'id': doc_id,
                        'text': chunk,
                        'metadata': {'path': str(file_path), 'chunk': index},
                    }
                )
        ingested = self._qdrant.upsert_documents(documents) if documents else 0
        return ingested, skipped

    def answer(self, question: str) -> tuple[str, list[dict]]:
        filtered: list[dict] = []
        context = ''
        if self._settings.rag_enabled and self._settings.rag_mode != 'never':
            query_vector = self._embeddings.embed_texts([question])[0]
            sources = self._qdrant.search(query_vector, limit=self._settings.top_k)
            filtered = [source for source in sources if source['score'] >= self._settings.min_score]
            use_rag = self._settings.rag_mode == 'always'
            if self._settings.rag_mode == 'auto':
                use_rag = not self._is_general_question(question)
                if filtered:
                    top_score = max(source['score'] for source in filtered)
                    if top_score < self._settings.min_score_strict:
                        use_rag = False
            if use_rag and filtered:
                max_sources = min(self._settings.top_k, self._settings.max_sources)
                filtered = filtered[:max_sources]
                context = self._build_context(filtered)
            else:
                filtered = []
                context = ''
        answer = self._llm.generate(self._build_prompt(question, context))
        answer = self._clean_answer(answer)
        result = (answer, filtered)
        return result

    def _build_context(self, sources: list[dict]) -> str:
        chunks = []
        total = 0
        for index, source in enumerate(sources, start=1):
            text = source['text']
            if not text:
                continue
            path = source.get('metadata', {}).get('path')
            if path:
                text = f'[{index}] {path}\n{text}'
            if total + len(text) > self._settings.max_context_chars:
                break
            chunks.append(text)
            total += len(text)
        return '\n\n'.join(chunks)

    def _build_prompt(self, question: str, context: str) -> str:
        if not context:
            context = 'No relevant context.'
        return (
            'Answer the user question using the context when relevant. '
            'Include code in fenced blocks when you provide code. '
            'Keep the answer to 2-5 sentences. '
            'Do not include any additional questions or the words "Question:" or "Answer:".\n\n'
            f'Context:\n{context}\n\nQuestion: {question}\nAnswer:'
        )

    def _chunk_text(self, text: str) -> list[str]:
        size = max(1, self._settings.chunk_size_chars)
        overlap = max(0, min(self._settings.chunk_overlap_chars, size - 1))
        chunks = []
        start = 0
        length = len(text)
        while start < length:
            end = min(start + size, length)
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            if end == length:
                break
            start = end - overlap
        return chunks

    def _chunk_python(self, text: str) -> list[str]:
        lines = text.splitlines()
        blocks: list[str] = []
        preamble: list[str] = []
        current: list[str] = []
        capture = False

        def flush_current():
            if current:
                block = '\n'.join(current).strip()
                if block:
                    blocks.append(block)

        for line in lines:
            stripped = line.lstrip()
            is_top_level = len(line) == len(stripped)
            is_def = is_top_level and (stripped.startswith('def ') or stripped.startswith('class '))
            is_decorator = is_top_level and stripped.startswith('@')
            if is_def:
                flush_current()
                current = [line]
                capture = True
                continue
            if is_decorator and not capture:
                preamble.append(line)
                continue
            if is_decorator and capture:
                current.append(line)
                continue
            if capture:
                current.append(line)
            else:
                preamble.append(line)

        flush_current()
        preamble_text = '\n'.join(preamble).strip()
        if preamble_text:
            blocks.insert(0, preamble_text)
        if not blocks:
            return self._chunk_text(text)
        return blocks

    def _stable_id(self, file_path: Path, text: str, index: int) -> str: # Use different
        digest = hashlib.sha1(text.encode('utf-8', errors='ignore')).hexdigest()
        return str(uuid.uuid5(uuid.NAMESPACE_URL, f'{file_path}:{index}:{digest}'))

    def _clean_answer(self, answer: str) -> str: # use clean , do not repeat 
        for marker in ('\nQuestion:', '\n\nQuestion:', 'Question:', '\nContext:', '\n\nContext:', 'Context:'):
            if marker in answer:
                answer = answer.split(marker, 1)[0]
        return answer.strip()

    def _is_general_question(self, question: str) -> bool: # use rag for general questions
        q = question.lower()
        project_markers = (
            'project',
            'repo',
            'codebase',
            'file',
            'path',
            'where',
            'implemented',
            'implementation',
            'class',
            'function',
            'endpoint',
            'api',
            'controller',
            'service',
            'module',
            'route',
        )
        if any(marker in q for marker in project_markers):
            return False
        if '\\' in q or '/' in q:
            return False
        return True
