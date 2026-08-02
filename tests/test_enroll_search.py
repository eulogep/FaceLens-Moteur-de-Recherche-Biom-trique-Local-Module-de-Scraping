import pytest
import numpy as np
from core.db import DatabaseManager
from core.vector_index import VectorIndexManager

@pytest.fixture
def test_corpus(tmp_path):
    db_path = str(tmp_path / "corpus_test.db")
    idx_path = str(tmp_path / "corpus_test.index")
    
    db = DatabaseManager(db_path)
    index = VectorIndexManager(dimension=512, index_path=idx_path)
    index.reset()

    # Generate 55 distinct normalized vectors
    vectors = []
    for i in range(55):
        vec = np.random.randn(512).astype(np.float32)
        vec /= np.linalg.norm(vec)
        vectors.append(vec)
        db.enroll_face_atomic(
            index_manager=index,
            vector=vec,
            image_path=f"/corpus/img_{i}.jpg",
            person_name=f"Subject #{i}",
            source_type="corpus_test"
        )
    return db, index, vectors

def test_search_top1_accuracy_50plus(test_corpus):
    db, index, vectors = test_corpus
    assert db.count_faces() == 55
    assert index.ntotal == 55
    assert db.verify_integrity(index) is True

    # Query using target vector #23 (exact match similarity should be ~1.0)
    query_target = vectors[23]
    top_results = index.search(query_target, top_k=5)

    assert len(top_results) == 5
    top_id, top_sim = top_results[0]
    
    # Top 1 result must be vector ID #24 (1-indexed SQLite autoincrement ID)
    assert top_id == 24
    assert abs(top_sim - 1.0) < 1e-4

    face_record = db.get_face(top_id)
    assert face_record["person_name"] == "Subject #23"
