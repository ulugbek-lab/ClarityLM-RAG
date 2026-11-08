from typing import Iterable

from sentence_transformers import SentenceTransformer


class EmbeddingService:
    def __init__(self, model_name: str) -> None: # Initialize the embedding model 'sentence-transformers/all-MiniLM-L6-v2'
        self._model = SentenceTransformer(model_name) 

    def dimension(self) -> int:
        return self._model.get_embedding_dimension() # Qdrant needs this dimension when creating its collection because every vector in that collection must have the expected length.

    def embed_texts(self, texts: Iterable[str]) -> list[list[float]]: # means the method accepts an iterable collection of strings, such as a list or generator. 
        embeddings = self._model.encode( # generates an embedding for every text.
            list(texts), # turns that iterable into a list so it can be passed to the model.
            normalize_embeddings=True, # scales each nonzero vector to approximately unit length (magnitude 1). This works well with cosine similarity.
            show_progress_bar=False, # disables the progress bar during encoding, which is generally appropriate for backend operations.
        )
        return [embedding.tolist() for embedding in embeddings] # This is a list comprehension. It converts each NumPy embedding array into a regular Python list of floats.
