# DOI deposit — everything is prepared; 3 clicks remain (account required)

> **Maintainer decision (2026-07-12): minting deferred** until a venue requires it
> (`VENUE_PLAN.md`). The hash-manifested GitHub releases remain the citable artifact reference;
> everything below stays ready.

Status (2026-07-18, bundle refreshed to **v1.1** — adds Office V3 + FIR-breadth prereg/results docs and adjudicators, the pinned-parity chain, the TORS PDF, the completed Office HSTU-BLaIR reference-run artifacts, and the extended 153-file RELEASE_MANIFEST; built reproducibly by `_bestrec_run/build_deposit_bundle.py`): the deposit is **fully assembled locally**. A DOI itself can only be minted
by an archive under your account — that is the single step that cannot be done from this machine
without your login. Everything else is done:

| prepared artifact | where |
|---|---|
| Deposit bundle (65 entries: papers incl. TORS PDF, all preregs + results docs, manifests, audit chain, code incl. adjudicators, comparator-run artifacts, README) | GitHub release **`v1.1.8-deposit`** asset `bestrec_deposit_v1.1.8.zip` (SHA256 in the sidecar asset `bestrec_deposit_v1.1.8.zip.sha256` and in `_release/` locally; bundle-internal `SHA256SUMS.txt` covers every payload entry (not itself); upload verified by a download-hash round trip). Prior deposit tags (`v1.1.7-deposit` and earlier) remain as dated snapshots, each superseded by the next. Superseded: `v1.1-deposit` (its uploaded assets went stale against later same-day commits — see RESPONSE_TO_PAPER_REVIEW_AUDIT.md, 2026-07-18 01:10). Historical: `v1.0-deposit` / `bestrec_deposit_v1.0.zip` (46 files, SHA256 `8fd3eb58e35e695d910b960b4cacf85c50e23e6ff77ec0a637953655f1d08770`) remains as the 2026-07-11 snapshot. |
| Zenodo metadata (title, creators, license, keywords, description) | `.zenodo.json` (repo root — Zenodo's GitHub integration reads it automatically) |
| Citation metadata | `CITATION.cff` (GitHub renders a "Cite this repository" button from it) |
| Code/docs license with dataset + vendored-code scope notes | `LICENSE` (MIT — swap before minting if you prefer another) |
| Hashes for the large artifacts NOT in the bundle (splits, caches, 51 result JSONs) + submission docs/PDF/parity artifacts | `RELEASE_MANIFEST.json` (self-policing: verified against the tree by `rebuild_hstu_submission.py --strict` at every rebuild) + the `v0.9-audit-evidence` release assets |

## Option A — Zenodo GitHub integration (recommended, ~3 clicks)

1. Log in at https://zenodo.org with your GitHub account → **GitHub** page
   (https://zenodo.org/account/settings/github/) → flip the toggle ON for
   `Ray0419/bestrec-sota-results`.
2. Publish any **new** release (Zenodo archives releases created *after* the toggle; re-tagging
   the current deposit tag with a bumped patch version is enough — or ask me and I'll cut it).
3. Zenodo mints a **version DOI + a concept DOI** within minutes, using `.zenodo.json` for
   metadata. Done.

**Hash-check rule (line endings):** when verifying, always hash the **tag blob**
(`git show <tag>:FILE`), the **release asset**, or the **bundle payload** — never the local
worktree copy. A pre-`.gitattributes` Windows checkout can hold CRLF worktree bytes for
LF-pinned files, so `Get-FileHash` on a worktree file may legitimately differ from the
byte-identical tag/asset/bundle trio.

## Option B — Zenodo manual upload (no GitHub linking)

1. https://zenodo.org/uploads/new → upload the **current** bundle `bestrec_deposit_v1.1.8.zip` from the `v1.1.8-deposit`
   release assets. A local `_release/` copy is safe ONLY if its SHA256 matches the release
   sidecar for the named tag (a post-tag rebuild can differ); when in doubt, use the
   downloaded release asset.
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
