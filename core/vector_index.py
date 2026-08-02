import os
import faiss
import numpy as np
from typing import List, Tuple
from core.config import settings

class VectorIndexManager:
    """
    FAISS Index Manager using faiss.IndexIDMap2(faiss.IndexFlatIP(512)).
    
    Why IndexIDMap2:
    A bare faiss.IndexFlatIP relies on implicit sequential positions [0, 1, ..., N-1].
    If a vector is deleted from a naked IndexFlatIP, subsequent vector positions shift,
    destroying the 1:1 mapping with SQLite primary keys.
    IndexIDMap2 maps custom 64-bit integer IDs (SQLite primary keys) directly to vectors
    and allows explicit deletion via index.remove_ids(ids) without index drift.
    """
    def __init__(self, dimension: int = 512, index_path: str = settings.INDEX_PATH):
        self.dimension = dimension
        self.index_path = index_path
        self.sub_index = faiss.IndexFlatIP(self.dimension)
        self.index = faiss.IndexIDMap2(self.sub_index)
        
        if os.path.exists(self.index_path):
            self.load()

    def add_vector(self, vector: np.ndarray, vector_id: int) -> None:
        """
        Add a single 512-d L2 normalized float32 vector with a specific SQLite ID.
        """
        vector = np.ascontiguousarray(vector.reshape(1, self.dimension).astype(np.float32))
        ids = np.array([vector_id], dtype=np.int64)
        self.index.add_with_ids(vector, ids)

    def add_vectors(self, vectors: np.ndarray, ids: List[int]) -> None:
        """
        Add multiple 512-d L2 normalized float32 vectors with specific SQLite IDs.
        """
        vectors = np.ascontiguousarray(vectors.astype(np.float32))
        ids_arr = np.array(ids, dtype=np.int64)
        self.index.add_with_ids(vectors, ids_arr)

    def search(self, query_vector: np.ndarray, top_k: int = 10) -> List[Tuple[int, float]]:
        """
        Search top_k similar vectors for a 512-d L2 normalized vector.
        Returns list of tuples: (vector_id, cosine_similarity_score).
        """
        if self.ntotal == 0:
            return []
        
        query_vector = np.ascontiguousarray(query_vector.reshape(1, self.dimension).astype(np.float32))
        top_k = min(top_k, self.ntotal)
        scores, ids = self.index.search(query_vector, top_k)
        
        results = []
        for v_id, score in zip(ids[0], scores[0]):
            if v_id != -1:
                results.append((int(v_id), float(score)))
        return results

    def remove_ids(self, ids: List[int]) -> int:
        """
        Remove vectors by SQLite ID. Returns count of removed items.
        """
        if not ids:
            return 0
        ids_arr = np.array(ids, dtype=np.int64)
        selector = faiss.IDSelectorBatch(ids_arr)
        removed_count = self.index.remove_ids(selector)
        return removed_count

    @property
    def ntotal(self) -> int:
        return self.index.ntotal

    def get_ids(self) -> List[int]:
        """Return the explicit SQLite IDs stored in the FAISS ID map."""
        return [int(vector_id) for vector_id in faiss.vector_to_array(self.index.id_map)]

    def save(self, path: str = None) -> None:
        save_path = path or self.index_path
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        faiss.write_index(self.index, save_path)

    def load(self, path: str = None) -> None:
        load_path = path or self.index_path
        if os.path.exists(load_path):
            self.index = faiss.read_index(load_path)

    def reset(self) -> None:
        self.sub_index = faiss.IndexFlatIP(self.dimension)
        self.index = faiss.IndexIDMap2(self.sub_index)
        if os.path.exists(self.index_path):
            os.remove(self.index_path)
