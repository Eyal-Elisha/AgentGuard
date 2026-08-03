"""The pages served in place of a blocked or flagged navigation. `block` and
`warn` render one each; `evidence` and `theme` hold what they have in common.
"""

from .block import build_block_html
from .warn import append_bypass_param, build_warn_html

__all__ = ["build_block_html", "build_warn_html", "append_bypass_param"]
