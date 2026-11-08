import uuid

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, PointStruct, VectorParams

from app.core.config import Settings
from app.services.embeddings_service import EmbeddingService


class QdrantService:
    def __init__(self, settings: Settings, embeddings: EmbeddingService) -> None:
        self._settings = settings # configurations  
        self._embeddings = embeddings  # embeddings
        self._client = QdrantClient(  # Qdrant database connection 
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
            timeout=settings.qdrant_timeout,
        )
        self._ensure_collection()

    def _ensure_collection(self) -> None: # create new if not exist , otherwise use that 
        collection = self._settings.qdrant_collection
        if self._client.collection_exists(collection):
            return
        vector_size = self._embeddings.dimension()
        self._client.create_collection(
            collection_name=collection,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )

    def upsert_documents(self, documents: list[dict]) -> int:  # turn text into embeddings
        texts = [doc['text'] for doc in documents] # First you extract the text field from every document.
        vectors = self._embeddings.embed_texts(texts) # Next, embed_texts(texts) generates vectors.
        points = []
        for doc, vector in zip(documents, vectors): # Loop, combines the original documents with their corresponding embeddings. zip() pairs items by position.
            doc_id = doc.get('id') or str(uuid.uuid4()) # ID and vector
            payload = { 
                'text': doc['text'], # text (what is python)
                'metadata': doc.get('metadata') or {}, # metadata (python.txt)
            }
            points.append(PointStruct(id=doc_id, vector=vector, payload=payload))
        self._client.upsert(collection_name=self._settings.qdrant_collection, points=points)
        return len(points)

    def search(self, query_vector: list[float], limit: int) -> list[dict]: # find responses The method takes an already-generated query embedding and the maximum number of results to retrieve.
        if hasattr(self._client, 'search'):
            results = self._client.search(
                collection_name=self._settings.qdrant_collection,
                query_vector=query_vector,
                limit=limit,
            )
        else:
            results = self._client.query_points(
                collection_name=self._settings.qdrant_collection,
                query=query_vector,
                limit=limit,
            ).points
        items = []
        for result in results:
            payload = result.payload or {}
            items.append(
                {
                    'id': str(result.id),
                    'score': float(result.score),
                    'text': payload.get('text', ''),
                    'metadata': payload.get('metadata') or {},
                }
            )
        return items

# _ensure_collection() → Check if the database collection exists; if not, create it.
# upsert_documents() → Save knowledge into the database.
# search() → Find relevant knowledge from the database.