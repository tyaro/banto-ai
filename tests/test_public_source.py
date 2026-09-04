"""MetroPT-3 source pinning tests; no network or large archive required."""

from __future__ import annotations

from contextlib import redirect_stderr
import hashlib
from io import StringIO
from pathlib import Path
import sys
import tempfile
import unittest
import warnings
import zipfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from banto_ai.manifest import load_json, validate  # noqa: E402
from banto_ai import public_source  # noqa: E402


class PublicSourceTests(unittest.TestCase):
    def _tiny_manifest(self, archive: Path, members: list[tuple[str, bytes]] | None = None) -> dict:
        members = members or [("a.txt", b"alpha"), ("b.txt", b"beta")]
        size = archive.stat().st_size
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        return {
            "schema_version": "0.1",
            "manifest_type": "public-dataset-source",
            "dataset_id": "metropt3",
            "source": {
                "repository": "UCI Machine Learning Repository",
                "dataset_id": 791,
                "page_url": "https://archive.ics.uci.edu/dataset/791/metropt%2B3%2Bdataset",
                "doi": "https://doi.org/10.24432/C5VW3R",
                "download_url": public_source.METROPT3_DOWNLOAD_URL,
                "last_updated": "2024-09-19",
                "revision": "2024-09-19",
            },
            "archive": {
                "filename": "metropt+3+dataset.zip",
                "size_bytes": size,
                "sha256": digest,
                "members": [
                    {"name": name, "size_bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}
                    for name, content in members
                ],
            },
            "license": {
                "spdx_id": "CC-BY-4.0",
                "url": "https://creativecommons.org/licenses/by/4.0/",
                "redistribution_allowed": True,
                "commercial_use_allowed": True,
                "attribution_required": True,
                "attribution": "Davari et al. (2021). MetroPT-3 Dataset. UCI Machine Learning Repository.",
                "verified_at": "2026-09-04",
            },
            "metadata_conflicts": [{
                "field": "sampling_frequency",
                "sources": ["1 Hz", "0.1 Hz"],
                "status": "unresolved",
                "resolution": "empirical cadence validation is required before conversion",
            }],
            "timezone": {"status": "unspecified", "assumption_required": True},
            "verified_at": "2026-09-04",
        }

    def _zip(self, directory: Path, members: list[tuple[str, bytes]]) -> Path:
        path = directory / "input.zip"
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as bundle:
            for name, content in members:
                bundle.writestr(name, content)
        return path

    def test_tracked_manifest_matches_strict_schema_and_fixed_facts(self):
        manifest = load_json(ROOT / "datasets" / "manifests" / "metropt3-source.json")
        validate(manifest, load_json(ROOT / "schemas" / "public-dataset-source.schema.json"))
        loaded = public_source.load_source_manifest()
        self.assertEqual(loaded["archive"]["sha256"], public_source.METROPT3_ARCHIVE_SHA256)
        self.assertEqual(loaded["dataset_facts"]["instances"], 1516948)
        self.assertEqual(loaded["metadata_conflicts"][0]["status"], "unresolved")
        self.assertEqual(loaded["timezone"]["status"], "unspecified")

    def test_acceptance_gate_precedes_cache_creation_and_downloader(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory) / "cache"
            downloader = unittest.mock.Mock()
            with self.assertRaisesRegex(public_source.PublicSourceError, "accept-cc-by-4.0"):
                public_source.prepare_source(cache, accepted=False, downloader=downloader)
            self.assertFalse(cache.exists())
            downloader.assert_not_called()

    def test_cache_must_be_external_and_archive_target_must_be_regular(self):
        with self.assertRaisesRegex(public_source.PublicSourceError, "outside"):
            public_source.prepare_source(ROOT / "artifacts" / "public", accepted=True, downloader=lambda *_: None)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self._zip(root, [("a.txt", b"alpha"), ("b.txt", b"beta")])
            manifest = self._tiny_manifest(source)
            cache = root / "cache"
            cache.mkdir()
            (cache / public_source.METROPT3_ARCHIVE_FILENAME).mkdir()
            with patch.object(public_source, "load_source_manifest", return_value=manifest):
                with self.assertRaisesRegex(public_source.PublicSourceError, "regular"):
                    public_source.prepare_source(cache, accepted=True, downloader=lambda *_: None)

    def test_existing_verified_archive_returns_machine_readable_evidence_without_download(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            members = [("a.txt", b"alpha"), ("b.txt", b"beta")]
            created = self._zip(root, members)
            manifest = self._tiny_manifest(created, members)
            target = root / public_source.METROPT3_ARCHIVE_FILENAME
            created.rename(target)
            downloader = unittest.mock.Mock()
            with patch.object(public_source, "load_source_manifest", return_value=manifest):
                result = public_source.prepare_source(target.parent, accepted=True, downloader=downloader)
            self.assertEqual(result["status"], "cached_verified")
            self.assertEqual(result["verification_status"], "verified")
            self.assertEqual(result["archive"]["path"], str(target))
            self.assertEqual([item["name"] for item in result["archive"]["members"]], ["a.txt", "b.txt"])
            downloader.assert_not_called()

    def test_download_uses_fixed_url_verifies_and_publishes_without_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self._zip(root, [("a.txt", b"alpha"), ("b.txt", b"beta")])
            manifest = self._tiny_manifest(source, [("a.txt", b"alpha"), ("b.txt", b"beta")])
            calls: list[tuple[str, Path]] = []

            def downloader(url: str, destination: Path) -> None:
                calls.append((url, destination))
                destination.write_bytes(source.read_bytes())

            with patch.object(public_source, "load_source_manifest", return_value=manifest):
                result = public_source.prepare_source(root / "cache", accepted=True, downloader=downloader)
            target = root / "cache" / public_source.METROPT3_ARCHIVE_FILENAME
            self.assertEqual(result["status"], "downloaded_verified")
            self.assertEqual(calls[0][0], public_source.METROPT3_DOWNLOAD_URL)
            self.assertTrue(target.is_file())
            self.assertEqual(tuple((root / "cache").glob("*.part")), ())

    def test_size_or_hash_mismatch_fails_without_replacing_existing_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self._zip(root, [("a.txt", b"alpha"), ("b.txt", b"beta")])
            manifest = self._tiny_manifest(source, [("a.txt", b"alpha"), ("b.txt", b"beta")])
            target = root / public_source.METROPT3_ARCHIVE_FILENAME
            target.write_bytes(b"not-a-zip")
            with patch.object(public_source, "load_source_manifest", return_value=manifest):
                with self.assertRaisesRegex(public_source.PublicSourceError, "size|SHA-256"):
                    public_source.prepare_source(root, accepted=True, downloader=lambda *_: self.fail("must not download"))
            self.assertEqual(target.read_bytes(), b"not-a-zip")

    def test_bad_zip_member_set_crc_hash_duplicate_extra_and_traversal_are_rejected(self):
        cases = [
            ([("a.txt", b"alpha")], [("a.txt", b"alpha"), ("b.txt", b"beta")], "member set"),
            ([("a.txt", b"alpha"), ("a.txt", b"alpha")], [("a.txt", b"alpha"), ("b.txt", b"beta")], "duplicate"),
            ([("a.txt", b"alpha"), ("b.txt", b"beta"), ("extra.txt", b"extra")], [("a.txt", b"alpha"), ("b.txt", b"beta")], "member set"),
            ([("../escape.txt", b"escape"), ("b.txt", b"beta")], [("../escape.txt", b"escape"), ("b.txt", b"beta")], "unsafe"),
            ([("C:/evil.txt", b"escape"), ("b.txt", b"beta")], [("C:/evil.txt", b"escape"), ("b.txt", b"beta")], "unsafe"),
            ([("a.txt", b"alpha"), ("b.txt", b"beta")], [("a.txt", b"alphx"), ("b.txt", b"beta")], "member SHA-256"),
        ]
        for archive_members, expected_members, message in cases:
            with self.subTest(message=message):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    if len({name for name, _ in archive_members}) != len(archive_members):
                        with warnings.catch_warnings():
                            warnings.simplefilter("ignore", UserWarning)
                            archive = self._zip(root, archive_members)
                    else:
                        archive = self._zip(root, archive_members)
                    manifest = self._tiny_manifest(archive, expected_members)
                    with self.assertRaisesRegex(public_source.PublicSourceError, message):
                        public_source.verify_archive(archive, manifest)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "invalid.zip"
            archive.write_bytes(b"not a ZIP archive")
            manifest = self._tiny_manifest(archive, [("a.txt", b"alpha"), ("b.txt", b"beta")])
            with self.assertRaisesRegex(public_source.PublicSourceError, "valid ZIP"):
                public_source.verify_archive(archive, manifest)

    def test_interrupted_download_cleans_only_own_temporary_file_and_does_not_publish(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self._zip(root, [("a.txt", b"alpha"), ("b.txt", b"beta")])
            manifest = self._tiny_manifest(source, [("a.txt", b"alpha"), ("b.txt", b"beta")])
            cache = root / "cache"

            def interrupted(_url: str, destination: Path) -> None:
                destination.write_bytes(b"partial")
                raise OSError("interrupted")

            with patch.object(public_source, "load_source_manifest", return_value=manifest):
                with self.assertRaises(OSError):
                    public_source.prepare_source(cache, accepted=True, downloader=interrupted)
            self.assertFalse((cache / public_source.METROPT3_ARCHIVE_FILENAME).exists())
            self.assertEqual(tuple(cache.glob("*.part")), ())

    def test_publish_race_refuses_replacement_and_preserves_target(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self._zip(root, [("a.txt", b"alpha"), ("b.txt", b"beta")])
            manifest = self._tiny_manifest(source, [("a.txt", b"alpha"), ("b.txt", b"beta")])
            target = root / "cache" / public_source.METROPT3_ARCHIVE_FILENAME

            def racing_link(_temporary: Path, destination: Path) -> None:
                destination.write_bytes(b"racing-target")
                raise FileExistsError("race")

            with patch.object(public_source, "load_source_manifest", return_value=manifest):
                with patch.object(public_source.os, "link", side_effect=racing_link):
                    with self.assertRaisesRegex(public_source.PublicSourceError, "refusing overwrite"):
                        public_source.prepare_source(
                            target.parent,
                            accepted=True,
                            downloader=lambda _url, destination: destination.write_bytes(source.read_bytes()),
                        )
            self.assertEqual(target.read_bytes(), b"racing-target")
            self.assertEqual(tuple(target.parent.glob("*.part")), ())

    def test_import_has_no_network_module_side_effect_and_cli_acceptance_is_domain_checked(self):
        source = (ROOT / "src" / "banto_ai" / "public_source.py").read_text(encoding="utf-8")
        module_header = source.split("def _download_stream", 1)[0]
        self.assertNotIn("urllib", module_header)
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory) / "cache"
            stderr = StringIO()
            with redirect_stderr(stderr):
                result = public_source.main(["--cache-dir", str(cache)])
            self.assertEqual(result, 1)
            self.assertIn("--accept-cc-by-4.0 is required", stderr.getvalue())
            self.assertFalse(cache.exists())


if __name__ == "__main__":
    unittest.main()
