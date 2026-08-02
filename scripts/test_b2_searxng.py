"""
Part B2 Test Script — Real SearXNG Spider & Deduplication
"""
import os
import sys
import time
import subprocess
import requests
import json

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
    print("  FaceLens B2 — Real SearXNG Spider & Deduplication Validation")
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
        query = "Emmanuel Macron portrait officiel"

        # Step 5: Trigger real SearXNG scrape job
        print(f"\n[5] POST /api/scrape/search (Query: '{query}')...")
        resp_scrape = requests.post(
            f"{BASE_URL}/api/scrape/search",
            json={"query": query, "engine": "searxng", "limit": 5}
        )
        assert resp_scrape.status_code == 200, f"Error: {resp_scrape.status_code} - {resp_scrape.text}"
        job_data = resp_scrape.json()
        job_id = job_data["job_id"]
        print(f"    Triggered Job ID: {job_id}")

        # Poll job status until completed/failed/partial
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

        print("\n    Job Final Status:")
        print(f"      Status:            {status_data.get('status')}")
        print(f"      Faces Indexed:     {status_data.get('faces_indexed')}")
        print(f"      Duplicates Skipped:{status_data.get('duplicates_skipped')}")
        print(f"      Errors by Domain:  {status_data.get('errors_by_domain')}")

        # Step 6: Deduplication — Re-run the EXACT same request
        print(f"\n[6] Re-running EXACT same query for Deduplication test...")
        resp_scrape2 = requests.post(
            f"{BASE_URL}/api/scrape/search",
            json={"query": query, "engine": "searxng", "limit": 5}
        )
        job_id2 = resp_scrape2.json()["job_id"]
        print(f"    Triggered Job ID #2: {job_id2}")

        print("    Polling job #2 status...")
        status_data2 = {}
        for attempt in range(40):
            time.sleep(2)
            resp_st2 = requests.get(f"{BASE_URL}/api/scrape/status/{job_id2}")
            status_data2 = resp_st2.json()
            st2 = status_data2.get("status")
            print(f"      [{attempt*2}s] status={st2}, indexed={status_data2.get('faces_indexed')}, skipped={status_data2.get('duplicates_skipped')}")
            if st2 in ("completed", "failed", "partial"):
                break

        print("\n    Job #2 Final Status (Deduplication Result):")
        print(f"      Status:            {status_data2.get('status')}")
        print(f"      Faces Indexed:     {status_data2.get('faces_indexed')} (Expect 0)")
        print(f"      Duplicates Skipped:{status_data2.get('duplicates_skipped')} (Expect > 0)")

        # Verify system stats
        resp_stats = requests.get(f"{BASE_URL}/api/scrape/stats")
        print("\n    System Stats:", resp_stats.json())

        print("\n" + "=" * 80)
        print("  B2 Real SearXNG Spider Test Completed!")
        print("=" * 80)

    finally:
        if server_process:
            server_process.terminate()

if __name__ == "__main__":
    main()
