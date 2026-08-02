import os
import pytest
import numpy as np
from PIL import Image

from core.config import settings
from core.face_engine import FaceEngine

@pytest.fixture
def dummy_images(tmp_path):
    # Create two images with identical visual patterns (person A) and one with a completely different pattern (person B)
    img1_path = str(tmp_path / "personA_1.jpg")
    img2_path = str(tmp_path / "personA_2.jpg")
    img3_path = str(tmp_path / "personB.jpg")

    # Image A: Vertical stripes
    arr_a = np.zeros((300, 300, 3), dtype=np.uint8)
    arr_a[:, :150] = 255
    
    # Image B: Horizontal stripes
    arr_b = np.zeros((300, 300, 3), dtype=np.uint8)
    arr_b[:150, :] = 255

    Image.fromarray(arr_a).save(img1_path)
    Image.fromarray(arr_a.copy()).save(img2_path)
    Image.fromarray(arr_b).save(img3_path)

    return img1_path, img2_path, img3_path

def test_verify_1v1_phash_fallback(dummy_images):
    img1_path, img2_path, img3_path = dummy_images
    engine = FaceEngine(ctx_id=-1)

    # When no faces detected, verify_1v1 falls back to pHash comparison with explicit warning
    res1 = engine.verify_1v1(img1_path, img2_path)
    assert res1["verified"] is True
    assert res1["similarity"] == 1.0
    assert "Un ou plusieurs visages" in res1["warning"]
    assert settings.DISCLAIMER in res1["disclaimer"]

    res2 = engine.verify_1v1(img1_path, img3_path)
    assert res2["verified"] is False
    assert res2["similarity"] == 0.0
    assert "Un ou plusieurs visages" in res2["warning"]
