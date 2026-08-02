"""
Part B3 Test Script — Real URL Scraping & Facial Search
"""
import os
import sys
import time
import subprocess
import requests
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.config import settings
from core.db import DatabaseManager

BASE_URL = "http://127.0.0.1:8000"


def wait_for_server(timeout_sec: int = 25) -> bool:
    start_time = time.time()
    while time.time() - start_time < timeout_sec:
        try:
            r = requests.get(f"{BASE_URL}/", timeout=2)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def main():
    print("=" * 80)
    print("  FaceLens B3 — Real URL Scraping & Facial Search Validation")
    print("=" * 80)

    server_process = None
    try:
        r = requests.get(f"{BASE_URL}/", timeout=2)
        print("-> Server already running at", BASE_URL)
    except Exception:
        print("-> Starting Uvicorn server on http://127.0.0.1:8000...")
        venv_python = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".venv", "Scripts", "python.exe"))
        server_process = subprocess.Popen(
            [venv_python, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
            cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        ready = wait_for_server(25)
        if not ready:
            print("FATAL: Uvicorn server failed to start.")
            sys.exit(1)
        print("-> Uvicorn server is READY!")

    try:
        target_url = "https://fr.wikipedia.org/wiki/Emmanuel_Macron"

        # Step 7: POST /api/scrape/url
        print(f"\n[7] POST /api/scrape/url (URL: {target_url})...")
        resp_url = requests.post(
            f"{BASE_URL}/api/scrape/url",
            json={"url": target_url, "max_images": 10, "source_type": "presse"}
        )
        assert resp_url.status_code == 200, f"Error {resp_url.status_code}: {resp_url.text}"
        job_data = resp_url.json()
        job_id = job_data["job_id"]
        print(f"    Triggered Job ID: {job_id}")

        print("    Polling job status...")
        status_data = {}
        for attempt in range(40):
            time.sleep(2)
            resp_st = requests.get(f"{BASE_URL}/api/scrape/status/{job_id}")
            status_data = resp_st.json()
            st = status_data.get("status")
            print(f"      [{attempt*2}s] status={st}, indexed={status_data.get('faces_indexed')}, skipped={status_data.get('duplicates_skipped')}")
            if st in ("completed", "failed", "partial"):
                break

        print("\n    URL Scrape Job Final Status:")
        print(f"      Status:            {status_data.get('status')}")
        print(f"      Faces Indexed:     {status_data.get('faces_indexed')}")
        print(f"      Duplicates Skipped:{status_data.get('duplicates_skipped')}")

        # Step 8: Perform facial search with a scraped face
        print("\n[8] POST /api/faces/search (Facial similarity search)...")
        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM faces ORDER BY id DESC LIMIT 10")
            scraped_faces = [dict(row) for row in cursor.fetchall()]

        print(f"    Total faces retrieved from database: {len(scraped_faces)}")

        if scraped_faces:
            test_face = scraped_faces[0]
            test_img_path = test_face["image_path"]
            print(f"    Searching with indexed face #{test_face['id']} ({test_img_path})...")

            with open(test_img_path, "rb") as f:
                resp_search = requests.post(
                    f"{BASE_URL}/api/faces/search?top_k=5",
                    files={"file": ("query.jpg", f, "image/jpeg")}
                )
            assert resp_search.status_code == 200
            search_res = resp_search.json()
            print(f"    Faces detected: {search_res['faces_detected']}")
            if search_res['results']:
                top1 = search_res['results'][0]
                print(f"    Top-1 Match:")
                print(f"      Face ID:    #{top1['id']}")
                print(f"      Similarity:  {top1['similarity']:.4f}")
                print(f"      Source URL:  {top1['source_url']}")
                print(f"      Verdict:     {top1['verdict']}")
                assert top1['similarity'] >= 0.70

        print("\n" + "=" * 80)
        print("  B3 Real URL Scraping Test Completed Successfully!")
        print("=" * 80)

    finally:
        if server_process:
            server_process.terminate()

if __name__ == "__main__":
    main()
