# DOI deposit — everything is prepared; 3 clicks remain (account required)

Status (2026-07-11): the deposit is **fully assembled locally**. A DOI itself can only be minted
by an archive under your account — that is the single step that cannot be done from this machine
without your login. Everything else is done:

| prepared artifact | where |
|---|---|
| Deposit bundle (46 files: papers, preregs, manifests, audit chain, code, comparator-run artifacts, README) | GitHub release **`v1.0-deposit`** asset `bestrec_deposit_v1.0.zip` (SHA256 `8fd3eb58e35e695d910b960b4cacf85c50e23e6ff77ec0a637953655f1d08770`) |
| Zenodo metadata (title, creators, license, keywords, description) | `.zenodo.json` (repo root — Zenodo's GitHub integration reads it automatically) |
| Citation metadata | `CITATION.cff` (GitHub renders a "Cite this repository" button from it) |
| Code/docs license with dataset + vendored-code scope notes | `LICENSE` (MIT — swap before minting if you prefer another) |
| Hashes for the large artifacts NOT in the bundle (splits, caches, 51 result JSONs) + submission docs/PDF/parity artifacts | `RELEASE_MANIFEST.json` (self-policing: verified against the tree by `rebuild_hstu_submission.py --strict` at every rebuild) + the `v0.9-audit-evidence` release assets |

## Option A — Zenodo GitHub integration (recommended, ~3 clicks)

1. Log in at https://zenodo.org with your GitHub account → **GitHub** page
   (https://zenodo.org/account/settings/github/) → flip the toggle ON for
   `Ray0419/bestrec-sota-results`.
2. Publish any **new** release (Zenodo archives releases created *after* the toggle; re-tagging
   `v1.0-deposit` as `v1.0.1-deposit` is enough — or ask me and I'll cut it).
3. Zenodo mints a **version DOI + a concept DOI** within minutes, using `.zenodo.json` for
   metadata. Done.

## Option B — Zenodo manual upload (no GitHub linking)

1. https://zenodo.org/uploads/new → upload `bestrec_deposit_v1.0.zip` (from the
   `v1.0-deposit` release assets, or `_release/` locally).
2. Paste the metadata from `.zenodo.json` (title/creators/description/keywords/license).
3. Publish → DOI minted.

## Option C — OSF

1. https://osf.io → new project → OSF Storage → upload the zip.
2. Enable the DOI in project settings ("Create DOI").

## After the DOI exists — tell me the DOI string and I will:

- add the `Code and Data Availability` DOI line to both papers (§8) and re-render the PDF,
- add the DOI badge to `CITATION.cff` (`doi:` field) and the README,
- update `RESPONSE_TO_RESUBMISSION_AUDIT_2026-07-11.md` Repair-#9 row from
  "DONE (DOI = user decision)" to fully closed with the identifier,
- commit + push the finished package.

## Why a DOI can't be minted from here

Zenodo/OSF mint DOIs only inside an authenticated account (ownership, takedown responsibility,
metadata stewardship). No API token for either service exists on this machine, and creating one
requires your login. The preparation above reduces your part to authentication + one publish
click.
