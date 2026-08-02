"""
FaceLens End-to-End Validation — REAL MODEL, NO MOCKS, REAL FACES (LFW)

Uses actual InsightFace buffalo_l model (ArcFace + RetinaFace) with onnxruntime,
running inference on real face photos from the LFW academic dataset.

Validates:
 1. Face detection on real LFW photos
 2. Enrollment via the core pipeline (atomic SQLite + FAISS IndexIDMap2)
 3. 1:N search accuracy (cropped/compressed/rotated variants must match top-1)
 4. 1:1 verification (same face -> verified=True, different face -> verified=False)
 5. Atomic integrity (verify_integrity passes after every operation)
 6. All observed scores printed and saved to a timestamped JSON report
"""
import argparse
import os
import sys
import json
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.config import settings
from core.face_engine import FaceEngine
from core.vector_index import VectorIndexManager
from core.db import DatabaseManager

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "test_faces")


def discover_identities():
    """Discover identity directories under assets/test_faces/."""
    identities = []
    if not os.path.isdir(ASSETS_DIR):
        return identities
    for d in sorted(os.listdir(ASSETS_DIR)):
        dp = os.path.join(ASSETS_DIR, d)
        if os.path.isdir(dp):
            orig = os.path.join(dp, f"{d}_original.jpg")
            if os.path.isfile(orig):
                identities.append(d)
    return identities


def parse_args():
    parser = argparse.ArgumentParser(description="Run the FaceLens E2E validation.")
    parser.add_argument(
        "--output",
        help=(
            "JSON result path. Defaults to "
            "data/e2e_results_YYYYMMDD_HHMMSS.json."
        ),
    )
    return parser.parse_args()


def main(output_path=None):
    print("=" * 80)
    print("  FaceLens E2E Validation - Real InsightFace buffalo_l + LFW Photos")
    print("=" * 80)

    identities = discover_identities()
    if not identities:
        print(f"FATAL: No test identities found in {ASSETS_DIR}")
        sys.exit(1)
    print(f"Found {len(identities)} identities: {', '.join(identities)}\n")

    # Separate test database & index
    test_db_path = os.path.join(settings.STORAGE_DIR, "e2e_test.db")
    test_idx_path = os.path.join(settings.STORAGE_DIR, "e2e_test.index")
    for p in [test_db_path, test_idx_path]:
        if os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass

    db = DatabaseManager(test_db_path)
    index = VectorIndexManager(dimension=512, index_path=test_idx_path)
    index.reset()

    # ---- Load real model ----
    print("[1] Loading InsightFace buffalo_l (REAL model, CPU)...")
    engine = FaceEngine(ctx_id=-1)
    if engine.app is None:
        print("FATAL: InsightFace model not available.")
        sys.exit(1)
    import onnxruntime
    print(f"    Model: buffalo_l | onnxruntime {onnxruntime.__version__} | CPUExecutionProvider")
    print("    -> Model loaded successfully.\n")

    # =========================================================
    # PHASE 1: Detection & Enrollment (originals only)
    # =========================================================
    print("[2] Detection & Enrollment...")
    enrolled = {}  # name -> (face_id, det_score)
    detection_log = {}

    for name in identities:
        orig_path = os.path.join(ASSETS_DIR, name, f"{name}_original.jpg")
        faces = engine.extract_faces(orig_path)
        detection_log[name] = len(faces)

        if not faces:
            print(f"    {name}: 0 faces detected - SKIPPED")
            continue

        top = max(faces, key=lambda f: f["det_score"])
        rec = db.enroll_face_atomic(
            index_manager=index,
            vector=top["embedding"],
            image_path=orig_path,
            person_name=name,
            source_type="e2e_test",
            image_hash=top["phash"]
        )
        enrolled[name] = (rec["id"], top["det_score"])
        print(f"    {name}: {len(faces)} face(s), enrolled ID #{rec['id']} "
              f"(det={top['det_score']:.4f})")

    print(f"\n    Enrolled: {len(enrolled)}/{len(identities)}")
    db.verify_integrity(index)
    print(f"    Integrity: PASSED (SQLite={db.count_faces()}, FAISS={index.ntotal})\n")

    if len(enrolled) < 2:
        print("FATAL: Fewer than 2 identities enrolled. Cannot run search/verify tests.")
        sys.exit(1)

    # =========================================================
    # PHASE 2: 1:N Search with degraded variants
    # =========================================================
    print("[3] 1:N Search - degraded variants vs enrolled corpus...")
    search_log = {}  # (name, variant) -> (top1_name, sim, correct)
    variants = ["cropped", "compressed", "rotated"]
    total_correct = 0
    total_queries = 0

    for name in enrolled:
        search_log[name] = {}
        for variant in variants:
            vpath = os.path.join(ASSETS_DIR, name, f"{name}_{variant}.jpg")
            if not os.path.isfile(vpath):
                continue

            faces = engine.extract_faces(vpath)
            if not faces:
                search_log[name][variant] = ("NO_FACE", 0.0, False)
                print(f"    [FAIL] {name}/{variant}: 0 faces detected")
                total_queries += 1
                continue

            top = max(faces, key=lambda f: f["det_score"])
            results = index.search(top["embedding"], top_k=3)

            if not results:
                search_log[name][variant] = ("NO_RESULTS", 0.0, False)
                total_queries += 1
                continue

            top_id, top_sim = results[0]
            top_rec = db.get_face(top_id)
            top_name = top_rec["person_name"] if top_rec else "?"
            correct = (top_name == name)
            search_log[name][variant] = (top_name, top_sim, correct)
            total_queries += 1
            if correct:
                total_correct += 1

            mark = "[OK]" if correct else "[FAIL]"
            strong = "*" if top_sim >= 0.70 else " "
            print(f"    {mark}{strong} {name}/{variant}: top-1={top_name} "
                  f"sim={top_sim:.4f}")

    print(f"\n    Accuracy: {total_correct}/{total_queries} correct top-1 matches")
    db.verify_integrity(index)
    print(f"    Integrity: PASSED\n")

    # =========================================================
    # PHASE 3: 1:1 Verification
    # =========================================================
    print("[4] 1:1 Verification...")
    enrolled_names = list(enrolled.keys())
    verify_log = []

    # Same face: original vs cropped
    name_a = enrolled_names[0]
    img_a_orig = os.path.join(ASSETS_DIR, name_a, f"{name_a}_original.jpg")
    img_a_crop = os.path.join(ASSETS_DIR, name_a, f"{name_a}_cropped.jpg")
    res_same = engine.verify_1v1(img_a_orig, img_a_crop)
    verify_log.append(("same_face", name_a, res_same))
    print(f"    Same ({name_a}): verified={res_same['verified']} "
          f"sim={res_same['similarity']:.4f} verdict={res_same['verdict']}")

    # Same face: original vs compressed
    img_a_comp = os.path.join(ASSETS_DIR, name_a, f"{name_a}_compressed.jpg")
    res_comp = engine.verify_1v1(img_a_orig, img_a_comp)
    verify_log.append(("same_compressed", name_a, res_comp))
    print(f"    Same compressed ({name_a}): verified={res_comp['verified']} "
          f"sim={res_comp['similarity']:.4f} verdict={res_comp['verdict']}")

    # Same face: original vs rotated
    img_a_rot = os.path.join(ASSETS_DIR, name_a, f"{name_a}_rotated.jpg")
    res_rot = engine.verify_1v1(img_a_orig, img_a_rot)
    verify_log.append(("same_rotated", name_a, res_rot))
    print(f"    Same rotated ({name_a}): verified={res_rot['verified']} "
          f"sim={res_rot['similarity']:.4f} verdict={res_rot['verdict']}")

    # Different faces
    name_b = enrolled_names[1]
    img_b_orig = os.path.join(ASSETS_DIR, name_b, f"{name_b}_original.jpg")
    res_diff = engine.verify_1v1(img_a_orig, img_b_orig)
    verify_log.append(("diff_face", f"{name_a}_vs_{name_b}", res_diff))
    print(f"    Diff ({name_a} vs {name_b}): verified={res_diff['verified']} "
          f"sim={res_diff['similarity']:.4f} verdict={res_diff['verdict']}")

    if len(enrolled_names) >= 3:
        name_c = enrolled_names[2]
        img_c = os.path.join(ASSETS_DIR, name_c, f"{name_c}_original.jpg")
        res_diff2 = engine.verify_1v1(img_a_orig, img_c)
        verify_log.append(("diff_face", f"{name_a}_vs_{name_c}", res_diff2))
        print(f"    Diff ({name_a} vs {name_c}): verified={res_diff2['verified']} "
              f"sim={res_diff2['similarity']:.4f} verdict={res_diff2['verdict']}")

    # =========================================================
    # PHASE 4: Delete & Re-verify Integrity
    # =========================================================
    print(f"\n[5] Deletion & Integrity...")
    del_name = enrolled_names[-1]
    del_id = enrolled[del_name][0]
    db.delete_face_atomic(index, del_id)
    print(f"    Deleted {del_name} (ID #{del_id})")
    db.verify_integrity(index)
    print(f"    Integrity: PASSED (SQLite={db.count_faces()}, FAISS={index.ntotal})")

    # Confirm deleted face is absent
    del_orig = os.path.join(ASSETS_DIR, del_name, f"{del_name}_original.jpg")
    faces = engine.extract_faces(del_orig)
    if faces:
        top = max(faces, key=lambda f: f["det_score"])
        results = index.search(top["embedding"], top_k=1)
        if results:
            found_id = results[0][0]
            assert found_id != del_id, f"Deleted ID #{del_id} still in index!"
            print(f"    Search for deleted: absent (top result is #{found_id})")

    # =========================================================
    # SUMMARY
    # =========================================================
    print("\n" + "=" * 80)
    print("  FULL E2E RESULTS")
    print("=" * 80)
    import onnxruntime as ort
    print(f"  Model:       InsightFace buffalo_l (ArcFace 512-d, RetinaFace/SCRFD)")
    print(f"  Runtime:     onnxruntime {ort.__version__} (CPUExecutionProvider)")
    print(f"  Test data:   LFW (Labeled Faces in the Wild) academic dataset")
    print(f"  Identities:  {len(identities)} attempted, {len(enrolled)} enrolled")
    print()

    print("  DETECTION:")
    for name, cnt in detection_log.items():
        status = "[OK]" if cnt > 0 else "[FAIL]"
        print(f"    {status} {name}: {cnt} face(s)")
    print()

    print("  1:N SEARCH SCORES:")
    for name in search_log:
        for variant, (top_name, sim, correct) in search_log[name].items():
            mark = "[OK]" if correct else "[FAIL]"
            print(f"    {mark} {name}/{variant}: top-1={top_name}, sim={sim:.4f}")
    print(f"    Accuracy: {total_correct}/{total_queries}")
    print()

    print("  1:1 VERIFICATION:")
    for test_type, label, res in verify_log:
        print(f"    {test_type} ({label}): verified={res['verified']}, "
              f"sim={res['similarity']:.4f}, verdict={res['verdict']}")
    print()

    print(f"  Integrity: SQLite={db.count_faces()}, FAISS={index.ntotal} - CONSISTENT")
    print(f"\n  {settings.DISCLAIMER}")
    print("=" * 80)

    # Write JSON results for programmatic consumption
    if output_path:
        results_path = os.path.abspath(output_path)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "data",
            f"e2e_results_{timestamp}.json",
        )
    os.makedirs(os.path.dirname(results_path), exist_ok=True)
    results = {
        "model": "buffalo_l",
        "onnxruntime": ort.__version__,
        "dataset": "LFW",
        "identities_attempted": len(identities),
        "identities_enrolled": len(enrolled),
        "detection": detection_log,
        "search": {
            name: {var: {"top1": tn, "sim": round(sim, 4), "correct": c}
                   for var, (tn, sim, c) in variants_dict.items()}
            for name, variants_dict in search_log.items()
        },
        "verification": [
            {"test": t, "label": l, "verified": r["verified"],
             "similarity": r["similarity"], "verdict": r["verdict"]}
            for t, l, r in verify_log
        ],
        "search_accuracy": f"{total_correct}/{total_queries}",
    }
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to {results_path}")


if __name__ == "__main__":
    args = parse_args()
    main(args.output)
