#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Materialize generated routes for the existing repository-root Pages source."""
import argparse
import importlib.util
import json
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def publish(check=False):
    spec = importlib.util.spec_from_file_location("site_builder", ROOT / "site/build.py")
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    routes = json.loads((ROOT / "site/routes.json").read_text())["routes"]
    paths = [r["path"] + "index.html" for r in routes] + ["robots.txt", "sitemap.xml"]
    stale = []
    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp)
        builder.build(output, "https://corelotorg.github.io/OpenPermit/")
        for path in paths:
            source, target = output / path, ROOT / path
            if check:
                if not target.is_file() or target.read_bytes() != source.read_bytes():
                    stale.append(path)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
    if stale:
        raise SystemExit("Stale published routes: " + ", ".join(stale) + "; run python site/publish_routes.py")
    print("Published route copies match" if check else "Published route copies updated")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    publish(parser.parse_args().check)
