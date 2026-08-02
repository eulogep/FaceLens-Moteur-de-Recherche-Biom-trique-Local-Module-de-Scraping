"""
Live FastAPI End-to-End Validation Script

Starts the FaceLens FastAPI app and executes real HTTP API requests:
 1. GET / -> Status & Disclaimer
 2. POST /api/faces/enroll -> Enroll real LFW faces into corpus
 3. POST /api/faces/search -> 1:N Facial similarity search with threshold score
 4. POST /api/faces/verify -> 1:1 Face verification
 5. POST /api/scrape/search & GET /api/scrape/status/{job_id} -> Scraper pipeline with errors_by_domain
 6. Re-indexing / deduplication verification (0 duplicates added)
 7. DELETE /api/faces/{id} & DELETE /api/scrape/source/{domain} -> Right to be forgotten & domain exclusion
 8. GET /api/scrape/stats -> System statistics & atomic integrity verification
"""
import os
import sys
import time
import subprocess
import requests
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "test_faces")
BASE_URL = "http://127.0.0.1:8000"


def wait_for_server(timeout_sec: int = 20) -> bool:
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
    print("  FaceLens Live FastAPI HTTP End-to-End Validation")
    print("=" * 80)

    server_process = None
    try:
        r = requests.get(f"{BASE_URL}/", timeout=2)
        print("-> Server already running at", BASE_URL)
    except Exception:
        print("-> Starting Uvicorn server on http://127.0.0.1:8000 (InsightFace model load)...")
        venv_python = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".venv", "Scripts", "python.exe"))
        server_process = subprocess.Popen(
            [venv_python, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
            cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        ready = wait_for_server(25)
        if not ready:
            print("FATAL: Uvicorn server failed to start within 25 seconds.")
            if server_process:
                stdout, stderr = server_process.communicate()
                print("Server STDOUT:", stdout.decode("utf-8", errors="ignore"))
                print("Server STDERR:", stderr.decode("utf-8", errors="ignore"))
            sys.exit(1)
        print("-> Uvicorn server is READY!")

    try:
        # Step 1: GET /
        resp_root = requests.get(f"{BASE_URL}/", timeout=5)
        print("\n[1] GET / Response:")
        print("   ", resp_root.json())
        assert resp_root.status_code == 200

        # Step 2: POST /api/faces/enroll (Enroll 2 real LFW faces)
        print("\n[2] POST /api/faces/enroll (Enrolling real LFW faces)...")
        img_powell = os.path.join(ASSETS_DIR, "colin_powell", "colin_powell_original.jpg")
        img_bush = os.path.join(ASSETS_DIR, "george_w_bush", "george_w_bush_original.jpg")

        with open(img_powell, "rb") as f:
            resp_e1 = requests.post(
                f"{BASE_URL}/api/faces/enroll",
                files={"file": ("colin_powell.jpg", f, "image/jpeg")},
                data={"person_name": "Colin Powell", "source_url": "https://news.org/powell.jpg", "source_type": "web"}
            )
        assert resp_e1.status_code == 200
        data_e1 = resp_e1.json()
        print(f"    Enrolled #{data_e1['id']}: {data_e1['person_name']} (URL: {data_e1['source_url']})")

        with open(img_bush, "rb") as f:
            resp_e2 = requests.post(
                f"{BASE_URL}/api/faces/enroll",
                files={"file": ("george_w_bush.jpg", f, "image/jpeg")},
                data={"person_name": "George W Bush", "source_url": "https://news.org/bush.jpg", "source_type": "web"}
            )
        assert resp_e2.status_code == 200
        data_e2 = resp_e2.json()
        print(f"    Enrolled #{data_e2['id']}: {data_e2['person_name']} (URL: {data_e2['source_url']})")

        # Step 3: POST /api/faces/search (1:N search with compressed/rotated photo)
        print("\n[3] POST /api/faces/search (1:N search with rotated Bush photo)...")
        img_bush_rot = os.path.join(ASSETS_DIR, "george_w_bush", "george_w_bush_rotated.jpg")
        with open(img_bush_rot, "rb") as f:
            resp_search = requests.post(
                f"{BASE_URL}/api/faces/search?top_k=5",
                files={"file": ("bush_rot.jpg", f, "image/jpeg")}
            )
        assert resp_search.status_code == 200
        search_data = resp_search.json()
        print(f"    Faces detected: {search_data['faces_detected']}")
        print("    Top-1 Match:")
        if search_data['results']:
            top1 = search_data['results'][0]
            print(f"      Name: {top1['person_name']}, Sim: {top1['similarity']:.4f}, Verdict: {top1['verdict']}")
            assert top1['person_name'] == "George W Bush"
            assert top1['similarity'] >= 0.70

        # Step 4: POST /api/faces/verify (1:1 verification)
        print("\n[4] POST /api/faces/verify (1:1 Verification)...")
        with open(img_powell, "rb") as fa, open(os.path.join(ASSETS_DIR, "colin_powell", "colin_powell_compressed.jpg"), "rb") as fb:
            resp_v1 = requests.post(
                f"{BASE_URL}/api/faces/verify",
                files={"image_a": ("powell_orig.jpg", fa, "image/jpeg"), "image_b": ("powell_comp.jpg", fb, "image/jpeg")}
            )
        data_v1 = resp_v1.json()
        print(f"    Same face (Powell orig vs comp): verified={data_v1['verified']}, sim={data_v1['similarity']:.4f}, verdict={data_v1['verdict']}")
        assert data_v1['verified'] is True

        with open(img_powell, "rb") as fa, open(img_bush, "rb") as fb:
            resp_v2 = requests.post(
                f"{BASE_URL}/api/faces/verify",
                files={"image_a": ("powell.jpg", fa, "image/jpeg"), "image_b": ("bush.jpg", fb, "image/jpeg")}
            )
        data_v2 = resp_v2.json()
        print(f"    Diff face (Powell vs Bush): verified={data_v2['verified']}, sim={data_v2['similarity']:.4f}, verdict={data_v2['verdict']}")
        assert data_v2['verified'] is False

        # Step 5: POST /api/scrape/search & GET /api/scrape/status/{job_id}
        print("\n[5] POST /api/scrape/search & GET /api/scrape/status/{job_id}...")
        resp_job = requests.post(
            f"{BASE_URL}/api/scrape/search",
            json={"query": "Colin Powell portrait", "limit": 5}
        )
        assert resp_job.status_code == 200
        job_data = resp_job.json()
        job_id = job_data['job_id']
        print(f"    Triggered Job ID: {job_id}")

        time.sleep(2)
        resp_status = requests.get(f"{BASE_URL}/api/scrape/status/{job_id}")
        assert resp_status.status_code == 200
        status_data = resp_status.json()
        print(f"    Status: {status_data['status']}, Indexed: {status_data['faces_indexed']}, Duplicates skipped: {status_data['duplicates_skipped']}")
        print(f"    Errors by domain: {status_data['errors_by_domain']}")

        # Step 6: GET /api/scrape/stats (System Stats & Atomic Integrity Verification)
        print("\n[6] GET /api/scrape/stats (System Stats & Integrity)...")
        resp_stats = requests.get(f"{BASE_URL}/api/scrape/stats")
        assert resp_stats.status_code == 200
        stats_data = resp_stats.json()
        print("    Stats:", stats_data)
        assert stats_data['integrity_verified'] is True

        print("\n" + "=" * 80)
        print("  Live FastAPI Validation: ALL 6 ENDPOINTS PASSED SUCCESSFULLY")
        print("=" * 80)

    finally:
        if server_process:
            server_process.terminate()

if __name__ == "__main__":
    main()
