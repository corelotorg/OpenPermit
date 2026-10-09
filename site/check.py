#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Check local page targets, fragments, canonical repository links and route coverage."""
import json
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.links, self.ids = [], set()
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id"):
            self.ids.add(attrs["id"])
        for key in ("href", "src"):
            if attrs.get(key):
                self.links.append(attrs[key])


def check(root):
    errors = []
    repo = Path(__file__).resolve().parents[1]
    routes = json.loads((repo / "site/routes.json").read_text())
    for route in routes["routes"]:
        if not (root / route["path"] / "index.html").is_file():
            errors.append(f'missing route: {route["path"]}')
    for path in root.rglob("*.html"):
        for href in Page(path.read_text()).links:
            url = urlsplit(href)
            if url.scheme or url.netloc:
                if url.netloc == "github.com" and any(x in url.path.lower() for x in ["/sheetpros/openpermit", "/jeremiahhorstick/openpermit"]):
                    errors.append(f"stale repository CTA: {href}")
                continue
            if url.path.startswith("/"):
                errors.append(f"root-relative route breaks project Pages: {href}")
                continue
            target = (path.parent / unquote(url.path)).resolve() if url.path else path.resolve()
            if not target.is_relative_to(root.resolve()):
                errors.append(f"outside site: {href}")
                continue
            if target.is_dir():
                target /= "index.html"
            if not target.is_file():
                errors.append(f"missing target in {path.relative_to(root)}: {href}")
            elif url.fragment and target.suffix == ".html" and unquote(url.fragment) not in Page(target.read_text()).ids:
                errors.append(f"missing fragment: {href}")
    return errors


if __name__ == "__main__":
    errors = check(Path(sys.argv[1] if len(sys.argv) > 1 else "_site"))
    for error in errors:
        print("FAIL", error)
    print(f'{"FAIL" if errors else "PASS"} public site links and routes')
    sys.exit(bool(errors))
