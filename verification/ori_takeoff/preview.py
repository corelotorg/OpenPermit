# SPDX-License-Identifier: Apache-2.0
"""Overlay previews: SVG (vector, page coordinates) and PNG (overlay drawn on the rendered page).

PDF pages are rendered with pypdfium2 (Apache-2.0 / BSD-3-Clause), the renderer pdfplumber
already depends on. DXF drawings have no page image; the overlay is drawn on a white canvas
with the source linework in grey.
"""

from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

COLORS = {"IfcWall": (200, 30, 30), "IfcDoor": (20, 120, 220), "IfcWindow": (0, 170, 170), "IfcOpeningElement": (240, 140, 0),
          "IfcSpace": (60, 170, 60), "IfcStair": (150, 60, 200), "IfcAnnotation": (110, 110, 110)}
ALPHA = {"IfcSpace": 60, "IfcWall": 110, "IfcStair": 90}


def _rings(g):
    if g["type"] == "Polygon":
        return g["coordinates"], True
    if g["type"] == "LineString":
        return [g["coordinates"]], False
    return [[g["coordinates"]]], False


def _bounds(page, skip_points=False):
    xs, ys = [], []
    for e in page["elements"]:
        if skip_points and e["geometry_page"]["type"] == "Point":
            continue
        rings, _ = _rings(e["geometry_page"])
        for r in rings:
            for x, y in r:
                xs.append(x)
                ys.append(y)
    return (min(xs), min(ys), max(xs), max(ys)) if xs else (0, 0, 1, 1)


def write_svg(page: dict, path: str | Path, background_href: str | None = None, pad: float = 24.0) -> Path:
    if page["page_units"] == "pt" and page["size_page_units"][0]:
        x0, y0, (x1, y1) = 0.0, 0.0, page["size_page_units"]
    else:
        x0, y0, x1, y1 = _bounds(page)
        x0, y0, x1, y1 = x0 - pad, y0 - pad, x1 + pad, y1 + pad
    w, h = x1 - x0, y1 - y0
    tf = lambda x, y: (x - x0, y1 - y)  # noqa: E731  (flip y for SVG)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {w:.2f} {h:.2f}" '
           f'width="{w:.0f}" height="{h:.0f}">',
           f"<title>ORI plan overlay p{page['page']} {escape(str(page.get('page_label')))}: reviewer evidence, not approval</title>"]
    if background_href:
        out.append(f'<image xlink:href="{escape(background_href)}" x="0" y="0" width="{w:.2f}" height="{h:.2f}" opacity="0.6"/>')
    order = ["IfcSpace", "IfcWall", "IfcOpeningElement", "IfcWindow", "IfcDoor", "IfcStair", "IfcAnnotation"]
    for cls in order:
        for e in [e for e in page["elements"] if e["ifc_class"] == cls]:
            r, g, b = COLORS[cls]
            rings, closed = _rings(e["geometry_page"])
            if e["geometry_page"]["type"] == "Point":
                x, y = tf(*rings[0][0])
                out.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="1.5" fill="rgb({r},{g},{b})"><title>{escape(e["id"])}</title></circle>')
                continue
            d = " ".join("M " + " L ".join(f"{tf(*p)[0]:.2f} {tf(*p)[1]:.2f}" for p in ring) + (" Z" if closed else "") for ring in rings)
            fill = f'rgba({r},{g},{b},{ALPHA.get(cls, 70) / 255:.2f})' if closed else "none"
            label = escape(f"{e['id']} {e['ifc_class']} {e.get('name') or ''} [{e['provenance']['method']}, {e['provenance']['review_status']}]")
            out.append(f'<path d="{d}" fill="{fill}" fill-rule="evenodd" stroke="rgb({r},{g},{b})" stroke-width="0.8"><title>{label}</title></path>')
            if cls == "IfcSpace" and e.get("name"):
                c = e["geometry_page"]["coordinates"][0]
                cx = sum(p[0] for p in c[:-1]) / (len(c) - 1)
                cy = sum(p[1] for p in c[:-1]) / (len(c) - 1)
                x, y = tf(cx, cy)
                a = e["properties"].get("area_ft2")
                out.append(f'<text x="{x:.1f}" y="{y + 14:.1f}" font-size="7" text-anchor="middle" fill="rgb(20,90,20)">'
                           f'{escape(e["id"])}{"" if a is None else f" {a:.1f} ft2"}</text>')
    out.append("</svg>")
    path = Path(path)
    path.write_text("\n".join(out) + "\n")
    return path


def render_pdf_page(pdf_path: str | Path, page: int, dpi: float = 100.0):
    import pypdfium2 as pdfium

    doc = pdfium.PdfDocument(str(pdf_path))
    img = doc[page - 1].render(scale=dpi / 72.0).to_pil().convert("RGB")
    doc.close()
    return img


def write_png(page: dict, path: str | Path, pdf_path: str | Path | None = None, dpi: float = 100.0,
              crop_to_overlay: bool = True, legend: bool = True) -> Path:
    from PIL import Image, ImageDraw

    k = dpi / 72.0 if page["page_units"] == "pt" else None
    if pdf_path is not None and page["page_units"] == "pt":
        base = render_pdf_page(pdf_path, page["page"], dpi)
        H = page["size_page_units"][1]
        tf = lambda x, y: (x * k, (H - y) * k)  # noqa: E731
    else:
        x0, y0, x1, y1 = _bounds(page)
        s = 2.0
        pad = 30
        base = Image.new("RGB", (int((x1 - x0) * s) + 2 * pad, int((y1 - y0) * s) + 2 * pad), "white")
        tf = lambda x, y: ((x - x0) * s + pad, (y1 - y) * s + pad)  # noqa: E731
    ov = Image.new("RGBA", base.size, (0, 0, 0, 0))
    dr = ImageDraw.Draw(ov)
    order = ["IfcSpace", "IfcWall", "IfcOpeningElement", "IfcWindow", "IfcDoor", "IfcStair", "IfcAnnotation"]
    for cls in order:
        r, g, b = COLORS[cls]
        for e in [e for e in page["elements"] if e["ifc_class"] == cls]:
            geo = e["geometry_page"]
            if geo["type"] == "Polygon":
                pts = [tf(*p) for p in geo["coordinates"][0]]
                dr.polygon(pts, fill=(r, g, b, ALPHA.get(cls, 90)), outline=(r, g, b, 255))
                for hole in geo["coordinates"][1:]:
                    dr.polygon([tf(*p) for p in hole], fill=(0, 0, 0, 0), outline=(r, g, b, 255))
            elif geo["type"] == "LineString":
                dr.line([tf(*p) for p in geo["coordinates"]], fill=(r, g, b, 255), width=2)
            else:
                x, y = tf(*geo["coordinates"])
                dr.ellipse([x - 2, y - 2, x + 2, y + 2], fill=(r, g, b, 200))
            sw = e["properties"].get("swing") if isinstance(e.get("properties"), dict) else None
            if sw and sw.get("hinge_page") and sw.get("radius_page"):
                hx, hy = tf(*sw["hinge_page"])
                rr = sw["radius_page"] * (k or 2.0)
                a0, a1 = sw["arc_deg"]
                dr.arc([hx - rr, hy - rr, hx + rr, hy + rr], start=-a1, end=-a0, fill=(r, g, b, 255), width=2)
    img = Image.alpha_composite(base.convert("RGBA"), ov)
    if crop_to_overlay:
        x0, y0, x1, y1 = _bounds(page, skip_points=True)
        (ax, ay), (bx, by) = tf(x0, y1), tf(x1, y0)
        m = 30
        img = img.crop((max(0, int(ax) - m), max(0, int(ay) - m), min(img.width, int(bx) + m), min(img.height, int(by) + m + (60 if legend else 0))))
    if legend:
        d2 = ImageDraw.Draw(img)
        x = 8
        y = img.height - 22
        for cls in order:
            d2.rectangle([x, y, x + 12, y + 12], fill=COLORS[cls])
            d2.text((x + 16, y), cls[3:], fill=(0, 0, 0))
            x += 16 + 7 * len(cls[3:]) + 14
        d2.text((8, 6), f"ORI plan overlay p{page['page']} {page.get('page_label')} - auto-extracted, unreviewed - reviewer evidence, not approval",
                fill=(0, 0, 0))
    path = Path(path)
    img.convert("RGB").save(path, optimize=True)
    return path
