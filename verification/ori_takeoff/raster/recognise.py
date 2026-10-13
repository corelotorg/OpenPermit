# SPDX-License-Identifier: Apache-2.0
"""Recognise walls, labels and dimension strings on a raster plan (DRAFT 0.1).

Classical image processing (OpenCV) plus Tesseract OCR. Inputs are pixels and
the scan resolution the scanner declared; nothing else. Outputs are pixel
coordinates in the *input* image plus, where a scale note was read, real-world
lengths. Every item is ai_extracted_unverified / unknown.
"""
from __future__ import annotations

import math
import re

import numpy as np

from . import ORIGIN, VALUE_STATUS, VERSION
from .. import units as U


def estimate_skew(gray: np.ndarray) -> float:
    """Dominant small rotation (degrees, OpenCV sign convention) from long straight lines."""
    import cv2

    edges = cv2.Canny(gray, 50, 150)
    min_len = max(40, int(min(gray.shape) * 0.08))
    lines = cv2.HoughLinesP(edges, 1, math.pi / 1800, threshold=80, minLineLength=min_len, maxLineGap=4)
    if lines is None:
        return 0.0
    angs, wts = [], []
    for x0, y0, x1, y1 in lines.reshape(-1, 4).tolist():
        a = math.degrees(math.atan2(y1 - y0, x1 - x0))
        a = ((a + 45) % 90) - 45  # fold to [-45, 45)
        if abs(a) <= 10:
            angs.append(a)
            wts.append(math.hypot(x1 - x0, y1 - y0))
    if not angs:
        return 0.0
    order = np.argsort(angs)
    a, w = np.array(angs)[order], np.array(wts)[order]
    med = a[np.searchsorted(np.cumsum(w), w.sum() / 2)]
    return float(-med)  # rotation that, applied with getRotationMatrix2D, undid the skew


def _rot(gray, ang):
    import cv2

    h, w = gray.shape
    R = cv2.getRotationMatrix2D((w / 2, h / 2), -ang, 1.0)
    return cv2.warpAffine(gray, R, (w, h), flags=cv2.INTER_LINEAR, borderValue=255), R


def detect_walls(gray: np.ndarray, dpi: int, min_thick_pt: float = 5.5, max_thick_pt: float = 16.0,
                 min_len_pt: float = 18.0) -> list[dict]:
    """Thick filled bands become wall candidates (pixel coords of the given image)."""
    import cv2

    px = dpi / 72.0
    g = cv2.GaussianBlur(cv2.medianBlur(gray, 3), (0, 0), max(1.0, 0.35 * px))
    dark = (g < 218).astype(np.uint8)
    k = max(2, int(round(min_thick_pt * px * 0.75)))
    core = cv2.morphologyEx(dark, cv2.MORPH_OPEN, np.ones((k, k), np.uint8))
    L = max(3, int(round(min_len_pt * px)))
    walls = []
    for orient, kern in (("h", np.ones((1, L), np.uint8)), ("v", np.ones((L, 1), np.uint8))):
        m = cv2.morphologyEx(core, cv2.MORPH_OPEN, kern)
        n, lab, stats, _ = cv2.connectedComponentsWithStats(m, 8)
        for i in range(1, n):
            x, y, w, h, area = stats[i]
            length, thick = (w, h) if orient == "h" else (h, w)
            # use the median run across the band, robust to corner blobs
            sub = lab[y:y + h, x:x + w] == i
            runs = sub.sum(axis=0 if orient == "h" else 1)
            runs = runs[runs > 0]
            t = float(np.median(runs)) if len(runs) else float(thick)
            if not (min_thick_pt * px * 0.75 <= t <= max_thick_pt * px * 1.4):
                continue
            if length < 2.5 * t:
                continue
            if orient == "h":
                ys = np.nonzero(sub.any(axis=1))[0]
                cy = y + (ys.min() + ys.max()) / 2
                p0, p1 = (float(x), float(cy)), (float(x + w), float(cy))
            else:
                xs = np.nonzero(sub.any(axis=0))[0]
                cx = x + (xs.min() + xs.max()) / 2
                p0, p1 = (float(cx), float(y)), (float(cx), float(y + h))
            walls.append({"orientation": orient, "p0_px": p0, "p1_px": p1, "thickness_px": t,
                          "length_px": float(length)})
    return walls


def _ocr_lines(gray, rotate: int = 0, upscale: float = 1.0, blur: float = 1.2) -> list[dict]:
    import cv2
    import pytesseract

    img = gray
    if upscale != 1.0:
        img = cv2.resize(img, None, fx=upscale, fy=upscale, interpolation=cv2.INTER_CUBIC)
    if blur:
        img = cv2.GaussianBlur(img, (0, 0), blur)
    H, W = img.shape
    if rotate == 90:
        img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
    _, img = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    d = pytesseract.image_to_data(img, config="--psm 11", output_type=pytesseract.Output.DICT)
    words = []
    for i, t in enumerate(d["text"]):
        t = t.strip()
        if not t or float(d["conf"][i]) < 0:
            continue
        x, y, w, h = d["left"][i], d["top"][i], d["width"][i], d["height"][i]
        cx, cy = x + w / 2, y + h / 2
        if rotate == 90:  # undo clockwise rotation: (cx, cy) in rotated -> original
            cx, cy = cy, H - cx
            w, h = h, w
        words.append({"text": t, "cx": cx / upscale, "cy": cy / upscale, "h": h / upscale,
                      "w": w / upscale, "conf": float(d["conf"][i]),
                      "key": (d["block_num"][i], d["par_num"][i], d["line_num"][i])})
    # group into lines
    lines: dict = {}
    for wd in words:
        lines.setdefault(wd["key"], []).append(wd)
    out = []
    for ws in lines.values():
        out.append({"text": " ".join(w["text"] for w in ws),
                    "cx": float(np.mean([w["cx"] for w in ws])), "cy": float(np.mean([w["cy"] for w in ws])),
                    "conf": float(np.mean([w["conf"] for w in ws])), "rotation": rotate})
    return out


_DIM_RE = re.compile(r"(\d{1,3})\s*['’`]\s*-?\s*(\d{1,2})?(?:\s+(\d)/(\d{1,2}))?\s*[\"”]?")


_OCR_MARKS = str.maketrans({"\u00b0": '"', "\u201d": '"', "\u201c": '"', "\u2019": "'", "\u2018": "'", "`": "'"})


def clean_ocr(text: str) -> str:
    """Undo common Tesseract confusions for inch and foot marks only; digits are never guessed."""
    return U.normalize(text.translate(_OCR_MARKS)).replace("''", '"').strip()


def parse_ocr_dimension(text: str) -> float | None:
    """Lenient feet-inch parse for OCR output; None when unsure."""
    t = clean_ocr(text)
    m = _DIM_RE.fullmatch(t)
    if m and m.group(2) and int(m.group(2)) >= 12:
        return None  # an OCR misread is likelier than a 12+ inch remainder
    v = U.parse_ft_in(t)
    if v is not None:
        return v
    if not m:
        return None
    ft, inch = int(m.group(1)), int(m.group(2) or 0)
    if inch >= 12:
        return None
    frac = int(m.group(3)) / int(m.group(4)) if m.group(3) else 0.0
    return ft * 12 + inch + frac


def recognise(gray: np.ndarray, dpi: int, deskew: bool = True) -> dict:
    """Full pass. Coordinates in the result are pixels of the *input* image."""
    import cv2

    ang = estimate_skew(gray) if deskew else 0.0
    work, R = _rot(gray, ang) if abs(ang) > 0.05 else (gray, np.array([[1, 0, 0], [0, 1, 0]], float))
    Rinv = cv2.invertAffineTransform(R)

    def back(p):
        x, y = p
        return (float(Rinv[0, 0] * x + Rinv[0, 1] * y + Rinv[0, 2]), float(Rinv[1, 0] * x + Rinv[1, 1] * y + Rinv[1, 2]))

    walls = detect_walls(work, dpi)
    up = max(1.0, 300.0 / dpi)
    texts = []
    for blur in (1.2, 0.0):  # two binarisations; keep each distinct reading once
        for t in _ocr_lines(work, 0, up, blur) + _ocr_lines(work, 90, up, blur):
            if not any(o["text"] == t["text"] and math.hypot(o["cx"] - t["cx"], o["cy"] - t["cy"]) < 10 for o in texts):
                texts.append(t)

    scale = {"status": "unknown", "real_in_per_px": None}
    for t in texts:
        if "SCALE" in t["text"].upper():
            sc = U.parse_scale_note(clean_ocr(t["text"]))
            if isinstance(sc, float):
                scale = {"status": "ocr_scale_note_unconfirmed", "text": t["text"],
                         "real_in_per_paper_in": sc, "real_in_per_px": sc / dpi}
                break
    k = scale["real_in_per_px"]
    items = []
    for i, w in enumerate(walls):
        items.append({"id": f"scan-wall-{i:03d}", "kind": "wall", "orientation": w["orientation"],
                      "p0_px": back(w["p0_px"]), "p1_px": back(w["p1_px"]),
                      "thickness_px": round(w["thickness_px"], 2),
                      "thickness_in": None if k is None else round(w["thickness_px"] * k, 2),
                      "length_in": None if k is None else round(w["length_px"] * k, 1),
                      "origin": ORIGIN, "value_status": VALUE_STATUS})
    for i, t in enumerate(texts):
        v = parse_ocr_dimension(t["text"])
        items.append({"id": f"scan-text-{i:03d}", "kind": "dimension_text" if v is not None else "text",
                      "text": t["text"], "value_in": v, "at_px": back((t["cx"], t["cy"])),
                      "ocr_confidence": round(t["conf"], 1), "rotation": t["rotation"],
                      "origin": ORIGIN, "value_status": VALUE_STATUS})
    return {"report": "ori-scan-recognition-0.1", "tool": f"ori_takeoff.raster {VERSION}",
            "status": "DRAFT - every item unverified; a person must confirm before any use",
            "dpi_declared": dpi, "skew_estimated_deg": round(ang, 3), "scale": scale, "items": items}
