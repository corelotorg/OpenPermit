# Public site routes and repository source

Canonical repository: https://github.com/corelotorg/OpenPermit, branch `test`.

`site/routes.json` owns the route-to-repository mapping. `site/build.py` creates a static artifact using versioned sources. All site links use relative paths so the same tree works under GitHub project Pages at `/OpenPermit/` and at the root of a custom domain.

| Site route | Repository content |
|---|---|
| `/` | `index.html` |
| `/docs/` | Charter, governance and implementation guides |
| `/spec/` | ORI specifications, JSON schemas and discovery |
| `/benchmark/` | Synthetic IFC cases and expected reports |
| `/contribute/` | Contribution, governance, licenses and issue tracker |
| `/model-verification/` | Assembly and evidence acceptance scope |
| `/.well-known/ori.json` | Machine-readable discovery |
| `/llms.txt` | Source-oriented discovery index |

Build and check:

```bash
python site/build.py --out _site --base-url https://corelotorg.github.io/OpenPermit/
python site/check.py _site
python -m unittest discover -s site -p 'test_*.py'
```

The existing Pages deployment publishes the repository root. Generated route index pages, robots.txt and sitemap.xml are therefore committed at that root. Run `python site/publish_routes.py` after changing route sources; CI runs `python site/publish_routes.py --check` and rejects stale or missing copies. The site workflow also uploads a checked artifact for review. It does not switch Pages settings, custom domains or DNS, and does not deploy a reference node. `/mcp` and `/health` are runtime routes, not static-site endpoints. Domain ownership, DNS, TLS, deployed site revision, and runtime authentication each require separate live receipts before cutover.

For a custom-domain deployment, rebuild with that verified domain as `--base-url` so sitemap and robots URLs match. Schema `$id` values remain stable identifiers and do not prove hosted availability.
