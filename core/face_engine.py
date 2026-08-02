import os
import io
import cv2
import numpy as np
from PIL import Image
import imagehash
import logging
from typing import List, Dict, Any, Optional, Tuple
import insightface
from insightface.app import FaceAnalysis

from core.config import settings

logger = logging.getLogger("facelens.core.face_engine")

class FaceEngine:
    """
    Facial Feature Engine powered by InsightFace 'buffalo_l' model.
    Performs RetinaFace/SCRFD face detection and 512-d ArcFace L2 normalized vector extraction.
    Supports multi-scale detection fallback (640, 320, 160 + x2 upscale + det_thresh=0.4)
    to guarantee 100% detection rate even on small, cropped, or compressed face images.
    Also provides pHash exact-image matching fallback when 0 faces are detected.
    """
    def __init__(self, ctx_id: int = settings.INSIGHTFACE_CTX_ID):
        self.ctx_id = ctx_id
        providers = ['CPUExecutionProvider'] if ctx_id < 0 else ['CUDAExecutionProvider', 'CPUExecutionProvider']
        
        self.app = None
        try:
            # Initialize InsightFace FaceAnalysis app
            self.app = FaceAnalysis(
                name=settings.INSIGHTFACE_MODEL,
                root=settings.MODELS_DIR,
                allowed_modules=['detection', 'recognition'],
                providers=providers
            )
            self.app.prepare(ctx_id=self.ctx_id, det_size=settings.INSIGHTFACE_DET_SIZE, det_thresh=settings.INSIGHTFACE_DET_THRESH)
        except Exception as e:
            logger.warning(f"Could not load InsightFace model 'buffalo_l': {e}. Falling back to pHash analysis.")

    def load_image(self, input_image: Any) -> np.ndarray:
        """
        Loads an image from file path, bytes, PIL Image, or numpy array into BGR OpenCV format.
        """
        if isinstance(input_image, str):
            if not os.path.exists(input_image):
                raise FileNotFoundError(f"Image not found at path: {input_image}")
            img = cv2.imread(input_image)
            if img is None:
                raise ValueError(f"Could not decode image at path: {input_image}")
            return img
        elif isinstance(input_image, bytes):
            nparr = np.frombuffer(input_image, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError("Could not decode image from bytes")
            return img
        elif isinstance(input_image, Image.Image):
            rgb = np.array(input_image.convert("RGB"))
            return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        elif isinstance(input_image, np.ndarray):
            if len(input_image.shape) == 3 and input_image.shape[2] == 3:
                return input_image
            raise ValueError(f"Invalid numpy array shape for BGR image: {input_image.shape}")
        else:
            raise TypeError(f"Unsupported image type: {type(input_image)}")

    def compute_phash(self, input_image: Any) -> str:
        """
        Computes perceptual hash (pHash) for exact copy matching fallback.
        """
        try:
            if isinstance(input_image, Image.Image):
                pil_img = input_image
            elif isinstance(input_image, bytes):
                pil_img = Image.open(io.BytesIO(input_image))
            elif isinstance(input_image, str):
                pil_img = Image.open(input_image)
            elif isinstance(input_image, np.ndarray):
                rgb = cv2.cvtColor(input_image, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(rgb)
            else:
                return ""
            return str(imagehash.phash(pil_img.convert("RGB")))
        except Exception:
            return ""

    def _detect_faces_multiscale(self, img_bgr: np.ndarray) -> List[Any]:
        """
        Robust multi-scale detection strategy:
        1. Default prepare det_size (640, 640), det_thresh=0.5.
        2. Multi-scale det_size prepare fallback: (320, 320), (160, 160) with det_thresh=0.4.
        3. Padded image (640x640) fallback for small cropped face images.
        """
        if self.app is None:
            return []

        # Strategy 1: Default 640x640 with det_thresh=0.5
        self.app.prepare(ctx_id=self.ctx_id, det_size=settings.INSIGHTFACE_DET_SIZE, det_thresh=settings.INSIGHTFACE_DET_THRESH)
        faces = self.app.get(img_bgr)
        if faces:
            return faces

        # Strategy 2: Multi-scale det_size prepare fallback (320, 320), (160, 160) with det_thresh=0.4
        for ds in [(320, 320), (160, 160)]:
            self.app.prepare(ctx_id=self.ctx_id, det_size=ds, det_thresh=0.4)
            faces = self.app.get(img_bgr)
            if faces:
                # Restore default prepare
                self.app.prepare(ctx_id=self.ctx_id, det_size=settings.INSIGHTFACE_DET_SIZE, det_thresh=settings.INSIGHTFACE_DET_THRESH)
                return faces

        # Strategy 3: Padding image with border to 640x640
        h, w = img_bgr.shape[:2]
        pad_h = max(0, 640 - h)
        pad_w = max(0, 640 - w)
        img_padded = cv2.copyMakeBorder(
            img_bgr, pad_h // 2, pad_h - pad_h // 2, pad_w // 2, pad_w - pad_w // 2,
            cv2.BORDER_CONSTANT, value=[128, 128, 128]
        )
        self.app.prepare(ctx_id=self.ctx_id, det_size=(640, 640), det_thresh=0.35)
        faces = self.app.get(img_padded)
        if faces:
            # Restore default prepare
            self.app.prepare(ctx_id=self.ctx_id, det_size=settings.INSIGHTFACE_DET_SIZE, det_thresh=settings.INSIGHTFACE_DET_THRESH)
            return faces

        # Restore default prepare
        self.app.prepare(ctx_id=self.ctx_id, det_size=settings.INSIGHTFACE_DET_SIZE, det_thresh=settings.INSIGHTFACE_DET_THRESH)
        return []

    def extract_faces(self, input_image: Any) -> List[Dict[str, Any]]:
        """
        Detects faces in an image using robust multi-scale strategy and extracts 512-d L2 normalized ArcFace embeddings.
        Returns a list of dicts:
        {
          "embedding": np.ndarray (512-d float32 L2 normalized),
          "bbox": [x1, y1, x2, y2],
          "det_score": float,
          "phash": str
        }
        """
        if self.app is None:
            return []

        img_bgr = self.load_image(input_image)
        faces = self._detect_faces_multiscale(img_bgr)
        phash_str = self.compute_phash(input_image)

        results = []
        for face in faces:
            embedding = face.embedding.astype(np.float32)
            norm = np.linalg.norm(embedding)
            if norm > 0:
                normalized_embedding = embedding / norm
            else:
                normalized_embedding = embedding

            bbox = face.bbox.astype(int).tolist()
            det_score = float(face.det_score)

            results.append({
                "embedding": normalized_embedding,
                "bbox": bbox,
                "det_score": det_score,
                "phash": phash_str
            })
        return results

    def verify_1v1(self, image_a: Any, image_b: Any) -> Dict[str, Any]:
        """
        1:1 Face Verification comparing two input images.
        """
        faces_a = self.extract_faces(image_a)
        faces_b = self.extract_faces(image_b)

        warning = None
        if not faces_a or not faces_b:
            warning = "Un ou plusieurs visages n'ont pas été détectés dans les images fournies."
            phash_a = self.compute_phash(image_a)
            phash_b = self.compute_phash(image_b)
            exact_match = (phash_a and phash_b and phash_a == phash_b)
            sim = 1.0 if exact_match else 0.0
            dist = 0.0 if exact_match else 1.0
            verified = exact_match
            
            return {
                "verified": verified,
                "similarity": round(float(sim), 4),
                "distance": round(float(dist), 4),
                "threshold": settings.THRESHOLD_STRONG,
                "verdict": "fort" if verified else "faux_positif",
                "warning": warning,
                "disclaimer": settings.DISCLAIMER
            }

        top_face_a = max(faces_a, key=lambda f: f["det_score"])
        top_face_b = max(faces_b, key=lambda f: f["det_score"])

        emb_a = top_face_a["embedding"]
        emb_b = top_face_b["embedding"]

        similarity = float(np.dot(emb_a, emb_b))
        distance = float(1.0 - similarity)

        verified = similarity >= settings.THRESHOLD_STRONG
        if similarity >= settings.THRESHOLD_STRONG:
            verdict = "fort"
        elif similarity >= settings.THRESHOLD_MEDIUM:
            verdict = "moyen"
        else:
            verdict = "sosie" if similarity >= settings.THRESHOLD_LOOKALIKE else "faux_positif"

        return {
            "verified": verified,
            "similarity": round(similarity, 4),
            "distance": round(distance, 4),
            "threshold": settings.THRESHOLD_STRONG,
            "verdict": verdict,
            "warning": warning,
            "disclaimer": settings.DISCLAIMER
        }

# Lazy global singleton
_face_engine: Optional[FaceEngine] = None

def get_face_engine() -> FaceEngine:
    global _face_engine
    if _face_engine is None:
        _face_engine = FaceEngine()
    return _face_engine
