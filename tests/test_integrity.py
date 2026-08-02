import os
import pytest
import numpy as np
from core.db import DatabaseManager
from core.vector_index import VectorIndexManager

@pytest.fixture
def clean_db_and_index(tmp_path):
    db_path = str(tmp_path / "test_facelens.db")
    idx_path = str(tmp_path / "test_facelens.index")
    
    db = DatabaseManager(db_path)
    index = VectorIndexManager(dimension=512, index_path=idx_path)
    index.reset()
    
    return db, index

def test_atomic_enrollment_and_deletion(clean_db_and_index):
    db, index = clean_db_and_index

    # 1. Initial State Check
    assert db.count_faces() == 0
    assert index.ntotal == 0
    assert db.verify_integrity(index) is True

    # 2. Atomic Enroll 5 faces
    for i in range(1, 6):
        # Normalized 512-d float32 vector
        vec = np.random.randn(512).astype(np.float32)
        vec /= np.linalg.norm(vec)

        enrolled = db.enroll_face_atomic(
            index_manager=index,
            vector=vec,
            image_path=f"/fake/path/face_{i}.jpg",
            person_name=f"Person_{i}",
            source_type="test"
        )
        assert enrolled["id"] == i
        assert db.count_faces() == i
        assert index.ntotal == i
        assert db.verify_integrity(index) is True

    # 3. Search Vector
    query_vec = np.random.randn(512).astype(np.float32)
    query_vec /= np.linalg.norm(query_vec)
    search_res = index.search(query_vec, top_k=3)
    assert len(search_res) <= 3

    # 4. Atomic Delete face #3
    deleted = db.delete_face_atomic(index, face_id=3)
    assert deleted is True
    assert db.count_faces() == 4
    assert index.ntotal == 4
    assert db.verify_integrity(index) is True

    # Check that ID #3 is gone from SQLite and FAISS
    assert db.get_face(3) is None
    rem_search = index.search(query_vec, top_k=10)
    found_ids = [res[0] for res in rem_search]
    assert 3 not in found_ids

    # 5. Domain exclusion atomic deletion
    # Add domain faces
    vec_dom = np.random.randn(512).astype(np.float32)
    vec_dom /= np.linalg.norm(vec_dom)
    db.enroll_face_atomic(
        index_manager=index,
        vector=vec_dom,
        image_path="/fake/path/spam.jpg",
        source_url="https://spammy-site.com/profile1.jpg",
        person_name="Spammer",
        source_type="web"
    )
    assert db.count_faces() == 5
    assert db.verify_integrity(index) is True

    deleted_count = db.delete_domain_atomic(index, domain="spammy-site.com")
    assert deleted_count == 1
    assert db.count_faces() == 4
    assert index.ntotal == 4
    assert db.verify_integrity(index) is True

    # 6. Manual SQLite deletion must be detected as an integrity breach
    with db.get_connection() as conn:
        conn.execute("DELETE FROM faces WHERE id = ?", (1,))
        conn.commit()

    with pytest.raises(AssertionError) as exc_info:
        db.verify_integrity(index)

    message = str(exc_info.value)
    assert "missing_in_faiss=[]" in message
    assert "missing_in_sqlite=[1]" in message
