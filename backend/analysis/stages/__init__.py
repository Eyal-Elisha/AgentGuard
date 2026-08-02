"""The two evaluation stages, ordered by what they cost to run.

Stage A runs every cheap rule on every request. Stage B runs the semantic
classifiers, and only for requests Stage A left in the undecided band — which
is the whole point of splitting them, since Stage B is the expensive half and
the proxy is holding a connection open while it runs.
"""
