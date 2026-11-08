from typing import Iterable

from sentence_transformers import SentenceTransformer


class EmbeddingService:
    # Initialize the embedding model 'sentence-transformers/all-MiniLM-L6-v2'
    def __init__(self, model_name: str) -> None:
        self._model = SentenceTransformer(model_name)

    def dimension(self) -> int:
        # Qdrant needs this dimension when creating its collection because every vector in that collection must have the expected length.
        return self._model.get_embedding_dimension()

    # means the method accepts an iterable collection of strings, such as a list or generator.
    def embed_texts(self, texts: Iterable[str]) -> list[list[float]]:
        embeddings = self._model.encode(  # generates an embedding for every text.
            # turns that iterable into a list so it can be passed to the model.
            list(texts),
            # scales each nonzero vector to approximately unit length (magnitude 1). This works well with cosine similarity.
            normalize_embeddings=True,
            # disables the progress bar during encoding, which is generally appropriate for backend operations.
            show_progress_bar=False,
        )
        # This is a list comprehension. It converts each NumPy embedding array into a regular Python list of floats.
        return [embedding.tolist() for embedding in embeddings]
