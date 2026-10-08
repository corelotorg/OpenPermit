# SPDX-License-Identifier: Apache-2.0
"""Write tiny synthetic vector PDFs for tests and examples (no external dependency).

Each page is 1224 x 792 pt (17 x 11 in, ANSI B) with Helvetica text lines. An
optional XMP packet can carry a PDF/A identification claim so the manifest's
claim detection can be tested. The files are synthetic and are not plan sets
for any real building. They are not PDF/A-conformant even when they claim to be.
"""

from __future__ import annotations

from pathlib import Path


def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def make_text_pdf(path: str | Path, pages: list[list[str]], pdfa_claim: tuple[int, str] | None = None,
                  page_labels: list[str] | None = None) -> Path:
    objs: list[bytes] = []

    def add(b: bytes) -> int:
        objs.append(b)
        return len(objs)

    font = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    page_ids, content_ids = [], []
    pages_id_placeholder = len(objs) + 1 + 2 * len(pages)  # computed below
    for lines in pages:
        ops = ["BT", "/F1 14 Tf", "72 720 Td", "18 TL"]
        for ln in lines:
            ops.append(f"({_esc(ln)}) Tj T*")
        ops.append("ET")
        stream = "\n".join(ops).encode("latin-1")
        cid = add(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")
        content_ids.append(cid)
        pid = add(b"PAGE_PLACEHOLDER")
        page_ids.append(pid)
    pages_id = add(b"PAGES_PLACEHOLDER")
    assert pages_id == pages_id_placeholder
    for cid, pid in zip(content_ids, page_ids):
        objs[pid - 1] = (b"<< /Type /Page /Parent %d 0 R /MediaBox [0 0 1224 792] /Contents %d 0 R "
                         b"/Resources << /Font << /F1 %d 0 R >> >> >>" % (pages_id, cid, font))
    kids = b" ".join(b"%d 0 R" % p for p in page_ids)
    objs[pages_id - 1] = b"<< /Type /Pages /Kids [%s] /Count %d >>" % (kids, len(page_ids))
    extra = b""
    if pdfa_claim:
        part, conf = pdfa_claim
        xmp = ('<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?><x:xmpmeta xmlns:x="adobe:ns:meta/">'
               '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"><rdf:Description rdf:about="" '
               f'xmlns:pdfaid="http://www.aiim.org/pdfa/ns/id/"><pdfaid:part>{part}</pdfaid:part>'
               f'<pdfaid:conformance>{conf}</pdfaid:conformance></rdf:Description></rdf:RDF></x:xmpmeta>'
               '<?xpacket end="w"?>').encode()
        mid = add(b"<< /Type /Metadata /Subtype /XML /Length %d >>\nstream\n" % len(xmp) + xmp + b"\nendstream")
        extra += b" /Metadata %d 0 R" % mid
    if page_labels:
        nums = b" ".join(b"%d << /P (%s) >>" % (i, _esc(l).encode("latin-1")) for i, l in enumerate(page_labels))
        extra += b" /PageLabels << /Nums [%s] >>" % nums
    catalog = add(b"<< /Type /Catalog /Pages %d 0 R%s >>" % (pages_id, extra))
    out = bytearray(b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for i, body in enumerate(objs, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    for off in offsets:
        out += b"%010d 00000 n \n" % off
    out += b"trailer\n<< /Size %d /Root %d 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, catalog, xref)
    path = Path(path)
    path.write_bytes(bytes(out))
    return path
