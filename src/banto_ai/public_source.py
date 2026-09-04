"""公開データ取得元の固定・検証境界（標準ライブラリのみ）。"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path, PureWindowsPath
import tempfile
from typing import Any, Callable, Mapping
import zipfile

from .manifest import ManifestValidationError, load_json, validate


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST_PATH = ROOT / "datasets" / "manifests" / "metropt3-source.json"
METROPT3_DOWNLOAD_URL = "https://archive.ics.uci.edu/static/public/791/metropt+3+dataset.zip"
METROPT3_ARCHIVE_FILENAME = "metropt+3+dataset.zip"
METROPT3_ARCHIVE_SHA256 = "aab991a970e58210de853bb8078ce0e63abb4d9412fdc5c79792dae3d8e1721a"
METROPT3_ARCHIVE_SIZE_BYTES = 218381995
METROPT3_MEMBERS = (
    ("Data Description_Metro.pdf", 81208, "b00fac0e8899854078309bef4adaa480d82ecf14dc81c5097c3646973e824127"),
    ("MetroPT3(AirCompressor).csv", 218300507, "db30ccb4ea402e3c8bf2c99db06e288d4f2a772f6928f9dbe26a920d69793e24"),
)
Downloader = Callable[[str, Path], None]


class PublicSourceError(ValueError):
    """公開データsourceの固定または検証に失敗した。"""


def _digest(path: Path) -> tuple[int, str]:
    size = 0
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            size += len(chunk)
            digest.update(chunk)
    return size, digest.hexdigest()


def _outside_repository(path: Path) -> Path:
    supplied = Path(path).expanduser()
    if supplied.is_symlink():
        raise PublicSourceError("cache-dir must not be a symlink")
    resolved = supplied.resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError:
        return resolved
    raise PublicSourceError("cache-dir must be outside the repository")


def load_source_manifest(path: Path = DEFAULT_MANIFEST_PATH) -> Mapping[str, Any]:
    """固定済みMetroPT-3 source manifestをschemaと値の両方で検証する。"""
    manifest_path = Path(path).expanduser().resolve()
    try:
        manifest = load_json(manifest_path)
        schema = load_json(ROOT / "schemas" / "public-dataset-source.schema.json")
        validate(manifest, schema)
    except ManifestValidationError as exc:
        raise PublicSourceError(str(exc)) from exc
    if not isinstance(manifest, dict):
        raise PublicSourceError("public source manifest must be an object")
    source = manifest["source"]
    archive = manifest["archive"]
    if source["download_url"] != METROPT3_DOWNLOAD_URL:
        raise PublicSourceError("MetroPT-3 download URL is not the fixed official URL")
    if archive["filename"] != METROPT3_ARCHIVE_FILENAME:
        raise PublicSourceError("MetroPT-3 archive filename is not fixed")
    expected_members = {
        name: (size, digest) for name, size, digest in METROPT3_MEMBERS
    }
    actual_members = {
        item["name"]: (item["size_bytes"], item["sha256"])
        for item in archive["members"]
    }
    if actual_members != expected_members or len(actual_members) != len(archive["members"]):
        raise PublicSourceError("MetroPT-3 archive member evidence is not fixed")
    if archive["size_bytes"] != METROPT3_ARCHIVE_SIZE_BYTES or archive["sha256"] != METROPT3_ARCHIVE_SHA256:
        raise PublicSourceError("MetroPT-3 archive evidence is not fixed")
    if manifest["license"]["spdx_id"] != "CC-BY-4.0":
        raise PublicSourceError("MetroPT-3 license must be CC-BY-4.0")
    return manifest


load_manifest = load_source_manifest


def _validate_zip_path(name: str) -> None:
    if not name or "\x00" in name or "\\" in name or PureWindowsPath(name).drive:
        raise PublicSourceError(f"ZIP member path is unsafe: {name!r}")
    parts = name.split("/")
    if name.startswith("/") or any(part in ("", ".", "..") for part in parts):
        raise PublicSourceError(f"ZIP member path is unsafe: {name!r}")


def verify_archive(archive_path: Path, manifest: Mapping[str, Any]) -> dict[str, Any]:
    """archive全体と、manifestに固定された全memberを検証する。"""
    supplied = Path(archive_path).expanduser()
    if supplied.is_symlink() or not supplied.is_file():
        raise PublicSourceError("archive target must be a regular non-symlink file")
    path = supplied.resolve()
    archive = manifest["archive"]
    size, digest = _digest(path)
    if size != archive["size_bytes"]:
        raise PublicSourceError(f"archive size mismatch: expected {archive['size_bytes']}, got {size}")
    if digest != archive["sha256"]:
        raise PublicSourceError(f"archive SHA-256 mismatch: expected {archive['sha256']}, got {digest}")

    expected = {
        item["name"]: (item["size_bytes"], item["sha256"])
        for item in archive["members"]
    }
    try:
        with zipfile.ZipFile(path) as bundle:
            infos = bundle.infolist()
            names = [info.filename for info in infos]
            if len(names) != len(set(names)):
                raise PublicSourceError("ZIP contains duplicate member names")
            for name in names:
                _validate_zip_path(name)
            if set(names) != set(expected):
                raise PublicSourceError("ZIP member set does not match the fixed manifest")
            if bundle.testzip() is not None:
                raise PublicSourceError("ZIP CRC verification failed")
            members: list[dict[str, Any]] = []
            for info in infos:
                expected_size, expected_digest = expected[info.filename]
                if info.is_dir() or info.file_size != expected_size:
                    raise PublicSourceError(f"ZIP member size mismatch: {info.filename}")
                member_digest = hashlib.sha256()
                with bundle.open(info, "r") as handle:
                    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                        member_digest.update(chunk)
                actual_digest = member_digest.hexdigest()
                if actual_digest != expected_digest:
                    raise PublicSourceError(f"ZIP member SHA-256 mismatch: {info.filename}")
                members.append({
                    "name": info.filename,
                    "size_bytes": info.file_size,
                    "sha256": actual_digest,
                })
    except zipfile.BadZipFile as exc:
        raise PublicSourceError("archive is not a valid ZIP") from exc
    return {
        "filename": archive["filename"],
        "size_bytes": size,
        "sha256": digest,
        "members": members,
    }


def _download_stream(url: str, destination: Path) -> None:
    """urllibを遅延importし、sourceを指定されたtemporary fileへstreamする。"""
    from urllib.request import urlopen

    with urlopen(url) as response, destination.open("wb") as handle:
        for chunk in iter(lambda: response.read(1024 * 1024), b""):
            handle.write(chunk)


def _publish_without_replacement(temporary: Path, target: Path) -> None:
    """同一filesystem内のhard linkを使い、既存targetを置換せずatomicにpublishする。"""
    try:
        os.link(temporary, target)
    except FileExistsError as exc:
        raise PublicSourceError("archive target appeared during publish; refusing overwrite") from exc
    except OSError as exc:
        raise PublicSourceError(f"atomic archive publish failed: {exc}") from exc
    finally:
        temporary.unlink(missing_ok=True)


def _runtime_evidence(manifest: Mapping[str, Any], archive_path: Path, verification: dict[str, Any], status: str) -> dict[str, Any]:
    return {
        "schema_version": "0.1",
        "status": status,
        "verification_status": "verified",
        "dataset_id": manifest["dataset_id"],
        "source": {
            "repository": manifest["source"]["repository"],
            "dataset_id": manifest["source"]["dataset_id"],
            "page_url": manifest["source"]["page_url"],
            "doi": manifest["source"]["doi"],
            "download_url": manifest["source"]["download_url"],
            "last_updated": manifest["source"]["last_updated"],
            "revision": manifest["source"]["revision"],
        },
        "archive": {**verification, "path": str(archive_path)},
        "license": manifest["license"],
        "metadata_conflicts": manifest["metadata_conflicts"],
        "timezone": manifest["timezone"],
        "verified_at": manifest["verified_at"],
    }


def prepare_source(
    cache_dir: Path,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
    *,
    accepted: bool,
    downloader: Downloader | None = None,
) -> dict[str, Any]:
    """MetroPT-3 archiveを取得または検証する。初期化・通信はaccept後だけ行う。"""
    if not accepted:
        raise PublicSourceError("--accept-cc-by-4.0 is required; no cache or network side effect was attempted")
    manifest = load_source_manifest(manifest_path)
    cache = _outside_repository(Path(cache_dir))
    if cache.exists() and not cache.is_dir():
        raise PublicSourceError("cache-dir must be a directory")
    cache.mkdir(parents=True, exist_ok=True)
    archive_path = cache / manifest["archive"]["filename"]
    if archive_path.exists() or archive_path.is_symlink():
        if archive_path.is_symlink() or not archive_path.is_file():
            raise PublicSourceError("archive target must be a regular non-symlink file")
        verification = verify_archive(archive_path, manifest)
        return _runtime_evidence(manifest, archive_path, verification, "cached_verified")

    temporary: Path | None = None
    try:
        handle = tempfile.NamedTemporaryFile(
            mode="wb", prefix=f".{archive_path.name}.", suffix=".part", dir=cache, delete=False
        )
        temporary = Path(handle.name)
        handle.close()
        (downloader or _download_stream)(manifest["source"]["download_url"], temporary)
        verification = verify_archive(temporary, manifest)
        _publish_without_replacement(temporary, archive_path)
        temporary = None
        return _runtime_evidence(manifest, archive_path, verification, "downloaded_verified")
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


prepare_metropt3 = prepare_source


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json
    import sys

    parser = argparse.ArgumentParser(prog="prepare_metropt3.py")
    parser.add_argument("--cache-dir", required=True)
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST_PATH))
    parser.add_argument("--accept-cc-by-4.0", action="store_true", dest="accepted")
    args = parser.parse_args(argv)
    try:
        result = prepare_source(
            Path(args.cache_dir),
            Path(args.manifest),
            accepted=args.accepted,
        )
    except (OSError, PublicSourceError, TypeError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


__all__ = [
    "DEFAULT_MANIFEST_PATH", "METROPT3_DOWNLOAD_URL", "METROPT3_ARCHIVE_FILENAME",
    "PublicSourceError", "load_source_manifest", "load_manifest", "verify_archive",
    "prepare_source", "prepare_metropt3", "main",
]
