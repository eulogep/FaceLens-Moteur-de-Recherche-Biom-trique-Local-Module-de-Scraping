"""
Generate REAL color test face images from LFW raw JPEG cache.

TRANSPARENCY NOTE:
==================
Source:    LFW (Labeled Faces in the Wild) — standard academic face recognition benchmark
URL:       http://vis-www.cs.umass.edu/lfw/
License:   Free for research and non-commercial use
Citation:  Gary B. Huang, Manu Ramesh, Tamara Berg, Erik Learned-Miller.
           "Labeled Faces in the Wild: A Database for Studying Face Recognition
           in Unconstrained Environments." University of Massachusetts, Amherst, 2007.

Uses the RAW COLOR JPEG files (250x250) from sklearn's LFW cache directory,
NOT the grayscale-compressed numpy arrays returned by fetch_lfw_people.

For each of the 10 selected identities, we create 4 variants:
  - original:    as-is from LFW (250x250 color JPEG)
  - cropped:     tight center crop (removing ~30% border)
  - compressed:  JPEG quality=50
  - rotated:     15° rotation + brightness/contrast shift
"""
import os
import sys
import cv2
import shutil

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sklearn.datasets import get_data_home

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "test_faces")

# 10 public figures with many photos in LFW
TARGET_PEOPLE = [
    "Alejandro_Toledo",
    "Arnold_Schwarzenegger",
    "George_W_Bush",
    "Colin_Powell",
    "Tony_Blair",
    "Donald_Rumsfeld",
    "Gerhard_Schroeder",
    "Hugo_Chavez",
    "Jean_Chretien",
    "Junichiro_Koizumi",
]


def create_variants(orig_path: str, name: str, output_dir: str):
    """Create 4 variants of an image and save them."""
    os.makedirs(output_dir, exist_ok=True)

    img = cv2.imread(orig_path)
    if img is None:
        print(f"    ERROR: Cannot read {orig_path}")
        return False

    H, W = img.shape[:2]

    # 1. Original (copy as-is)
    cv2.imwrite(os.path.join(output_dir, f"{name}_original.jpg"), img,
                [cv2.IMWRITE_JPEG_QUALITY, 95])

    # 2. Cropped (center ~70%)
    mx = int(W * 0.15)
    my = int(H * 0.15)
    cropped = img[my:H - my, mx:W - mx].copy()
    cv2.imwrite(os.path.join(output_dir, f"{name}_cropped.jpg"), cropped,
                [cv2.IMWRITE_JPEG_QUALITY, 95])

    # 3. Compressed (JPEG quality 50)
    cv2.imwrite(os.path.join(output_dir, f"{name}_compressed.jpg"), img,
                [cv2.IMWRITE_JPEG_QUALITY, 50])

    # 4. Rotated 15° + brightness shift
    cx, cy = W // 2, H // 2
    M = cv2.getRotationMatrix2D((cx, cy), 15, 1.0)
    rotated = cv2.warpAffine(img, M, (W, H), borderMode=cv2.BORDER_REFLECT)
    rotated = cv2.convertScaleAbs(rotated, alpha=1.15, beta=20)
    cv2.imwrite(os.path.join(output_dir, f"{name}_rotated.jpg"), rotated,
                [cv2.IMWRITE_JPEG_QUALITY, 90])

    return True


def main():
    lfw_home = os.path.join(get_data_home(), "lfw_home", "lfw_funneled")
    if not os.path.isdir(lfw_home):
        print(f"FATAL: LFW funneled directory not found at {lfw_home}")
        print("Run 'from sklearn.datasets import fetch_lfw_people; fetch_lfw_people()' first.")
        sys.exit(1)

    print(f"LFW funneled directory: {lfw_home}")

    # Clean previous test data
    if os.path.exists(ASSETS_DIR):
        shutil.rmtree(ASSETS_DIR)
    os.makedirs(ASSETS_DIR, exist_ok=True)

    # Find and process target people
    selected = []
    for person_dir_name in TARGET_PEOPLE:
        person_dir = os.path.join(lfw_home, person_dir_name)
        if not os.path.isdir(person_dir):
            print(f"  SKIP: {person_dir_name} not found in LFW cache")
            continue

        jpegs = sorted([f for f in os.listdir(person_dir) if f.lower().endswith(".jpg")])
        if not jpegs:
            print(f"  SKIP: {person_dir_name} has no JPEG files")
            continue

        # Use the first JPEG
        src_path = os.path.join(person_dir, jpegs[0])
        safe_name = person_dir_name.lower()
        identity_dir = os.path.join(ASSETS_DIR, safe_name)

        # Verify it's a real color image
        test_img = cv2.imread(src_path)
        if test_img is None or test_img.shape[0] < 100:
            print(f"  SKIP: {person_dir_name} image unreadable or too small")
            continue

        ok = create_variants(src_path, safe_name, identity_dir)
        if ok:
            files = os.listdir(identity_dir)
            print(f"  {safe_name}: {len(files)} variants ({test_img.shape[1]}x{test_img.shape[0]} color) from {jpegs[0]}")
            selected.append(safe_name)

    # If we didn't get 10 from the target list, scan for more
    if len(selected) < 10:
        print(f"\nFilling remaining slots (have {len(selected)}/10)...")
        for person_dir_name in sorted(os.listdir(lfw_home)):
            if len(selected) >= 10:
                break
            if person_dir_name.lower() in selected:
                continue
            person_dir = os.path.join(lfw_home, person_dir_name)
            if not os.path.isdir(person_dir):
                continue
            jpegs = [f for f in os.listdir(person_dir) if f.lower().endswith(".jpg")]
            if len(jpegs) < 10:  # only use people with many photos
                continue
            src_path = os.path.join(person_dir, jpegs[0])
            safe_name = person_dir_name.lower()
            identity_dir = os.path.join(ASSETS_DIR, safe_name)
            test_img = cv2.imread(src_path)
            if test_img is None or test_img.shape[0] < 100:
                continue
            ok = create_variants(src_path, safe_name, identity_dir)
            if ok:
                files = os.listdir(identity_dir)
                print(f"  {safe_name}: {len(files)} variants ({test_img.shape[1]}x{test_img.shape[0]})")
                selected.append(safe_name)

    total = sum(len(os.listdir(os.path.join(ASSETS_DIR, d)))
                for d in os.listdir(ASSETS_DIR)
                if os.path.isdir(os.path.join(ASSETS_DIR, d)))
    print(f"\nTotal: {total} images across {len(selected)} identities")
    print("Source: LFW (Labeled Faces in the Wild) — raw color JPEGs from sklearn cache")


if __name__ == "__main__":
    main()
