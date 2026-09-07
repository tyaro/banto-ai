"""Fixed S4-B1 child. No stdout/stderr diagnostics, fallback or publication."""

import sys

sys.dont_write_bytecode = True

try:
    from pathlib import Path
    _repository = Path(__file__).absolute().parents[2]
    sys.path.insert(0, str(_repository / "src"))
    from banto_ai._anomaly_v03_windows import _child_main, _Failure, _resource_stop, _CHILD_RESOURCE_EXIT
    if len(sys.argv) != 2 or not sys.flags.isolated:
        raise ValueError()
    _code = _child_main(Path(sys.argv[1]))
except BaseException as _error:
    # Fixed diagnostic stages, never exception text, paths or token material.
    _stages = ("child_scope", "child_profile", "child_source", "object_open", "write_file",
               "operation_unexpected", "operation_matrix", "access_expectation", "child_token_drift")
    _reason = getattr(_error, "reason", "")
    _code = (_CHILD_RESOURCE_EXIT if "_resource_stop" in globals() and _resource_stop(_error)
             else 32 + _stages.index(_reason) if _reason in _stages else 1)

raise SystemExit(_code)
