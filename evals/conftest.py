"""load_test.py is a standalone script (run directly: `python evals/load_test.py`),
not a pytest suite - its `test_*`-named functions return dicts rather than
using assert, which is what tripped this up: pytest's testpaths=evals was
auto-collecting them by name, producing PytestReturnNotNoneWarning noise
without actually running them as part of the correctness suite."""

collect_ignore = ["load_test.py"]
