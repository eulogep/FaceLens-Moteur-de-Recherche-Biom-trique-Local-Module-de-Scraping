import pytest
import asyncio
import numpy as np
from core.db import DatabaseManager
from core.vector_index import VectorIndexManager
from spider.job_manager import ScrapeJobManager

@pytest.fixture
def spider_setup(tmp_path):
    db_path = str(tmp_path / "spider_test.db")
    idx_path = str(tmp_path / "spider_test.index")
    
    db = DatabaseManager(db_path)
    index = VectorIndexManager(dimension=512, index_path=idx_path)
    index.reset()

    return db, index

def test_deduplication_and_dryrun(spider_setup):
    db, index = spider_setup
    job_mgr = ScrapeJobManager(db, index)

    # 1. Enroll a initial vector
    vec = np.random.randn(512).astype(np.float32)
    vec /= np.linalg.norm(vec)

    db.enroll_face_atomic(
        index_manager=index,
        vector=vec,
        image_path="/scraped/face1.jpg",
        source_url="https://example.com/face1.jpg",
        person_name="Example Person",
        source_type="web"
    )

    assert db.count_faces() == 1
    assert index.ntotal == 1

    # 2. Test Deduplication Check: vector with cosine similarity > 0.95 (e.g., identical or near-identical vector)
    near_identical = vec + (np.random.randn(512) * 0.001)
    near_identical /= np.linalg.norm(near_identical)

    top_matches = index.search(near_identical, top_k=1)
    assert top_matches[0][1] >= 0.95

    # 3. Dry-run simulation: job status tracking
    asyncio.run(job_mgr.execute_url_job(
        job_id="test_job_1",
        url="https://invalid-non-existent-domain-12345.com/page",
        max_images=10,
        dry_run=True
    ))

    job_status = db.get_scrape_job("test_job_1")
    assert job_status is not None
    assert job_status["status"] == "failed"
    assert "errors_by_domain" in job_status
    assert "invalid-non-existent-domain-12345.com" in job_status["errors_by_domain"]

    # Verify no dry-run data was written
    assert db.count_faces() == 1
    assert index.ntotal == 1
    assert db.verify_integrity(index) is True
