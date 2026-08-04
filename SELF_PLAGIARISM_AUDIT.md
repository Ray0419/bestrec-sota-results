# Self-Plagiarism And Text-Reuse Audit

**Audit time:** 2026-06-08 12:31:01 +10:00

## Verdict

No local long-phrase reuse was detected between the old BEST-Rec PDF and the
new LC2C Retrieval LTR paper draft. This is not a full external plagiarism
clearance, because I can only compare files present in the workspace or public
texts explicitly fetched for review.

## Local Check Performed

Compared:

- `BERT-Embedded Self-attention Transformer Recommender (BEST-Rec)_ Tackling Sparsity and Cold-Starts.pdf`
- `_bestrec_sota_lab/paper_draft/lc2c_retrieval_ltr_paper.md`

Method:

- Extracted old PDF text with `pypdf`.
- Lowercased and tokenized both documents.
- Checked exact overlapping normalized n-grams of lengths 8, 10, 12, and 15.

Result:

| N-gram length | Unique exact overlaps |
|---:|---:|
| 8 | 0 |
| 10 | 0 |
| 12 | 0 |
| 15 | 0 |

## Limitations

- This does not compare against every external paper.
- This does not detect paraphrase-level plagiarism.
- This does not verify that every borrowed idea is cited; that is covered
  separately in `CITATION_AUDIT.md` and `_bestrec_run/CITATIONS.md`.
- The old PDF extraction produced `pypdf` xref warnings, but still extracted
  99,376 characters and 14,631 normalized tokens.

## Required Before Submission

- Run a venue-appropriate external plagiarism/similarity checker on the final
  PDF.
- Keep the explicit attribution paragraphs in the manuscript.
- Avoid recycling introduction/background paragraphs from the old BEST-Rec PDF.

