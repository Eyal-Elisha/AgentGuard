"""Turning an intercepted response into the features the rules read.

`FeatureExtractor` parses the HTML once and produces an `ExtractedFeatures`
snapshot — URL parts plus the DOM facts the rules need (title, forms, inputs,
links). Every deterministic rule reads from that snapshot rather than
re-parsing the page.
"""

from .feature_extractor import FeatureExtractor, ExtractedFeatures, DomFeatures

__all__ = [
    "FeatureExtractor",
    "ExtractedFeatures",
    "DomFeatures",
]