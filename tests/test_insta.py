from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from spider.insta.client import InstagramPublicClient
from spider.insta.service import InstagramIndexer


class FakeDB:
    def __init__(self) -> None:
        self.jobs = {}
        self.enrolled = []

    def create_scrape_job(self, job_id, target_url):
        self.jobs[job_id] = {"target_url": target_url, "status": "pending"}

    def update_scrape_job(self, job_id, status, **values):
        self.jobs[job_id].update(status=status, **values)

    def enroll_face_atomic(self, **values):
        self.enrolled.append(values)
        return {"id": len(self.enrolled)}


class FakeIndex:
    def __init__(self, similarity=0.0) -> None:
        self.similarity = similarity

    def search(self, _vector, top_k=1):
        return [(1, self.similarity)] if self.similarity else []


class FakeEngine:
    def extract_faces(self, _image):
        return [{"embedding": np.ones(512, dtype=np.float32), "phash": "abc"}]


class FakeHttp:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def get(self, _url):
        return SimpleNamespace(content=b"image", raise_for_status=lambda: None)


class FakePublicClient:
    def __init__(self, private=False) -> None:
        self.user = SimpleNamespace(
            username="example",
            pk="42",
            full_name="Example Person",
            biography="Bio",
            is_private=private,
            is_verified=True,
            profile_pic_url_hd="https://cdn.example/profile.jpg",
        )
        self.media_calls = 0

    def user_info_by_username_public(self, _username):
        return self.user

    def user_medias_public(self, _user_id, _amount):
        self.media_calls += 1
        return []


def make_service(db, index, client):
    return InstagramIndexer(
        db,
        index,
        client=client,
        engine_factory=lambda: FakeEngine(),
        http_client_factory=FakeHttp,
        sleep_fn=lambda _seconds: None,
        delay_range=(0, 0),
    )


def test_adapter_uses_only_explicit_public_gql_methods():
    raw = SimpleNamespace(
        user_info_by_username_gql=lambda username: ("user", username),
        user_medias_gql=lambda user_id, amount, sleep: (user_id, amount, sleep),
    )
    client = InstagramPublicClient(raw)
    assert client.user_info_by_username_public("alice") == ("user", "alice")
    assert client.user_medias_public("42", 10) == ("42", 10, 0)


def test_profile_indexes_metadata(tmp_path, monkeypatch):
    monkeypatch.setattr("spider.insta.service.settings.STORAGE_DIR", str(tmp_path))
    db = FakeDB()
    service = make_service(db, FakeIndex(), FakePublicClient())
    service.execute_profile_job("job-profile", "@Example")
    assert db.jobs["job-profile"]["status"] == "completed"
    assert db.jobs["job-profile"]["faces_indexed"] == 1
    assert db.enrolled[0]["source_type"] == "instagram"
    assert '"username":"example"' in db.enrolled[0]["tags"]
    assert '"is_verified":true' in db.enrolled[0]["tags"]


def test_profile_rescrape_uses_existing_dedup_threshold(tmp_path, monkeypatch):
    monkeypatch.setattr("spider.insta.service.settings.STORAGE_DIR", str(tmp_path))
    db = FakeDB()
    service = make_service(db, FakeIndex(similarity=0.95), FakePublicClient())
    service.execute_profile_job("job-dedup", "example")
    assert db.jobs["job-dedup"]["duplicates_skipped"] == 1
    assert db.jobs["job-dedup"]["faces_indexed"] == 0
    assert db.enrolled == []


def test_private_profile_media_job_is_clean_and_does_not_fetch_media():
    db = FakeDB()
    client = FakePublicClient(private=True)
    service = make_service(db, FakeIndex(), client)
    service.execute_medias_job("job-private", "example", 10)
    assert db.jobs["job-private"]["status"] == "partial"
    assert "Compte privé" in db.jobs["job-private"]["errors_by_domain"]["instagram.com"]
    assert client.media_calls == 0
