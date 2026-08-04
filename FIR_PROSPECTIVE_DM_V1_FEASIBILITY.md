# Digital Music prospective V1 feasibility result

Protocol: `PREREG_FIR_PROSPECTIVE_DM_V1_SELECTION`

Mechanical verdict: **`DM-V1-FEASIBILITY-VOID`**.

The stage-A freeze was committed and pushed at Git commit `043a120c` before
acquisition. The two revision-pinned upstream objects matched their frozen
byte counts and SHA-256 digests. After earliest-event `(user,item)`
deduplication, the raw review file contained 128,763 interactions. Recursive
5-core filtering then produced:

| pass | retained interactions | retained users | retained items |
|---:|---:|---:|---:|
| 1 | 2,236 | 1,419 | 3,663 |
| 2 | 153 | 120 | 47 |
| 3 | 8 | 9 | 7 |
| 4 | 0 | 0 | 0 |

The frozen minimums of 1,000 users, 1,000 items, and 10,000 interactions all
fail. No Digital Music embedding, model training, validation trajectory, TEST
ranking, or scientific endpoint was computed. V1 permits no fallback category
or relaxed preprocessing. It is therefore closed as a transparent feasibility
failure, not interpreted as evidence for or against the FIR method.

Machine-readable evidence:

- `_bestrec_run/digital_music_acquisition_manifest.json`
- `_bestrec_run/digital_music_feasibility.json`
