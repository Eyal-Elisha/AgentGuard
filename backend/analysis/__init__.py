"""The rule engine: what turns a page into a risk score and a decision.

`rules` holds the definitions — the types, the calibration and the catalogue
of sixteen rules. `stages` holds the two evaluators that run them: Stage A for
the cheap rules, Stage B for the semantic classifiers, which run only when
Stage A finishes undecided.
"""
