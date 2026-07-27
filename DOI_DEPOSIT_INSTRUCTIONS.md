# DOI/deposit candidate — do not publish before metadata verification

Status as of 2026-07-28: `v1.2.0` is an **unpublished local candidate**, not an
existing Git tag, GitHub release, archive record, or DOI. The historical
`v1.1.11-deposit` tag remains provenance only and is stale relative to the
current manuscript. Do not upload or retag it as current.

The deterministic candidate bundle is
`_release/bestrec_deposit_v1.2.0.zip` (92 entries: 90 tracked
payloads plus `README_DEPOSIT.txt` and `SHA256SUMS.txt`) and has an adjacent
`.sha256` sidecar. Rebuild it with:

```powershell
python _bestrec_run/build_deposit_bundle.py --candidate
```

Candidate mode validates current metadata, bundle inventory, manifest hashes,
and worktree content, but deliberately does not require or create a tag. Normal
mode remains fail-closed and is reserved for rebuilding the exact final tagged
tree.

## Publication blockers

Before any tag, release, upload, or DOI mint:

1. replace `CREATOR METADATA REQUIRED BEFORE PUBLICATION` in `.zenodo.json` and
   `CITATION.cff` with legal author metadata matching the manuscript;
2. fill all bracketed author/affiliation/COI/reviewer/preprint fields in the
   manuscript and `COVER_LETTER_TORS.md`;
3. verify the selected code license and the redistribution/takedown position for
   derived Amazon Reviews assets;
4. rebuild both PDFs and run the strict and clean-clone gates;
5. regenerate `RELEASE_MANIFEST.json` with the final intended tag;
6. build the bundle in candidate mode, inspect it, commit, then create the tag;
7. rebuild in normal mode at that exact tag and compare the zip hash; and
8. only then upload to GitHub/Zenodo or OSF through the maintainer's authenticated
   account.

## Final publication procedure

### Zenodo GitHub integration

1. Enable Zenodo's GitHub integration for the repository under the maintainer's
   authenticated account.
2. Create the final versioned GitHub release only after the final-tag gate passes.
3. Confirm that Zenodo imported the verified creator/title/license metadata and
   the exact release asset.
4. After minting, record both the version DOI and concept DOI in the manuscript,
   README, `.zenodo.json`, and `CITATION.cff`, then rebuild once more.

### Manual Zenodo/OSF upload

Upload only the zip whose SHA-256 equals its committed/tagged sidecar. Paste the
verified metadata; never use the placeholder candidate metadata. Preserve the
bundle-internal `SHA256SUMS.txt`.

## Verification boundaries

- `RELEASE_MANIFEST.json` pins the repository/public-asset evidence boundary.
- `SHA256SUMS.txt` pins exactly the payload bytes inside the candidate zip.
- The adjacent `.zip.sha256` pins the outer zip.
- For text files, compare the tag blob or LF-normalized bundle payload, not raw
  CRLF worktree bytes on Windows.
- A candidate build is preparation only. It is not a claim that an archival
  record or DOI exists.
