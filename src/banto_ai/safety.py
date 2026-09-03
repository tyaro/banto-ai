"""公開repositoryへ危険なデータ・credential・checkpointを入れない検査。"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Iterable


FORBIDDEN_SEGMENTS = frozenset({
    "customer", "customers", "customer-data", "customer_data", "client-data", "client_data",
    "production-data", "production_data", "prod-data", "prod_data", "private-data", "private_data",
    "raw-data", "raw_data", "credentials", "secrets", "secret",
})
FORBIDDEN_EXTENSIONS = frozenset({
    ".ckpt", ".pt", ".pth", ".safetensors", ".onnx", ".bin", ".pkl", ".pickle", ".joblib",
    ".parquet", ".feather", ".arrow", ".sqlite", ".db", ".pem", ".key", ".pfx", ".csv",
})
FORBIDDEN_NAMES = frozenset({".env", "id_rsa", "credentials.json", "secrets.json"})
SECRET_PATTERNS = (
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)


class RepositorySafetyError(RuntimeError):
    """安全なtracked file列挙を保証できない場合に発生する。"""


FALLBACK_IGNORED_DIRS = frozenset({
    ".git", ".venv", "venv", "__pycache__", "data", "artifacts", "checkpoints", "local",
})


def scan_repository(root: Path, paths: Iterable[Path] | None = None) -> list[str]:
    """検査対象をtracked fileに限定する。gitなしではlocal領域を除外したfallbackを使う。

    ``paths``を渡した場合は、明示したファイル／ディレクトリだけを検査する。
    これはgit metadataのない環境で、tracked相当の対象を呼び出し側が指定するための入口でもある。
    """
    findings: list[str] = []
    for path in _files_to_scan(root, paths):
        relative = path.relative_to(root)
        lower_parts = {part.lower() for part in relative.parts}
        if lower_parts & FORBIDDEN_SEGMENTS:
            findings.append(f"forbidden path: {relative}")
        lower_name = path.name.lower()
        if (lower_name in FORBIDDEN_NAMES or lower_name.endswith(".safetensors.index.json")
                or lower_name.endswith(".csv.gz") or path.suffix.lower() in FORBIDDEN_EXTENSIONS):
            findings.append(f"forbidden file type: {relative}")
        if path.stat().st_size <= 2_000_000 and path.suffix.lower() in {".json", ".md", ".py", ".toml", ".yml", ".yaml"}:
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if any(pattern.search(text) for pattern in SECRET_PATTERNS):
                findings.append(f"credential-like content: {relative}")
    return findings


def _files_to_scan(root: Path, paths: Iterable[Path] | None) -> list[Path]:
    if paths is not None:
        candidates: list[Path] = []
        for supplied in paths:
            candidate = supplied if supplied.is_absolute() else root / supplied
            if not candidate.resolve().is_relative_to(root.resolve()):
                raise ValueError(f"scan path is outside repository: {supplied}")
            if candidate.is_file():
                candidates.append(candidate)
            elif candidate.is_dir():
                candidates.extend(path for path in candidate.rglob("*") if path.is_file())
        return sorted(set(candidates))

    tracked = _git_tracked_files(root)
    if tracked is not None:
        return tracked
    return sorted(
        path for path in root.rglob("*")
        if path.is_file() and not _is_fallback_ignored(path.relative_to(root))
    )


def _git_tracked_files(root: Path) -> list[Path] | None:
    if not (root / ".git").exists():
        return None
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z"],
            check=True,
            capture_output=True,
            text=False,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RepositorySafetyError(
            f"git metadata exists but tracked file enumeration failed: {exc}"
        ) from exc
    try:
        names = result.stdout.decode("utf-8").split("\0")
    except UnicodeDecodeError as exc:
        raise RepositorySafetyError("git ls-files returned invalid UTF-8") from exc
    return sorted(root / name for name in names if name)


def _is_fallback_ignored(relative: Path) -> bool:
    return any(part.lower() in FALLBACK_IGNORED_DIRS for part in relative.parts)
