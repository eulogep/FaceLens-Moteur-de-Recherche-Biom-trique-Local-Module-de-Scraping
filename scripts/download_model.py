"""
Download and verify InsightFace buffalo_l model.
Tries the official insightface API first, then falls back to a direct URL download.
"""
import os
import sys
import zipfile
import urllib.request

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

MODEL_NAME = "buffalo_l"
MODEL_DIR = os.path.expanduser("~/.insightface/models")
TARGET_DIR = os.path.join(MODEL_DIR, MODEL_NAME)
ZIP_PATH = os.path.join(MODEL_DIR, f"{MODEL_NAME}.zip")
DOWNLOAD_URL = "https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip"

EXPECTED_FILES = [
    "1k3d68.onnx",
    "2d106det.onnx",
    "det_10g.onnx",
    "genderage.onnx",
    "w600k_r50.onnx",
]


def model_ready() -> bool:
    """Check if all expected ONNX files are present."""
    if not os.path.isdir(TARGET_DIR):
        return False
    for f in EXPECTED_FILES:
        if not os.path.isfile(os.path.join(TARGET_DIR, f)):
            return False
    return True


def download_with_urllib(url: str, dest: str) -> bool:
    """Download a file using urllib with a proper User-Agent (GitHub blocks default python UA)."""
    print(f"Downloading {url} -> {dest}")
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        with urllib.request.urlopen(req, timeout=120) as resp, open(dest, "wb") as out:
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            chunk_size = 1024 * 256
            while True:
                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                out.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = downloaded * 100 // total
                    print(f"\r  {downloaded // (1024*1024)} MB / {total // (1024*1024)} MB  ({pct}%)", end="", flush=True)
            print()
        return True
    except Exception as e:
        print(f"Download failed: {e}")
        return False


def main():
    os.makedirs(MODEL_DIR, exist_ok=True)

    if model_ready():
        print(f"Model already present at {TARGET_DIR}")
        for f in os.listdir(TARGET_DIR):
            sz = os.path.getsize(os.path.join(TARGET_DIR, f))
            print(f"  {f}: {sz / (1024*1024):.1f} MB")
        return True

    # Attempt 1: Try InsightFace built-in download via FaceAnalysis init
    print("Attempt 1: Using insightface.app.FaceAnalysis to download model...")
    try:
        from insightface.app import FaceAnalysis
        app = FaceAnalysis(
            name=MODEL_NAME,
            root=os.path.expanduser("~/.insightface"),
            providers=["CPUExecutionProvider"],
        )
        app.prepare(ctx_id=-1, det_size=(640, 640))
        print("SUCCESS: Model loaded via insightface API.")
        return True
    except Exception as e:
        print(f"InsightFace auto-download failed: {e}")

    # Attempt 2: Direct urllib download with proper User-Agent
    print(f"\nAttempt 2: Direct download from {DOWNLOAD_URL}")
    if os.path.exists(ZIP_PATH):
        os.remove(ZIP_PATH)

    ok = download_with_urllib(DOWNLOAD_URL, ZIP_PATH)
    if not ok:
        print("FAILED: Could not download buffalo_l.zip")
        return False

    # Extract zip
    print(f"Extracting {ZIP_PATH} -> {MODEL_DIR}")
    with zipfile.ZipFile(ZIP_PATH, "r") as zf:
        zf.extractall(MODEL_DIR)

    if model_ready():
        print(f"SUCCESS: Model extracted to {TARGET_DIR}")
        for f in os.listdir(TARGET_DIR):
            sz = os.path.getsize(os.path.join(TARGET_DIR, f))
            print(f"  {f}: {sz / (1024*1024):.1f} MB")
        os.remove(ZIP_PATH)
        return True
    else:
        print(f"FAILED: Extraction incomplete. Contents of {MODEL_DIR}:")
        for root, dirs, files in os.walk(MODEL_DIR):
            for f in files:
                print(f"  {os.path.join(root, f)}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
