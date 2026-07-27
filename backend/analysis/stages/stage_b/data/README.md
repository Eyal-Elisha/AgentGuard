# Stage B Semantic Classifier Artifacts

Trained `sklearn.pipeline.Pipeline` objects live here as pickled files, one per
semantic rule:

| File                    | Bound rule          |
| ----------------------- | ------------------- |
| `phishing.pkl`          | `phishing_language` |
| `prompt_injection.pkl`  | `prompt_injection`  |

Each pickle is a binary classifier whose final step is a `LogisticRegression`
and whose positive class label is `1` (malicious).

If a file is missing the corresponding rule falls back to the keyword
heuristic in [`../heuristics.py`](../heuristics.py).

To regenerate the artifacts, run:

```bash
python -m backend.analysis.stages.stage_b.train --all
```

See [`../train.py`](../train.py) for dataset sources and CLI flags.
