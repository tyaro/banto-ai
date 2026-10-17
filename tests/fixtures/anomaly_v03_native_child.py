"""Fixed S4-B1 child. No stdout/stderr diagnostics, fallback or publication."""

import sys

sys.dont_write_bytecode = True
_child_invoked = False

try:
    from pathlib import Path
    _repository = Path(__file__).absolute().parents[2]
    sys.path.insert(0, str(_repository / "src"))
    from banto_ai._anomaly_v03_windows import _child_main, _child_failure_exit
    if len(sys.argv) != 2 or not sys.flags.isolated:
        raise ValueError()
    _root = Path(sys.argv[1])
    _child_invoked = True
    _code = _child_main(_root)
except BaseException as _error:
    # Imports can fail before the shared classifier/constant is available.
    # Keep this protocol literal synchronized with _CHILD_RESOURCE_EXIT.
    if (isinstance(_error, MemoryError)
            or isinstance(_error, OSError) and getattr(_error, "winerror", None) in (8, 14, 39, 112, 1450, 1455, 1816)):
        _code = 80
    elif _child_invoked:
        _code = _child_failure_exit(_error)
    else:
        # Fixed bootstrap classes; no exception text, paths, output or file writes.
        # Keep the order synchronized with _CHILD_EXCEPTION_TYPES in the core.
        _types = (ModuleNotFoundError, ImportError, PermissionError, FileNotFoundError,
                  OSError, ValueError, TypeError, KeyError, AttributeError, RuntimeError, SystemExit)
        _code = 96 + _types.index(type(_error)) if type(_error) in _types else 107

raise SystemExit(_code)
