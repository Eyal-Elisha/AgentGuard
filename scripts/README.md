# Offline evaluation pipeline

Three scripts that together let you measure how AgentGuard's full rule engine
(Stage A deterministic + contextual + Stage B semantic classifier) performs on
a static dataset of `(url, html, label)` records, *without* needing to run the
proxy or write to the live SQLite DB.

## Pipeline

```
PhreshPhish parquet ──load_phreshphish──▶ data/<name>.jsonl ──eval_offline──▶ runs/<name>.jsonl ──eval_metrics──▶ report
```

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
    --output runs/phreshphish_test.jsonl
```

Stage B (semantic classifier) is on by default. Pass `--no-stage-b` to
isolate Stage A.

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
HTTP-IP-URL phish, one typo-squat). Running the full pipeline on it should
print AP=1.0 and identify `unencrypted_connection`, `sensitive_fields`,
`brand_domain_mismatch` as the firing rules.

```bash
python scripts/eval_offline.py --input data/smoke.jsonl --output runs/smoke.jsonl
python scripts/eval_metrics.py --input runs/smoke.jsonl
```

## Methodology caveats (read before quoting numbers)

This pipeline does **not** by itself give you a publishable evaluation. Some
gaps you should close before presenting numbers as "AgentGuard's accuracy":

1. **No temporal split.** The PhreshPhish test split is already separated
   from train, but this harness doesn't enforce that. If you build a custom
   dataset, partition by capture time, not at random.

2. **No domain-disjoint check between train and test.** If you ever retrain
   anything on PhreshPhish, dedupe by registered domain across splits.

3. **Stage B classifiers were trained on email/SMS text**, not webpage HTML.
   Running them on PhreshPhish HTML is an out-of-distribution test; that's
   often the more interesting story, but flag it.

4. **Base rates.** Real-world phishing is ~0.05–1% of traffic, not 50%.
   PhreshPhish includes benchmark splits at realistic base rates — use those
   for any number you want to publish.

5. **Don't lead with accuracy.** Average precision, P@R=target, and FPR at
   the recall you want to ship at are what matter for a phishing detector.
