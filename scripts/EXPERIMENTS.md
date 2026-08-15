# Experiment log

What was tried to raise precision at a realistic base rate, and what the
measurements said. Negative results are here so nobody spends a second week
rediscovering them.

The number being optimised throughout is **precision at a 1% phishing base
rate**, because the evaluation corpora are roughly half phishing and real
traffic is not. Corpus precision of 0.99 is 0.74 once converted. See
`README.md` for the conversion.

Two evaluation sets are used, and the distinction matters more than anything
else in this file:

- **in-corpus** — PhreshPhish held-out pages, domains absent from training.
- **cross-corpus** — a different corpus entirely (ealvaradob), collected by
  different people.

## The finding that governs the rest

Domain-disjoint splitting inside one corpus does not measure generalisation.
A whole corpus shares one collection methodology, and a model can learn that
methodology while looking flawless on every held-out split you construct from
it. Every result below is therefore reported on both sets.

## 1. Character-level URL classifier — rejected

Nothing in the engine reads the URL as a string; the URL rules test discrete
properties. Every published baseline for PhreshPhish uses character n-grams
over the raw URL, so this looked like the obvious gap.

TF-IDF `char_wb` 3-5 grams into logistic regression, trained on 224,670 URLs
with all evaluation domains held out.

| | in-corpus | cross-corpus |
|---|---|---|
| average precision | 0.988 | 0.780 |
| precision@1% at 50% recall | 0.813 | 0.042 |

In-corpus it beat the entire shipped engine. Cross-corpus its precision
collapsed by roughly twenty times. Six variants were then trained and judged
on both sets at once:

| variant | in-corpus AP | cross AP | cross precision@1% @R50 |
|---|---|---|---|
| char 3-5, 300k, C=1 | 0.9887 | 0.7686 | 0.040 |
| regularised C=0.05 | 0.9689 | 0.7300 | 0.032 |
| small vocab 20k, C=0.5 | 0.9864 | 0.7495 | 0.035 |
| short ngrams 2-3, 20k | 0.9864 | 0.7568 | 0.037 |
| + half the target corpus, 20k | 0.9856 | 0.7908 | 0.045 |
| + half the target corpus, 300k | 0.9880 | 0.8160 | 0.052 |

Regularising harder made transfer *worse*. Training on half the target
corpus's own domains was the only thing that helped, and still only reached
0.052. **Rejected.** `build_url_trainset.py` remains, since the next attempt
should be trained across corpora and judged cross-corpus from the start.

## 2. Page-text classifier trained across corpora — shipped

The one lever that moved anything in (1) was mixing corpora, so it was applied
to the signal that carries the engine. Fitted on the PhreshPhish training
split plus half of the ealvaradob corpus, the other half held back.

End to end, precision@1% at 30% recall:

| | in-corpus | cross-corpus |
|---|---|---|
| shipped | 0.736 | 0.126 |
| mixed corpora | 0.729 | **0.580** |

Cross-corpus AP 0.784 → 0.887, AUC 0.909 → 0.946, for an in-corpus cost of
0.001 AP. **Shipped.**

Read the cross-corpus figure narrowly. That corpus stores no URLs, so it
cannot be split by domain and was split by row; 6.9% of the eval half shares
exact page text with the train half and is excluded from the figures above.
Half the corpus is now in training, so the eval half measures "has seen this
corpus", not transfer to an unseen third corpus. No third corpus with real
HTML was available.

## 3. Prompt-injection classifier trained across corpora — rejected

The same treatment applied to the other semantic rule.

| fire rate on real pages | benign @0.85 | benign @0.93 |
|---|---|---|
| in-corpus, before | 0.72% | 0.00% |
| in-corpus, after | 0.72% | 0.00% |
| cross-corpus, before | 0.68% | 0.15% |
| cross-corpus, after | 0.49% | 0.00% |

A marginal cross-corpus gain, and the demonstration injection payload scored
*lower* (0.9356 → 0.9333), cutting its margin above the decision floor from
0.0056 to 0.0033. Negligible upside for a thinner safety margin on the only
genuine payload available. **Rejected and reverted.**

The likely reason is scale: the added benign web text was 4,988 rows against
an existing 108,410, in a negative class already outnumbered by 375,607
positives.

## 4. Combiner hyperparameters — rejected

Eight candidates, trained on the same dev features. To avoid choosing a
configuration by the number then quoted, the cross-corpus set was split: one
half selects, the other is touched once by the single chosen configuration.

Best on the selection half was `GradientBoosting(subsample=0.7)` at 0.655
against the current model's 0.559 — an apparent gain of nearly ten points.

On the held-out reporting half:

| | AP | precision@1% at 30% recall |
|---|---|---|
| current | 0.8910 | 0.605 |
| chosen | 0.8919 | 0.605 |

Identical. The entire apparent gain was selection noise. **No change.** The
current `GradientBoostingClassifier(random_state=42)` stands, and this is
evidence it is not the bottleneck.

## Where the remaining gap is

Roughly 10% of phishing pages produce no signal any rule can read, and over
half of those are on reputable free hosting (blogspot and similar), where the
domain is trustworthy, the transport is encrypted and the hostname is
ordinary. Closing that needs evidence the engine does not currently collect —
page screenshots and visual brand similarity, script behaviour after load, or
where outbound form submissions actually go — rather than better weights on
the evidence already in hand.
