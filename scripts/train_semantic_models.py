"""Train TF-IDF + Logistic Regression classifiers for Stage B semantic rules.

This script materializes the pickle artifacts in
`backend/analysis/stages/stage_b/data/` consumed by
`SemanticClassifier`. Each artifact is a scikit-learn `Pipeline` whose final
step is a binary `LogisticRegression(classes_=[0, 1])`.

Datasets used:

* Phishing classifier:
  - HuggingFace `ealvaradob/phishing-dataset` (`combined_reduced` config — text/label).
  - The Kaggle `naserabdullahalam/phishing-email-dataset` from the spec is not
    on HuggingFace; pass it via --benign-csv / --malicious-csv if you want to
    fold it in.
* Prompt-injection classifier (binary; HF sources are positives-only, so we
  pair them with a public benign-instructions corpus):
  - Positives: `imoxto/prompt_injection_cleaned_dataset` (uses `user_input`)
               + `yanismiraoui/prompt_injections`.
  - Benign:    `databricks/databricks-dolly-15k` (instructions only).

Dependencies (install before running): `scikit-learn`, `datasets`, `pandas`.

CLI:

    python scripts/train_semantic_models.py --all
    python scripts/train_semantic_models.py --rule phishing_language
    python scripts/train_semantic_models.py --rule prompt_injection \\
        --benign-csv path/to/benign.csv --malicious-csv path/to/malicious.csv

When `--benign-csv` and `--malicious-csv` are passed, the script reads them
directly (expects a `text` column) — useful in environments without internet
access. Otherwise it pulls the public datasets via `datasets.load_dataset`.
"""

from __future__ import annotations

import argparse
import logging
import pickle
import sys
from pathlib import Path
from typing import Iterable, List, Tuple

_logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parent.parent
_MODEL_DIR = _REPO_ROOT / "backend" / "analysis" / "stages" / "stage_b" / "data"
_MIN_PER_CLASS = 50  # refuse to train if either class has fewer samples than this


def _build_pipeline():
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline

    return Pipeline([
        ("tfidf", TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 2),
            min_df=2,
            max_df=0.95,
            max_features=50_000,
            sublinear_tf=True,
        )),
        ("clf", LogisticRegression(
            solver="liblinear",
            class_weight="balanced",
            C=1.0,
            max_iter=1000,
        )),
    ])


def _train_and_save(model_id: str, texts: List[str], labels: List[int]) -> Path:
    from sklearn.metrics import classification_report
    from sklearn.model_selection import train_test_split

    pos = sum(1 for label in labels if label == 1)
    neg = len(labels) - pos
    if pos < _MIN_PER_CLASS or neg < _MIN_PER_CLASS:
        raise RuntimeError(
            f"Need at least {_MIN_PER_CLASS} samples per class for {model_id} "
            f"(got benign={neg}, malicious={pos})"
        )

    x_train, x_test, y_train, y_test = train_test_split(
        texts, labels, test_size=0.2, random_state=42, stratify=labels,
    )

    pipeline = _build_pipeline()
    pipeline.fit(x_train, y_train)

    _logger.info("[%s] hold-out report:\n%s", model_id,
                 classification_report(y_test, pipeline.predict(x_test), digits=3))

    _MODEL_DIR.mkdir(parents=True, exist_ok=True)
    out = _MODEL_DIR / f"{model_id}.pkl"
    with out.open("wb") as fh:
        pickle.dump(pipeline, fh)
    _logger.info("[%s] saved → %s", model_id, out)
    return out


def _read_csv_pair(benign_csv: Path, malicious_csv: Path) -> Tuple[List[str], List[int]]:
    import pandas as pd

    benign = pd.read_csv(benign_csv)
    malicious = pd.read_csv(malicious_csv)
    if "text" not in benign.columns or "text" not in malicious.columns:
        raise ValueError("Both CSVs must include a 'text' column")
    texts = [str(t) for t in benign["text"].tolist()] + [str(t) for t in malicious["text"].tolist()]
    labels = [0] * len(benign) + [1] * len(malicious)
    return texts, labels


def _load_phishing_datasets() -> Tuple[List[str], List[int]]:
    """Load `ealvaradob/phishing-dataset` directly from its raw JSON files.

    The repo ships a `phishing-dataset.py` loading script — but `datasets` 4.x
    refuses to run scripts. Bypass by pulling the underlying JSON files via
    `huggingface_hub.hf_hub_download` and parsing with pandas. Both files have
    columns `text` (string) and `label` (int, 1=phishing, 0=benign).

    `texts.json` is a ~52 MB subset (emails + SMS) — fast to download and
    well-suited to the page-text semantic rule. To use the much larger
    combined corpus instead (URLs + HTML + emails, ~521 MB), set
    `AGENTGUARD_PHISHING_FILE=combined_reduced.json` before running.
    """
    import os
    import pandas as pd
    from huggingface_hub import hf_hub_download

    repo_id = "ealvaradob/phishing-dataset"
    filename = os.environ.get("AGENTGUARD_PHISHING_FILE", "texts.json")
    _logger.info("downloading %s from %s …", filename, repo_id)
    path = hf_hub_download(repo_id=repo_id, filename=filename, repo_type="dataset")

    df = pd.read_json(path)
    df = df.dropna(subset=["text", "label"])
    texts = [str(t) for t in df["text"].tolist()]
    labels = [1 if int(label) == 1 else 0 for label in df["label"].tolist()]

    pos = sum(labels)
    _logger.info("phishing dataset loaded: %d rows (pos=%d, neg=%d)",
                 len(texts), pos, len(texts) - pos)
    return texts, labels


def _load_prompt_injection_datasets() -> Tuple[List[str], List[int]]:
    """Build a binary prompt-injection dataset.

    The two HF injection sources are positives-only, so we pull benign
    instructions from `databricks/databricks-dolly-15k`.
    """
    from datasets import load_dataset

    texts: List[str] = []
    labels: List[int] = []

    # Positives — imoxto: `user_input` carries the injection payload.
    primary = load_dataset("imoxto/prompt_injection_cleaned_dataset", split="train")
    for row in primary:
        text = row.get("user_input") or row.get("prompt") or ""
        if text:
            texts.append(str(text))
            labels.append(1)

    # Positives — multilingual; single column `prompt_injections`.
    multilingual = load_dataset("yanismiraoui/prompt_injections", split="train")
    for row in multilingual:
        text = row.get("prompt_injections") or ""
        if text:
            texts.append(str(text))
            labels.append(1)

    pos_count = sum(labels)

    # Benign — Databricks Dolly instructions. We cap to roughly match the
    # positive count so the classifier doesn't learn a class-prior shortcut.
    benign = load_dataset("databricks/databricks-dolly-15k", split="train")
    benign_added = 0
    benign_cap = max(pos_count, 1000)
    for row in benign:
        if benign_added >= benign_cap:
            break
        text = row.get("instruction") or ""
        if not text:
            continue
        # Some Dolly instructions ask the model to follow context; that's
        # benign. We skip rows that look adversarial just by literal phrase
        # match so we don't pollute the negative class.
        lowered = text.lower()
        if "ignore previous" in lowered or "ignore all instructions" in lowered:
            continue
        texts.append(str(text))
        labels.append(0)
        benign_added += 1

    _logger.info("prompt-injection dataset loaded: %d rows (pos=%d, neg=%d)",
                 len(texts), pos_count, len(texts) - pos_count)
    return texts, labels


_DATASETS = {
    "phishing_language": ("phishing", _load_phishing_datasets),
    "prompt_injection":  ("prompt_injection", _load_prompt_injection_datasets),
}


def _train_rule(rule_id: str, benign_csv: Path | None, malicious_csv: Path | None) -> None:
    if rule_id not in _DATASETS:
        raise SystemExit(f"Unknown rule_id: {rule_id}. Choose from {list(_DATASETS)}")
    model_id, loader = _DATASETS[rule_id]

    if benign_csv and malicious_csv:
        texts, labels = _read_csv_pair(benign_csv, malicious_csv)
    else:
        texts, labels = loader()

    _train_and_save(model_id, texts, labels)


def _iter_rules(args: argparse.Namespace) -> Iterable[str]:
    if args.all:
        return _DATASETS.keys()
    if args.rule:
        return [args.rule]
    raise SystemExit("Pass --all or --rule <rule_id>")


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true", help="Train every semantic rule")
    parser.add_argument("--rule", choices=list(_DATASETS.keys()), help="Train a single rule")
    parser.add_argument("--benign-csv", type=Path, help="CSV with a 'text' column of benign samples")
    parser.add_argument("--malicious-csv", type=Path, help="CSV with a 'text' column of malicious samples")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if (args.benign_csv is None) != (args.malicious_csv is None):
        parser.error("--benign-csv and --malicious-csv must be passed together")

    for rule_id in _iter_rules(args):
        _train_rule(rule_id, args.benign_csv, args.malicious_csv)
    return 0


if __name__ == "__main__":
    sys.exit(main())
