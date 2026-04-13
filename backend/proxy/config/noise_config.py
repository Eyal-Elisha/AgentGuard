"""Configuration constants used by the noise traffic filter."""

EASYPRIVACY_URL = "https://easylist.to/easylist/easyprivacy.txt"

NOISE_HOST_TOKENS = {
    "analytics",
    "beacon",
    "beacons",
    "signaler",
    "telemetry",
    "metrics",
    "sentry",
    "amplitude",
    "mixpanel",
    "hotjar",
    "segment",
    "collect",
    "gtag",
    "cdn",
    "update",
    "appcast",
    "extensions",
    "browseros",
    "safebrowsing",
    "gcp",
    "gvt",
    "clients",
}

PATH_NOISE_KEYWORDS = (
    "domainreliability",
    "domainreliability/upload",
    "multi-watch",
    "multi_watch",
    "update-manifest",
    "extensions.json",
    "appcast",
    "check-update",
    "update",
    "/nel/",
    "/domainreliability/",
    "/beacon",
    "/beacons",
)
