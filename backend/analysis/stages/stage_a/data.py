"""Static reference data used by Stage A deterministic rules."""

from __future__ import annotations

import re
from typing import Dict, List, Tuple

# Known brand → official registrable domains (suffix-matched).
# There is no universal open feed that maps brand names to their official domains - maybe should use db instead
BRAND_DOMAINS: Dict[str, List[str]] = {
    # ── Search / Big Tech ────────────────────────────────────────────────────
    "google":        ["google.com", "google.co.uk", "google.de", "google.fr",
                      "google.co.jp", "google.com.br", "google.com.au",
                      "googleapis.com", "googleusercontent.com", "youtube.com",
                      "googlevideo.com", "gstatic.com", "google.ca"],
    "microsoft":     ["microsoft.com", "live.com", "outlook.com", "office.com",
                      "office365.com", "azure.com", "azurewebsites.net",
                      "microsoftonline.com", "sharepoint.com", "onedrive.com",
                      "bing.com", "msn.com", "skype.com", "xbox.com",
                      "visualstudio.com", "github.com"],
    "apple":         ["apple.com", "icloud.com", "itunes.com", "mzstatic.com",
                      "apple-cloudkit.com"],
    "amazon":        ["amazon.com", "amazon.co.uk", "amazon.de", "amazon.fr",
                      "amazon.co.jp", "amazon.com.br", "amazon.com.au",
                      "amazon.ca", "amazonaws.com", "amazon.in",
                      "amazon.it", "amazon.es"],

    # ── Social / Communication ───────────────────────────────────────────────
    "facebook":      ["facebook.com", "fb.com", "fbcdn.net", "instagram.com",
                      "whatsapp.com", "messenger.com", "meta.com"],
    "twitter":       ["twitter.com", "x.com", "t.co"],
    "linkedin":      ["linkedin.com", "licdn.com"],
    "tiktok":        ["tiktok.com", "tiktokcdn.com", "musical.ly"],
    "snapchat":      ["snapchat.com", "snap.com"],
    "pinterest":     ["pinterest.com", "pinimg.com"],
    "reddit":        ["reddit.com", "redd.it", "redditmedia.com", "reddituploads.com"],
    "discord":       ["discord.com", "discord.gg", "discordapp.com", "discordcdn.com"],
    "telegram":      ["telegram.org", "t.me", "telegram.me"],
    "signal":        ["signal.org"],
    "tumblr":        ["tumblr.com"],
    "twitch":        ["twitch.tv", "twitchapps.com"],

    # ── Email ────────────────────────────────────────────────────────────────
    "gmail":         ["gmail.com", "google.com"],
    "yahoo":         ["yahoo.com", "yahoo.co.uk", "yahoo.fr", "yahoo.co.jp",
                      "ymail.com", "yahoomail.com"],
    "protonmail":    ["protonmail.com", "proton.me", "pm.me"],

    # ── Payment / Fintech ────────────────────────────────────────────────────
    "paypal":        ["paypal.com", "paypal.me", "paypalobjects.com"],
    "stripe":        ["stripe.com", "stripe.network", "stripecdn.com"],
    "venmo":         ["venmo.com"],
    "cashapp":       ["cash.app", "cashapp.com"],
    "zelle":         ["zellepay.com"],
    "square":        ["squareup.com", "square.com", "squarespace.com"],
    "klarna":        ["klarna.com"],
    "affirm":        ["affirm.com"],

    # ── Banking ──────────────────────────────────────────────────────────────
    "chase":         ["chase.com", "jpmorganchase.com", "jpmorgan.com"],
    "wellsfargo":    ["wellsfargo.com"],
    "bankofamerica": ["bankofamerica.com", "bac.com", "ml.com"],
    "citibank":      ["citibank.com", "citi.com", "citigroup.com"],
    "capitaloneone": ["capitalone.com"],
    "usbank":        ["usbank.com"],
    "tdbank":        ["td.com", "tdbank.com", "tdameritrade.com"],
    "barclays":      ["barclays.com", "barclaysus.com", "barclaycard.com"],
    "hsbc":          ["hsbc.com", "hsbc.co.uk"],
    "americanexpress": ["americanexpress.com", "amex.com"],
    "discover":      ["discover.com", "discovercard.com"],
    "ally":          ["ally.com"],
    "schwab":        ["schwab.com", "charlesschwab.com"],
    "fidelity":      ["fidelity.com", "fidelityinvestments.com"],
    "vanguard":      ["vanguard.com"],
    "robinhood":     ["robinhood.com"],

    # ── Crypto ───────────────────────────────────────────────────────────────
    "coinbase":      ["coinbase.com", "coinbase.pro"],
    "binance":       ["binance.com", "binance.us"],
    "kraken":        ["kraken.com"],
    "gemini":        ["gemini.com"],
    "cryptocom":     ["crypto.com"],
    "metamask":      ["metamask.io"],
    "opensea":       ["opensea.io"],
    "ledger":        ["ledger.com"],
    "trezor":        ["trezor.io"],

    # ── Cloud / Hosting / Dev ────────────────────────────────────────────────
    "github":        ["github.com", "githubusercontent.com", "githubassets.com",
                      "github.io"],
    "gitlab":        ["gitlab.com"],
    "atlassian":     ["atlassian.com", "jira.com", "confluence.com", "bitbucket.org",
                      "trello.com"],
    "digitalocean":  ["digitalocean.com", "digitaloceanspaces.com"],
    "cloudflare":    ["cloudflare.com", "cloudflareinsights.com", "cloudflareworkers.com"],
    "heroku":        ["heroku.com", "herokuapp.com"],
    "netlify":       ["netlify.com", "netlify.app"],
    "vercel":        ["vercel.com", "vercel.app"],
    "dropbox":       ["dropbox.com", "dropboxstatic.com"],

    # ── Productivity / SaaS ──────────────────────────────────────────────────
    "slack":         ["slack.com", "slack-edge.com"],
    "zoom":          ["zoom.us", "zoom.com"],
    "notion":        ["notion.so", "notion.com"],
    "airtable":      ["airtable.com"],
    "salesforce":    ["salesforce.com", "force.com", "salesforceliveagent.com"],
    "hubspot":       ["hubspot.com", "hs-scripts.com"],
    "zendesk":       ["zendesk.com"],
    "intercom":      ["intercom.io", "intercom.com"],
    "adobe":         ["adobe.com", "adobecc.com", "typekit.net", "adobedtm.com"],
    "docusign":      ["docusign.com", "docusign.net"],

    # ── Entertainment / Streaming ────────────────────────────────────────────
    "netflix":       ["netflix.com", "nflxvideo.net", "nflximg.net"],
    "spotify":       ["spotify.com", "scdn.co"],
    "hulu":          ["hulu.com"],
    "disney":        ["disney.com", "disneyplus.com", "disney-plus.net"],
    "hbo":           ["hbo.com", "max.com", "hbomax.com"],

    # ── E-commerce / Retail ──────────────────────────────────────────────────
    "ebay":          ["ebay.com", "ebay.co.uk", "ebay.de", "ebayimg.com",
                      "ebaystatic.com"],
    "etsy":          ["etsy.com", "etsystatic.com"],
    "shopify":       ["shopify.com", "myshopify.com", "shopifycdn.com"],
    "walmart":       ["walmart.com"],
    "target":        ["target.com"],
    "bestbuy":       ["bestbuy.com"],
    "aliexpress":    ["aliexpress.com"],
    "alibaba":       ["alibaba.com"],

    # ── Shipping / Logistics ─────────────────────────────────────────────────
    "ups":           ["ups.com"],
    "fedex":         ["fedex.com"],
    "dhl":           ["dhl.com"],
    "usps":          ["usps.com"],

    # ── Travel ───────────────────────────────────────────────────────────────
    "airbnb":        ["airbnb.com"],
    "booking":       ["booking.com"],
    "expedia":       ["expedia.com"],
    "uber":          ["uber.com", "ubereats.com"],
    "lyft":          ["lyft.com"],
    "doordash":      ["doordash.com"],

    # ── Government (US) ──────────────────────────────────────────────────────
    "irs":           ["irs.gov"],
    "ssa":           ["ssa.gov"],
    "usps_gov":      ["usps.gov"],

    # ── Password Managers / Security ─────────────────────────────────────────
    "lastpass":      ["lastpass.com"],
    "1password":     ["1password.com"],
    "bitwarden":     ["bitwarden.com"],
    "dashlane":      ["dashlane.com"],
    "nordvpn":       ["nordvpn.com"],
    "expressvpn":    ["expressvpn.com"],
}

# input type="password" is unconditionally sensitive
SENSITIVE_INPUT_TYPES: frozenset = frozenset({"password"})

# Comprehensive pattern for sensitive field name / id attributes
SENSITIVE_NAME_RE = re.compile(
    r"("
    # Passwords
    r"passw(or)?d|passwd|pwd|pass\b"
    # Credit card
    r"|credit.?card|card.?(num(ber)?|no\b)|cc.?(num(ber)?|no\b)"
    r"|card.?holder|cardholder"
    # Card security codes
    r"|cvv2?|cvc2?|csc\b|ccv|security.?code|card.?code"
    # Card expiry
    r"|expir(y|ation|date)|exp.?date|card.?exp"
    # Bank / wire
    r"|account.?(num(ber)?|no\b)|acct.?(num(ber)?|no\b)"
    r"|routing.?(num(ber)?|no\b)|iban\b|swift\b|bic\b"
    # National identity / tax
    r"|ssn\b|social.?sec(urity)?|national.?id|tax.?id|ein\b"
    # Auth tokens / API secrets
    r"|auth.?token|access.?token|refresh.?token"
    r"|api.?key|api.?secret|client.?secret|private.?key|bearer"
    r"|secret\b"
    # OTP / 2FA
    r"|\botp\b|\b2fa\b|\bmfa\b|verif(y|ication).?code|one.?time"
    r"|authenticat(or|ion).?code|backup.?code"
    # PIN
    r"|\bpin\b|pin.?code"
    # Personal documents
    r"|passport|drivers?.?licen|license.?(num(ber)?|no\b)"
    r"|date.?of.?birth|\bdob\b|birth.?date"
    r")",
    re.IGNORECASE,
)

# Multi-character visual substitutions — applied before single-char confusables
MULTI_CHAR_SUBS: List[Tuple[str, str]] = [
    ("rn", "m"),
    ("vv", "w"),
    ("cl", "d"),
]

# Single-character confusables: lookalike → canonical ASCII
# Covers Cyrillic, Greek, and other Unicode lookalikes used in IDN attacks,
# plus common digit-to-letter substitutions.
CHAR_CONFUSABLES: Dict[str, str] = {
    # Digit → letter (leetspeak / typosquatting)
    "0": "o", "1": "l", "3": "e", "4": "a",
    "5": "s", "6": "g", "7": "t", "8": "b",
    # Cyrillic lookalikes (IDN homograph attacks)
    "\u0430": "a",  # а (Cyrillic small a)
    "\u0435": "e",  # е (Cyrillic small ie)
    "\u043e": "o",  # о (Cyrillic small o)
    "\u0440": "p",  # р (Cyrillic small er)
    "\u0441": "c",  # с (Cyrillic small es)
    "\u0445": "x",  # х (Cyrillic small ha)
    "\u0456": "i",  # і (Cyrillic small i)
    "\u0455": "s",  # ѕ (Cyrillic small dze)
    "\u0501": "d",  # ԁ (Cyrillic small komi de)
    "\u0261": "g",  # ɡ (Latin small script g)
    # Greek lookalikes
    "\u03bf": "o",  # ο (Greek small omicron)
    "\u03b1": "a",  # α (Greek small alpha)
    "\u03bd": "v",  # ν (Greek small nu)
    # Other Latin lookalikes
    "\u0131": "i",  # ı (dotless i)
    "\u01a5": "p",  # ƥ
    "@": "a",
}
