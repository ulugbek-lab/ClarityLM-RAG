import uuid

from qdrant_client import QdrantClient, models

from app.core.config import Settings
from app.services.embeddings_service import EmbeddingService


class QdrantService:
    def __init__(self, settings: Settings, embeddings: EmbeddingService) -> None:
        self._settings = settings
        self._embeddings = embeddings
        self._client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
            timeout=settings.qdrant_timeout,
        )
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        collection = self._settings.qdrant_collection
        if not self._client.collection_exists(collection):
            self._client.create_collection(
                collection_name=collection,
                vectors_config=models.VectorParams(
                    size=self._embeddings.dimension(), distance=models.Distance.COSINE
                ),
            )
        # Enables efficient and reliable deletion of old chunks by document_id.
        self._client.create_payload_index(
            collection_name=collection,
            field_name='metadata.document_id',
            field_schema=models.PayloadSchemaType.KEYWORD,
            wait=True,
        ) if not self._has_document_index(collection) else None

    def _has_document_index(self, collection: str) -> bool:
        info = self._client.get_collection(collection)
        indexes = (info.payload_schema or {})
        return 'metadata.document_id' in indexes

    def upsert_documents(self, documents: list[dict]) -> int:
        if not documents:
            return 0
        vectors = self._embeddings.embed_texts(
            [doc['text'] for doc in documents])
        points = [
            models.PointStruct(
                id=doc.get('id') or str(uuid.uuid4()),
                vector=vector,
                payload={'text': doc['text'],
                         'metadata': doc.get('metadata') or {}},
            )
            for doc, vector in zip(documents, vectors)
        ]
        self._client.upsert(
            collection_name=self._settings.qdrant_collection, points=points, wait=True)
        return len(points)

    def replace_document(self, document_id: str, documents: list[dict]) -> int:
        # Embeddings computed first so a failed encoder won't delete the prior document.
        vectors = self._embeddings.embed_texts(
            [doc['text'] for doc in documents])
        points = [
            models.PointStruct(
                id=doc['id'],
                vector=vector,
                payload={'text': doc['text'], 'metadata': doc['metadata']},
            )
            for doc, vector in zip(documents, vectors)
        ]
        self._client.delete(
            collection_name=self._settings.qdrant_collection,
            points_selector=models.FilterSelector(
                filter=models.Filter(must=[
                    models.FieldCondition(
                        key='metadata.document_id', match=models.MatchValue(value=document_id)
                    )
                ])
            ),
            wait=True,
        )
        if points:
            self._client.upsert(
                collection_name=self._settings.qdrant_collection, points=points, wait=True)
        return len(points)

    def search(self, query_vector: list[float], limit: int) -> list[dict]:
        results = self._client.query_points(
            collection_name=self._settings.qdrant_collection,
            query=query_vector,
            limit=limit,
            with_payload=True,
        ).points
        return [
            {
                'id': str(point.id),
                'score': float(point.score),
                'text': (point.payload or {}).get('text', ''),
                'metadata': (point.payload or {}).get('metadata') or {},
            }
            for point in results
        ]
