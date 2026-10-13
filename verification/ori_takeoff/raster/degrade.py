# SPDX-License-Identifier: Apache-2.0
"""Render a synthetic vector sheet to pixels and degrade it like a scan.

The page-to-pixel transform of every degraded image is returned so the
evaluator can project ground truth onto it. The recogniser never sees it.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict

import numpy as np


@dataclass(frozen=True)
class Degradation:
    name: str
    dpi: int = 300
    skew_deg: float = 0.0
    noise_sigma: float = 0.0
    blur_px: float = 0.0
    jpeg_quality: int | None = None
    seed: int = 0


# Ordered from easiest to hardest. Values chosen by ORI, not from any study.
LEVELS = [
    Degradation("clean_300dpi", 300),
    Degradation("scan_200dpi", 200, skew_deg=1.2, noise_sigma=6, blur_px=0.8, seed=1),
    Degradation("scan_150dpi_skew3", 150, skew_deg=-3.0, noise_sigma=12, blur_px=1.0, jpeg_quality=60, seed=2),
    Degradation("fax_100dpi", 100, skew_deg=2.0, noise_sigma=18, blur_px=1.2, jpeg_quality=40, seed=3),
    Degradation("poor_72dpi", 72, skew_deg=-1.5, noise_sigma=22, blur_px=1.5, jpeg_quality=30, seed=4),
]


def render_pdf_page(path, page_index: int, dpi: int) -> tuple[np.ndarray, float]:
    """Return a greyscale uint8 image and the page height in points."""
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(str(path))
    page = pdf[page_index]
    h_pt = page.get_height()
    img = page.render(scale=dpi / 72.0, grayscale=True).to_numpy()
    if img.ndim == 3:
        img = img[..., 0]
    page.close()
    pdf.close()
    return np.ascontiguousarray(img.astype(np.uint8)), h_pt


def degrade(img: np.ndarray, d: Degradation, h_pt: float) -> tuple[np.ndarray, np.ndarray]:
    """Apply skew, blur, noise and JPEG loss. Returns (image, 2x3 page-pt -> pixel affine)."""
    import cv2

    s = d.dpi / 72.0
    base = np.array([[s, 0, 0], [0, -s, h_pt * s]], dtype=float)  # PDF y-up -> pixel y-down
    h, w = img.shape
    out = img
    M = base
    if d.skew_deg:
        R = cv2.getRotationMatrix2D((w / 2, h / 2), d.skew_deg, 1.0)
        out = cv2.warpAffine(out, R, (w, h), flags=cv2.INTER_LINEAR, borderValue=255)
        M = R @ np.vstack([base, [0, 0, 1]])
    if d.blur_px:
        out = cv2.GaussianBlur(out, (0, 0), d.blur_px)
    if d.noise_sigma:
        rng = np.random.default_rng(d.seed)
        out = np.clip(out.astype(float) + rng.normal(0, d.noise_sigma, out.shape), 0, 255).astype(np.uint8)
    if d.jpeg_quality:
        ok, buf = cv2.imencode(".jpg", out, [cv2.IMWRITE_JPEG_QUALITY, d.jpeg_quality])
        out = cv2.imdecode(buf, cv2.IMREAD_GRAYSCALE)
    return out, M


def make_scan(pdf_path, page_index: int, d: Degradation) -> dict:
    img, h_pt = render_pdf_page(pdf_path, page_index, d.dpi)
    out, M = degrade(img, d, h_pt)
    return {"image": out, "page_to_px": M, "dpi": d.dpi, "degradation": asdict(d)}
