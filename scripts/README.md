# Offline tooling

Everything here runs outside the request path — nothing in `backend/` imports
any of it. This is where the numbers in `analysis/rules/tuning.py` came from,
and where you go to re-derive them.

| Script | Does |
|---|---|
| `load_phreshphish.py` | PhreshPhish parquet → `data/*.jsonl` |
| `split_by_domain.py` | split a JSONL into dev/test disjoint by registered domain |
| `eval_offline.py` | score a JSONL through the real rule engine → `runs/*.jsonl` |
| `eval_metrics.py` | precision/recall/AP/per-rule lift from a scored run |
| `calibrate_thresholds.py` | pick WARN and BLOCK from a scored dev split |
| `build_semantic_trainset.py` | PhreshPhish → the two CSVs Stage B trains on |
| `train_semantic_models.py` | fit and write the Stage B classifier pickles |
| `build_rule_features.py` | per-page rule-score vectors, for the meta-classifier |
| `train_meta_classifier.py` | meta-classifier vs weighted-average bake-off |
| `try_domain.py` | what the URL-only rules say about one domain |
| `create_admin.py` | create or promote an admin user in the local DB |

`create_admin.py` is the odd one out — an operational helper, not part of the
eval pipeline.

## Training the semantic classifiers

`train_semantic_models.py` writes the TF-IDF + logistic regression pipelines to
`backend/analysis/stages/stage_b/data/`. `scikit-learn` is in
`requirements.txt` (the runtime needs it to unpickle these), but `datasets` and
`pandas` are not — install them before training. Stage B falls back to keyword
heuristics when the artifacts are missing, so the backend still runs without
them.

```bash
python scripts/train_semantic_models.py --all
```

Train on page text, not email text. `build_semantic_trainset.py` exists because
the original classifiers were trained on email/SMS corpora and were near-random
on webpages; it runs PhreshPhish rows through the same
`FeatureExtractor` → `extract_semantic_text` path the classifier sees at
inference, and drops any domain present in the holdout file.

## The meta-classifier

`build_rule_features.py` emits one rule-score vector per page and
`train_meta_classifier.py` compares a model over those vectors against the
weighted average. The meta-classifier won and is now live whenever
`backend/analysis/data/meta_classifier.pkl` loads.

That artifact ships pre-built and **no script here regenerates it** — the
bake-off only reports. Rebuilding it means fitting on
`build_rule_features.py` output and pickling
`{"model": estimator, "features": [...]}` yourself.

# Evaluation pipeline

Measures how the full rule engine (Stage A deterministic + contextual, Stage B
semantic) performs on a static dataset of `(url, html, label)` records, without
running the proxy or touching the live SQLite DB.

## Pipeline

```
PhreshPhish parquet ──load_phreshphish──▶ data/<name>.jsonl ──eval_offline──▶ runs/<name>.jsonl ──eval_metrics──▶ report
```

Split with `split_by_domain.py` first if you are going to calibrate on one half
and report on the other.

## 1. Convert PhreshPhish to JSONL

After downloading the dataset, point the loader at the parquet shards:

```bash
python scripts/load_phreshphish.py \
    --parquet-glob "C:/path/to/phreshphish/test-*.parquet" \
    --output data/phreshphish_test.jsonl
```

Or stream from Hugging Face directly (~36 GB pull, slow):

```bash
python scripts/load_phreshphish.py --hf-split test --limit 5000 \
    --output data/phreshphish_test_5k.jsonl
```

If the script writes 0 rows it logs the first-row keys it saw — edit the
`_URL_CANDIDATES` / `_HTML_CANDIDATES` / `_LABEL_CANDIDATES` lists at the top
of `load_phreshphish.py` to match.

## 2. Score with AgentGuard

```bash
python scripts/eval_offline.py \
    --input data/phreshphish_test.jsonl \
    --output runs/phreshphish_test.jsonl \
    --workers 8 \
    --progress-every 500
```

Stage B (semantic classifier) is on by default. Pass `--no-stage-b` to
isolate Stage A.

**Speed.** Defaults to `lxml` HTML parsing (~5-10x faster than `html.parser`)
and `--workers = CPU-1` for parallelism. On an 8-core box expect a few hundred
records/sec, so 168k → roughly 15-45 minutes. Bumping `--workers` past your
physical core count rarely helps (the pipeline is CPU-bound, not I/O-bound).
Pass `--parser html.parser` if you want to mirror the production proxy
byte-for-byte (slower).

Output is one JSON per row:

```json
{"url": "...", "label": 1, "score": 0.74, "decision": "warn",
 "hard_block": false, "stage_b_ran": true,
 "triggered_rules": [{"rule_id": "sensitive_fields", "score": 1.0, "hard_block": false}, ...]}
```

## 3. Compute metrics

```bash
python scripts/eval_metrics.py --input runs/phreshphish_test.jsonl \
    --json runs/phreshphish_test.metrics.json
```

Reports:

- Average precision (area under PR curve) and ROC AUC — threshold-free
- Precision and FPR at recall = 0.9
- Confusion matrix at the production decision (Warn-or-Block, and Block-only)
- Confusion matrix at the tuned-for-R=0.9 threshold
- Per-rule contribution (fires on phish vs benign, TPR, FPR, lift) so you can
  see which rules carry the load

## Smoke test

A 3-row sample dataset is at `data/smoke.jsonl` (one benign Google page, one
HTTP-IP-URL phish, one typo-squat).

```bash
python scripts/eval_offline.py --input data/smoke.jsonl --output runs/smoke.jsonl
python scripts/eval_metrics.py --input runs/smoke.jsonl
```

Expect AP = 1.0, both phishing rows blocked at 0.1966 and 0.2247, firing
`unencrypted_connection`, `external_form_action`, `ip_based_url` and
`suspicious_tld`.

The benign row is the interesting one: it warns at 0.0433 with **no rule
triggered at all**. Sub-threshold Stage B probabilities still enter the
weighted average, and WARN is only 0.04 — so a page can cross the line with
nothing to show for it. Three rows is too few to conclude anything, but it is a
fair illustration of what the low thresholds cost.

## Methodology caveats (read before quoting numbers)

This pipeline does **not** by itself give you a publishable evaluation. Some
gaps you should close before presenting numbers as "AgentGuard's accuracy":

1. **No temporal split.** The PhreshPhish test split is already separated
   from train, but this harness doesn't enforce that. If you build a custom
   dataset, partition by capture time, not at random.

2. **Domain disjointness is opt-in.** `split_by_domain.py` and
   `build_semantic_trainset.py --holdout-jsonl` enforce it; nothing else does.
   Skip them and a rule that memorizes a domain will look better than it is.

3. **Base rates.** Real-world phishing is ~0.05–1% of traffic, not 50%.
   PhreshPhish includes benchmark splits at realistic base rates — use those
   for any number you want to publish.

4. **Don't lead with accuracy.** Average precision, P@R=target, and FPR at
   the recall you want to ship at are what matter for a phishing detector.

5. **The tuning numbers are from one dataset.** Everything in
   `analysis/rules/tuning.py` was calibrated on PhreshPhish. The per-rule lift
   figures quoted there are properties of that eval slice, not of the web.
