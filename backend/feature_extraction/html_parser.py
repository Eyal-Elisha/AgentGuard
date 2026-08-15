"""Which BeautifulSoup backend parses page HTML.

Every analysed request is parsed twice, once to extract features and once to
strip script/style before Stage B vectorises the text, so the choice of parser
is a measurable share of the decision latency the agent waits on.

`lxml` is a C parser and is measurably faster than Python's built-in
`html.parser`, though by less than its reputation suggests once the rest of the
pipeline is included. Measured over 300 captured pages, four interleaved rounds
per parser in a single process (comparing separate runs is unreliable here, as
run-to-run variance exceeds the effect): median total analysis time 43.6 ms to
40.8 ms (6%), mean 95.8 ms to 82.5 ms (14%), 95th percentile 365.8 ms to
308.6 ms (16%).

The gain concentrates in the slow tail, which is where it matters: parsing cost
scales with page size, so the pages that made the agent wait longest are the
ones that improve most.

The two are not perfectly interchangeable, because they recover differently
from malformed HTML and phishing pages are frequently malformed. Measured over
1,000 captured pages: exactly the same rules fired on every page, the final
risk score differed on two, and one of those crossed a decision band. On that
page (a labelled phishing page) `lxml` scored higher and blocked where
`html.parser` only warned.

`lxml` is a hard dependency in `requirements.txt`, but Stage B already degrades
gracefully when its optional pieces are missing, so this does the same rather
than turning a missing wheel into an import error.
"""

from __future__ import annotations

import logging

_logger = logging.getLogger(__name__)


def _select_parser() -> str:
    try:
        import lxml  # noqa: F401
    except ImportError:
        _logger.warning(
            "lxml is not installed; falling back to html.parser. Analysis will "
            "be roughly 20%% slower per request."
        )
        return "html.parser"
    return "lxml"


#: Passed as the ``features`` argument to every ``BeautifulSoup`` call in the
#: request path. Import this rather than naming a parser inline, so the two
#: call sites cannot drift apart.
HTML_PARSER: str = _select_parser()
