"""Parses an intercepted response once into an `ExtractedFeatures` snapshot. Every
rule reads from that snapshot rather than re-parsing the page.
"""

from .feature_extractor import FeatureExtractor, ExtractedFeatures, DomFeatures

__all__ = [
    "FeatureExtractor",
    "ExtractedFeatures",
    "DomFeatures",
]