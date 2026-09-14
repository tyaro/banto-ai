"""Pinned single-attempt worker plumbing; no fixture inspection after failure."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess

from . import anomaly_v03_handle_owner as owned
from .anomaly_v03_held_driver import HeldDriver, WindowsHeldContext

MAX_PIN_BYTES = 256 * 1024
MAX_SOURCE_BYTES = 2 * 1024 * 1024
MAX_OUTPUT_BYTES = 320 * 1024
SOURCE_ROOTS = ("src/banto_ai", "tests/fixtures", "tests/__init__.py")
RESOURCE_NOTICE = b'{"held_worker":"resource_stop","resource_stop":true}\n'
# Keep reachable through main return and interpreter shutdown. No destructor
# closes these native leases; the dedicated process exit is the terminal owner.
_LIVE_WORKER = None


def _read(path, limit):
    with path.open("rb") as stream:
        raw = stream.read(limit + 1)
    owned._need(len(raw) <= limit, "held_launch_input_budget")
    return raw


def source_names(root):
    raw = subprocess.check_output(["git", "ls-files", "-z", "--", *SOURCE_ROOTS], cwd=root)
    names = tuple(name for name in raw.decode("utf-8").split("\0") if name and name.endswith((".py", ".ps1")))
    owned._need(0 < len(names) <= 512 and len(set(names)) == len(names), "held_launch_source_count")
    for name in names:
        path = PurePosixPath(name)
        owned._need(not path.is_absolute() and ".." not in path.parts and "\\" not in name and ":" not in name,
                    "held_launch_source_path")
    return names


def validate_inputs(root, pin_path, revision, expected_sha):
    owned._need(type(revision) is str and re.fullmatch("[a-f0-9]{40}", revision) is not None
                and type(expected_sha) is str and re.fullmatch("[a-f0-9]{64}", expected_sha) is not None,
                "held_launch_pin_shape")
    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    owned._need(actual == revision and not subprocess.check_output(["git", "status", "--porcelain"], cwd=root),
                "held_launch_requires_clean_head")
    raw = _read(pin_path, MAX_PIN_BYTES)
    owned._need(hashlib.sha256(raw).hexdigest() == expected_sha, "held_launch_input_digest")
    pin = json.loads(raw)
    owned._need(type(pin) is dict and set(pin) == {"implementation_revision", "sources"}
                and pin["implementation_revision"] == revision and type(pin["sources"]) is dict,
                "held_launch_input_shape")
    names = source_names(root)
    owned._need(set(names) == set(pin["sources"]), "held_launch_input_inventory")
    for name in names:
        expected = pin["sources"][name]
        owned._need(type(expected) is dict and set(expected) == {"bytes", "sha256"}
                    and type(expected["bytes"]) is int and 0 <= expected["bytes"] <= MAX_SOURCE_BYTES
                    and type(expected["sha256"]) is str, "held_launch_source_pin")
        contents = _read(root / name, MAX_SOURCE_BYTES)
        owned._need(len(contents) == expected["bytes"]
                    and hashlib.sha256(contents).hexdigest() == expected["sha256"], "held_launch_source_changed")
    return len(names)


def execute(context, revision, pin_sha, source_count, write):
    global _LIVE_WORKER
    owned._need(_LIVE_WORKER is None, "held_launch_worker_reused")
    driver = HeldDriver(context)
    _LIVE_WORKER = driver  # Register before any acquisition or callback.
    try:
        driver.run()
    except BaseException as error:
        driver._record(error)
    # Only one stdout call in all paths, including write failure or short write.
    if driver.exit_code() == 80:
        raw = RESOURCE_NOTICE
    else:
        try:
            report = json.loads(driver.report_bytes())
            report.update(source_revision=revision, input_sha256=pin_sha, pinned_source_count=source_count,
                          attempt=1, scope="held consumer local engineering attempt")
            raw = (json.dumps(report, sort_keys=True, ensure_ascii=True) + "\n").encode("ascii")
            if len(raw) > MAX_OUTPUT_BYTES:
                raise MemoryError("held_launch_output_budget")
        except BaseException as error:
            driver._record(error)
            # Failed reporting cannot overwrite retained/resource termination.
            if driver.exit_code() != 80:
                return driver.exit_code()
            raw = RESOURCE_NOTICE
    try:
        count = write(1, raw)
        owned._need(type(count) is int and count == len(raw), "held_launch_short_output")
    except BaseException as error:
        driver._record(error)
    return driver.exit_code()


def launch(root, base, revision, pin_sha, write, *, context_factory=WindowsHeldContext):
    owned._need(_LIVE_WORKER is None, "held_launch_worker_reused")
    count = validate_inputs(root, base / "input-pin.json", revision, pin_sha)
    attempt = base / "attempt-1"
    context = context_factory(attempt, revision)  # No native work in constructor.
    attempt.mkdir()  # Exclusive; no exists check, cleanup, fallback or retry.
    return execute(context, revision, pin_sha, count, write)
