#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Build static public routes from versioned sources; no runtime service is deployed."""
import argparse
import html
import json
import shutil
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]


def build(out, base_url):
    out = out.resolve()
    # Refuse a destination that can overwrite sources or recursively copy itself.
    if out == ROOT or ROOT.is_relative_to(out):
        raise ValueError("output must not contain the repository")
    routes = json.loads((ROOT / "site/routes.json").read_text())
    out.mkdir(parents=True, exist_ok=True)
    for name in ["index.html", "README.md", "CHARTER.md", "GOVERNANCE.md", "CONTRIBUTING.md", "CREDITS.md", "NOTICE.md", "LICENSE", "LICENSE-SPEC.md", "SECURITY.md", "llms.txt", ".nojekyll"]:
        src = ROOT / name
        if src.exists():
            shutil.copy2(src, out / name)
    for name in ["spec", "profiles", "rules", "docs", "conformance", "verification/examples", ".well-known", "LICENSES"]:
        src = ROOT / name
        for path in sorted(src.rglob("*")):
            if path.is_file() and path.suffix not in {".py", ".pyc"} and "__pycache__" not in path.parts:
                target = out / path.relative_to(ROOT)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, target)
    # Benchmark documentation lives outside examples.
    (out / "verification").mkdir(exist_ok=True)
    shutil.copy2(ROOT / "verification/README.md", out / "verification/README.md")
    for route in routes["routes"]:
        path = Path(route["path"])
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("route must stay within site")
        target = out / path / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        prefix = "../" * len(path.parts)
        links = []
        for source in route["links"]:
            if not (out / source).is_file():
                raise ValueError(f"route {path}: missing source {source}")
            repo_url = f'{routes["repository"]}/blob/{routes["branch"]}/{quote(source)}'
            links.append(f'<li><a href="{html.escape(repo_url)}">{html.escape(source)}</a> · <a href="{prefix}{html.escape(quote(source))}">file</a></li>')
        title = html.escape(route["title"])
        target.write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{title} · OpenPermit</title><style>body{{background:#10151b;color:#e8edf2;font:18px/1.6 system-ui;max-width:960px;margin:5vh auto;padding:24px}}a{{color:#8dccff}}li{{margin:12px 0}}</style>'
            f'<nav><a href="{prefix}">OpenPermit</a> · <a href="{html.escape(routes["repository"])}">Repository</a></nav>'
            f'<main><h1>{title}</h1><p>{html.escape(route["description"])}</p><ul>{"".join(links)}</ul>'
            f'<p><a href="{html.escape(routes["repository"])}/issues">Report an issue</a></p></main></html>\n')
    base = base_url.rstrip("/") + "/"
    urls = [base] + [base + r["path"] for r in routes["routes"]]
    (out / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + ''.join(f'<url><loc>{html.escape(u)}</loc></url>' for u in urls) + '</urlset>\n')
    (out / "robots.txt").write_text(f'User-agent: *\nAllow: /\n\nSitemap: {base}sitemap.xml\n')
    return len(routes["routes"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=ROOT / "_site")
    parser.add_argument("--base-url", default="https://corelotorg.github.io/OpenPermit/")
    args = parser.parse_args()
    print(f"Built {build(args.out, args.base_url)} public routes")
