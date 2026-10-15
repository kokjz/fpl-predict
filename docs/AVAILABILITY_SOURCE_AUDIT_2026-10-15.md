# Historical availability source audit — 15 October 2026

The inspected AIrsenal archive provides useful **pre-deadline Git-history
evidence** for the declared 11-GW sample. This admits a source research route,
not a learned availability model, a prediction-accuracy claim or an automatic
change to the approved champion.

## Method

Pinned AIrsenal revision `212a0aa478fe885808355dc5f08f81f8f9822893` contains
`src/airsenal/data/player_attributes_history_2526.csv`:23,271,124bytes, Git blob
`74829dc09b97143eb0aefbdf4cfb0721359d183a`. Downloaded once with a25MB/180s cap,
verified the Git blob and SHA256, and retained6,925,164compressed bytes. No
repository clone, model weights, external code execution or dataset redistribution.

The exporter records a naive `datetime.now()` clock. The workflow uses a hosted
runner but that alone is not sufficient proof of the clock's timezone. Instead:

1. Query the original pre-rename CSV path for the last Git commit strictly before
   each independently checked FPL deadline.
2. Obtain that historical file's byte size and Git blob ID.
3. Hash exactly that prefix of the retained current CSV, including the Git blob
   header. All11prefixes match. Thus these exact byte sequences occur in Git
   commits bearing pre-deadline dates; no historical duplicate CSVs are needed.
4. Select the last complete append group, verify declared season/GW and stable
   Opta-code/FPL-element/position joins against an independent bootstrap capture.
   Use **commit publication time** as the conservative availability boundary;
   retain naive source clocks without inventing UTC offsets.

Git dates/history remain publisher evidence rather than independently certified
capture times. A matching hash is an integrity check, not proof against rewritten
or backdated repository history. Source observations can change between two
different captures; identity/deadline agreement does not imply news text equality.

## Declared sample and findings

Sample fixed before field inspection:2025/26GW4,20–28,38, covering the first
reported historical coverage, the recent validation window, evaluation start and
season end. It is **not** a complete all-season source audit. Across8,823rows,
all stable codes/elements/positions match the independent captures; zero identity
conflicts or missing source-to-bootstrap identities in this sample.

| GW | Latest published group rows | Publication lead before deadline(hours) | Known chance labels | Nonempty news |
| --- | ---: | ---: | ---: | ---: |
| 4 | 738 | 0.772 | 273 | 206 |
| 20 | 780 | 1.755 | 505 | 294 |
| 21 | 790 | 9.240 | 512 | 292 |
| 22 | 796 | 1.766 | 535 | 287 |
| 23 | 802 | 1.761 | 547 | 281 |
| 24 | 808 | 4.236 | 558 | 279 |
| 25 | 817 | 9.088 | 568 | 303 |
| 26 | 817 | 8.503 | 582 | 315 |
| 27 | 817 | 4.221 | 588 | 309 |
| 28 | 818 | 9.102 | 591 | 315 |
| 38 | 840 | 3.738 | 630 | 292 |

Totals:5,889known chance labels and3,173nonempty news observations. Missing chance
is unknown, not100%; empty captured news is not a healthy/start probability.
Return-gameweek is a provider-derived field with its own assumptions, not a
verified future return. No points/minutes outcomes select rows or verify news.

## Repeatable offline command

`fpl-predict audit-availability --archive private/source.csv.gz --proof
private/proof.json --output private/new-audit.json` performs no network access,
training, runtime initialisation or registry changes. Output is write-once and
aggregate-only. Input/decompression sizes are bounded; duplicate identities,
checksum/deadline/position conflicts and publication at/after deadline fail closed.

Proof JSON has `scope` and `records`. Each record supplies `gameweek,deadline,
published_at,commit,size,git_blob_sha1,bootstrap_path,bootstrap_sha256` from actual
independently retrieved sources. Bootstrap may be JSON or bounded xz JSON. Hashes
cover exact supplied bytes. The audit does not obtain or authenticate remote
metadata itself: retain source URLs/retrieval dates and review them separately.
The pure `admit_prefix` helper also returns raw selected observations for a
separately reviewed private adapter; no chance labels become calibrated probabilities.

| Retained evidence | SHA256 |
| --- | --- |
| Raw CSV | `b6f95fc1d91add8d71fbc17c3f562ab567243f1d6552818db689f8369707210f` |
| Retained gzip | `61229a6ee72c5897994141d77acca959f1b557238214d603f20f2c0af8f190ea` |
| Aggregate audit | `50e8d607f957dfe2dd7d6126be58f7e0fc4ad5688e013b8b07b97dec3af8283a` |

## Consequence for the work plan

A future availability experiment can use explicitly verified observations, but
must first expand admission to **every required training/evaluation GW**, preserve
unknowns and source revisions, and freeze a new development protocol. Coverage
starts September2025, so it cannot be silently added to the older I4 folds or
make older seasons fully observed. I4 remains stopped with no finalist. No
availability-dependent fit or new current-season prediction was run here.

Source project declares an MIT software licence. Underlying FPL data rights and
redistribution permissions are separate; no general dataset licence conclusion
or raw-data redistribution follows from this audit.

## Primary sources

- [AIrsenal pinned exporter](https://github.com/alan-turing-institute/AIrsenal/blob/212a0aa478fe885808355dc5f08f81f8f9822893/src/airsenal/export/attributes.py)
- [Daily export workflow](https://github.com/alan-turing-institute/AIrsenal/blob/212a0aa478fe885808355dc5f08f81f8f9822893/.github/workflows/attributes.yml)
- [Source loader/coverage declaration](https://github.com/alan-turing-institute/AIrsenal/blob/212a0aa478fe885808355dc5f08f81f8f9822893/src/airsenal/ingest/attributes_history.py)
- [Historical GW20 pre-deadline commit](https://github.com/alan-turing-institute/AIrsenal/commit/0892d46dbd4384de50504b542a6731df33dfb637)
- [Source software licence](https://github.com/alan-turing-institute/AIrsenal/blob/212a0aa478fe885808355dc5f08f81f8f9822893/LICENSE)


## Subsequent complete experimental-window admission

A later [fixed news/availability experiment](NEWS_AVAILABILITY_RESULTS_2026-10-16.md) expanded the exact-prefix/bootstrap method to every GW4–38 required by that experiment. The eleven-week sample above remains the original frozen audit. The later report retains all35prefix records, cohort gaps and source limitations; source admission remains separate from model promotion.
