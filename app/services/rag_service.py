import hashlib
import io
import uuid
from pathlib import Path

from pypdf import PdfReader

from app.core.config import Settings
from app.services.embeddings_service import EmbeddingService
from app.services.llm_service import LocalLLM
from app.services.qdrant_service import QdrantService


class RAGService:
    def __init__(self, settings: Settings, embeddings: EmbeddingService,
                 qdrant: QdrantService, llm: LocalLLM) -> None:
        self._settings = settings
        self._embeddings = embeddings
        self._qdrant = qdrant
        self._llm = llm

    def ingest(self, documents: list[dict]) -> int:
        return self._qdrant.upsert_documents(documents)

    def ingest_upload(self, filename: str, data: bytes) -> tuple[str, int]:
        suffix = Path(filename).suffix.lower()
        if suffix == '.pdf':
            try:
                reader = PdfReader(io.BytesIO(data))
                if reader.is_encrypted:
                    raise ValueError('Encrypted PDFs are not supported.')
                if len(reader.pages) > 100:
                    raise ValueError('PDF limit is 100 pages.')
                text = '\n\n'.join(page.extract_text()
                                   or '' for page in reader.pages)
            except ValueError:
                raise
            except Exception as exc:
                raise ValueError('Could not read PDF content.') from exc
        elif suffix in {'.txt', '.md'}:
            try:
                text = data.decode('utf-8-sig')
            except UnicodeDecodeError as exc:
                raise ValueError('Text files must be UTF-8 encoded.') from exc
        else:
            raise ValueError('Unsupported file type.')

        if not text.strip():
            raise ValueError(
                'Document contains no extractable text. Scanned PDFs need OCR.')

        # A filename is a logical document key for this single-user portfolio demo.
        # Uploading the same filename replaces the previous version.
        document_id = str(uuid.uuid5(uuid.NAMESPACE_URL,
                          'claritylm-upload:' + filename))
        chunks = self._chunk_text(text)
        docs = [
            {
                'id': str(uuid.uuid5(uuid.NAMESPACE_URL, f'{document_id}:{i}')),
                'text': chunk,
                'metadata': {'path': filename, 'document_id': document_id, 'chunk': i},
            }
            for i, chunk in enumerate(chunks)
        ]
        count = self._qdrant.replace_document(document_id, docs)
        return document_id, count

    def ingest_folder(self, path: str) -> tuple[int, int]:
        # Existing local-development feature: only ingest readable source/text files.
        root = Path(path).expanduser()
        if not root.is_dir():
            raise ValueError('Folder not found.')
        docs = []
        skipped = 0
        ignored = {'.git', '.venv', '__pycache__', 'node_modules', 'clarityLM'}
        allowed = {'.py', '.txt', '.md', '.json'}
        for file_path in root.rglob('*'):
            if not file_path.is_file() or any(p in ignored for p in file_path.parts):
                continue
            if file_path.suffix.lower() not in allowed:
                skipped += 1
                continue
            try:
                text = file_path.read_text(encoding='utf-8')
            except (OSError, UnicodeDecodeError):
                skipped += 1
                continue
            chunks = self._chunk_python(text) if file_path.suffix.lower(
            ) == '.py' else self._chunk_text(text)
            for i, chunk in enumerate(chunks):
                digest = hashlib.sha1(chunk.encode('utf-8')).hexdigest()
                docs.append({
                    'id': str(uuid.uuid5(uuid.NAMESPACE_URL, f'{file_path}:{i}:{digest}')),
                    'text': chunk,
                    'metadata': {'path': str(file_path), 'chunk': i},
                })
            if not chunks:
                skipped += 1
        return (self._qdrant.upsert_documents(docs) if docs else 0), skipped

    def answer(self, question: str, use_rag: bool = True) -> tuple[str, list[dict]]:
        sources = []
        if use_rag and self._settings.rag_enabled:
            vector = self._embeddings.embed_texts([question])[0]
            candidates = self._qdrant.search(vector, self._settings.top_k)
            eligible = [x for x in candidates if x['score']
                        >= self._settings.min_score]
            sources = eligible[:self._settings.max_sources]
        context, included = self._build_context(sources)
        prompt = self._build_prompt(question, context, use_rag)
        answer = self._clean_answer(self._llm.generate(prompt))
        return answer, included

    def _build_context(self, sources: list[dict]) -> tuple[str, list[dict]]:
        chunks, included, total = [], [], 0
        for i, source in enumerate(sources, 1):
            path = source.get('metadata', {}).get('path', 'document')
            text = f'[{i}] {path}\n{source["text"]}'
            remaining = self._settings.max_context_chars - total
            if remaining <= 0:
                break
            if len(text) > remaining:
                text = text[:remaining]
            chunks.append(text)
            included.append(source)
            total += len(text)
        return '\n\n'.join(chunks), included

    @staticmethod
    def _build_prompt(question: str, context: str, use_rag: bool) -> str:
        if use_rag:
            instruction = (
                'Use the provided document excerpts to answer the question. '
                'If the excerpts do not contain the answer, say that the document does not provide enough information. '
                'Do not invent sources or facts. Keep the answer concise.\n\n'
                f'Document excerpts:\n{context or "No relevant excerpts found."}\n\n'
                f'Question: {question}'
            )
        else:
            instruction = f'Answer the following question clearly and concisely:\n{question}'
        return f'### Instruction:\n{instruction}\n\n### Response:'

    def _chunk_text(self, text: str) -> list[str]:
        size = max(1, self._settings.chunk_size_chars)
        overlap = min(max(0, self._settings.chunk_overlap_chars), size - 1)
        chunks, pos = [], 0
        while pos < len(text):
            end = min(pos + size, len(text))
            chunk = text[pos:end].strip()
            if chunk:
                chunks.append(chunk)
            if end == len(text):
                break
            pos = end - overlap
        return chunks

    def _chunk_python(self, text: str) -> list[str]:
        # Preserve meaningful top-level blocks for codebase ingestion.
        lines = text.splitlines()
        blocks, preamble, current = [], [], []
        for line in lines:
            stripped = line.lstrip()
            top = len(line) == len(stripped)
            boundary = top and (stripped.startswith(
                'def ') or stripped.startswith('class '))
            if boundary and current:
                blocks.append('\n'.join(current).strip())
                current = []
            if boundary and preamble:
                blocks.insert(0, '\n'.join(preamble).strip())
                preamble = []
            if current or boundary:
                current.append(line)
            else:
                preamble.append(line)
        if current:
            blocks.append('\n'.join(current).strip())
        if preamble:
            blocks.insert(0, '\n'.join(preamble).strip())
        return [c for b in blocks for c in self._chunk_text(b)]

    @staticmethod
    def _clean_answer(answer: str) -> str:
        for marker in ('### Instruction:', '\n### Response:', '\nQuestion:', '\nContext:'):
            if marker in answer:
                answer = answer.split(marker, 1)[0]
        return answer.strip()
