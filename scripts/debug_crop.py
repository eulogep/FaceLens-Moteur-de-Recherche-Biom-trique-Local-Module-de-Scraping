import cv2
import numpy as np
from insightface.app import FaceAnalysis

img_path = "assets/test_faces/alejandro_toledo/alejandro_toledo_cropped.jpg"
img = cv2.imread(img_path)
print(f"Cropped image shape: {img.shape}")

app = FaceAnalysis(name="buffalo_l", root="~/.insightface", allowed_modules=['detection', 'recognition'])

# Test 1: Standard prepare (640, 640), det_thresh=0.5
app.prepare(ctx_id=-1, det_size=(640, 640), det_thresh=0.5)
faces1 = app.get(img)
print("1. Default 640x640 det_thresh=0.5:", len(faces1))

# Test 2: prepare (320, 320), det_thresh=0.5
app.prepare(ctx_id=-1, det_size=(320, 320), det_thresh=0.5)
faces2 = app.get(img)
print("2. Prepare 320x320 det_thresh=0.5:", len(faces2))

# Test 3: prepare (640, 640), det_thresh=0.3
app.prepare(ctx_id=-1, det_size=(640, 640), det_thresh=0.3)
faces3 = app.get(img)
print("3. Prepare 640x640 det_thresh=0.3:", len(faces3))

# Test 4: Upscale image x2 (350x350)
h, w = img.shape[:2]
img2x = cv2.resize(img, (w * 2, h * 2), interpolation=cv2.INTER_CUBIC)
app.prepare(ctx_id=-1, det_size=(640, 640), det_thresh=0.4)
faces4 = app.get(img2x)
print("4. Upscale x2 + det_thresh=0.4:", len(faces4))

# Test 5: Pad image with border to 640x640
pad_h = max(0, 640 - h)
pad_w = max(0, 640 - w)
img_padded = cv2.copyMakeBorder(img, pad_h//2, pad_h - pad_h//2, pad_w//2, pad_w - pad_w//2, cv2.BORDER_CONSTANT, value=[128,128,128])
app.prepare(ctx_id=-1, det_size=(640, 640), det_thresh=0.4)
faces5 = app.get(img_padded)
print("5. Padded to 640x640 + det_thresh=0.4:", len(faces5))

# Test 6: Check crop generation in generate_test_faces.py!
print("\nChecking original vs crop bounding box...")
orig_img = cv2.imread("assets/test_faces/alejandro_toledo/alejandro_toledo_original.jpg")
app.prepare(ctx_id=-1, det_size=(640, 640), det_thresh=0.5)
orig_faces = app.get(orig_img)
if orig_faces:
    print("Original face bbox:", orig_faces[0].bbox)
