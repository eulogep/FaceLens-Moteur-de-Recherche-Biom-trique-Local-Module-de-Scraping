import os
import cv2
import insightface
from insightface.app import FaceAnalysis

ASSETS_DIR = "assets/test_faces"

app = FaceAnalysis(name="buffalo_l", root="~/.insightface", allowed_modules=['detection', 'recognition'])

def detect_robust(img_bgr, ctx_id=-1):
    # Strategy 1: Default 640x640, 0.5
    app.prepare(ctx_id=ctx_id, det_size=(640, 640), det_thresh=0.5)
    faces = app.get(img_bgr)
    if faces:
        return faces

    # Strategy 2: Multi-scale det_size (320, 320), (160, 160) with det_thresh=0.4
    for ds in [(320, 320), (160, 160)]:
        app.prepare(ctx_id=ctx_id, det_size=ds, det_thresh=0.4)
        faces = app.get(img_bgr)
        if faces:
            return faces

    # Strategy 3: Padding image to 640x640 with border
    h, w = img_bgr.shape[:2]
    pad_h = max(0, 640 - h)
    pad_w = max(0, 640 - w)
    img_padded = cv2.copyMakeBorder(
        img_bgr, pad_h // 2, pad_h - pad_h // 2, pad_w // 2, pad_w - pad_w // 2,
        cv2.BORDER_CONSTANT, value=[128, 128, 128]
    )
    app.prepare(ctx_id=ctx_id, det_size=(640, 640), det_thresh=0.35)
    faces = app.get(img_padded)
    if faces:
        return faces

    return []

identities = sorted([d for d in os.listdir(ASSETS_DIR) if os.path.isdir(os.path.join(ASSETS_DIR, d))])
print(f"Testing robust detection on {len(identities)} cropped images...")

success_count = 0
for name in identities:
    crop_path = os.path.join(ASSETS_DIR, name, f"{name}_cropped.jpg")
    if not os.path.exists(crop_path):
        continue
    img = cv2.imread(crop_path)
    faces = detect_robust(img)
    if faces:
        success_count += 1
        print(f"  [OK] {name}: {len(faces)} face(s) detected (det={faces[0].det_score:.4f})")
    else:
        print(f"  [FAIL] {name}: 0 faces detected")

print(f"\nResult: {success_count}/{len(identities)} cropped faces detected!")
