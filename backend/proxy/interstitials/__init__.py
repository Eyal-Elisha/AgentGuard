"""HTML pages the proxy serves in place of a blocked or flagged navigation.

`block` and `warn` render one page each; `evidence` and `theme` hold the rule
rendering and styling they have in common.
"""

from .block import build_block_html
from .warn import append_bypass_param, build_warn_html

__all__ = ["build_block_html", "build_warn_html", "append_bypass_param"]
