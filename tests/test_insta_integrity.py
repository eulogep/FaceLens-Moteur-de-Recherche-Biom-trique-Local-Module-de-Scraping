import numpy as np

from core.db import DatabaseManager
from core.vector_index import VectorIndexManager


def test_instagram_face_deletion_keeps_sqlite_faiss_integrity(tmp_path):
    db = DatabaseManager(str(tmp_path / "insta.db"))
    index = VectorIndexManager(
        dimension=512,
        index_path=str(tmp_path / "insta.index"),
    )
    vector = np.ones(512, dtype=np.float32)
    vector /= np.linalg.norm(vector)

    face = db.enroll_face_atomic(
        index_manager=index,
        vector=vector,
        image_path=str(tmp_path / "instagram.jpg"),
        source_url="https://www.instagram.com/example/",
        person_name="Example",
        source_type="instagram",
        tags='{"instagram":{"username":"example"}}',
        image_hash="abc",
    )

    assert db.delete_face_atomic(index, face["id"]) is True
    assert db.count_faces() == 0
    assert index.ntotal == 0
    assert db.verify_integrity(index) is True
