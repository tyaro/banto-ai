"""Public dataset quality gate tests using a small synthetic MetroPT-shaped ZIP."""

from __future__ import annotations

import csv
from datetime import datetime, timedelta
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
import zipfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from banto_ai import public_quality, quality  # noqa: E402
from banto_ai.manifest import load_json  # noqa: E402
from banto_ai.public_quality import PublicDatasetQualityError, check_public_dataset  # noqa: E402

_SPEC = importlib.util.spec_from_file_location(
    "metropt3_import_tool_quality", ROOT / "tools" / "public-data" / "import_metropt3.py"
)
assert _SPEC is not None and _SPEC.loader is not None
import_metropt3 = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(import_metropt3)


class PublicQualityTests(unittest.TestCase):
    def _workspace(self) -> Path:
        root = Path(tempfile.mkdtemp())
        for relative in (
            "examples/configs/metropt3-public-2020-02-21.json",
            "datasets/manifests/metropt3-source.json",
            "schemas/public-transform-config.schema.json",
            "schemas/public-dataset-source.schema.json",
            "schemas/public-dataset-manifest.schema.json",
            "schemas/public-split-manifest.schema.json",
            "schemas/synthetic-dataset-manifest.schema.json",
            "schemas/synthetic-generator-config.schema.json",
            "schemas/split-manifest.schema.json",
        ):
            destination = root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, destination)
        return root

    def _archive(self, directory: Path) -> Path:
        config = load_json(ROOT / "examples/configs/metropt3-public-2020-02-21.json")
        output = io.StringIO(newline="")
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(config["expected_source_header"])
        start = datetime(2020, 2, 21)
        for index in range(1440):
            timestamp = (start + timedelta(minutes=index)).strftime("%Y-%m-%d %H:%M:%S")
            writer.writerow([index, timestamp, 1, 2, 3, 4, 5, 6, 7, index % 2, (index + 1) % 2, index % 2, (index + 1) % 2, index % 2, (index + 1) % 2, index % 2, 99])
        archive = directory / "metropt+3+dataset.zip"
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
            bundle.writestr(import_metropt3.SOURCE_CSV_MEMBER, output.getvalue())
        return archive

    def _build(self, root: Path) -> Path:
        archive = self._archive(root.parent)
        source = load_json(root / "datasets/manifests/metropt3-source.json")
        with patch.object(import_metropt3, "prepare_source", return_value={"archive": {"path": str(archive)}}), patch.object(import_metropt3, "verify_archive", return_value={}):
            return import_metropt3.import_metropt3(root.parent / "external-cache", root / "examples/configs/metropt3-public-2020-02-21.json", accepted=True, root=root)

    def test_public_quality_passes_and_quality_dispatch_preserves_synthetic_branch(self):
        root = self._workspace()
        try:
            output = self._build(root)
            result = check_public_dataset(output, root)
            self.assertEqual(result["status"], "pass")
            self.assertEqual(result["observation_record_count"], 1440)
            self.assertEqual(quality.check_dataset(output, root)["status"], "pass")
            self.assertTrue((output / "fingerprint.json").is_file())
            expected = "UTF-8 JSON with deterministic object key order and compact separators; JSONL row order is timestamp order; aggregate input is sorted file name and digest"
            self.assertEqual(public_quality.FINGERPRINT_CANONICALIZATION, expected)
            self.assertEqual(import_metropt3.FINGERPRINT_CANONICALIZATION, expected)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_chronological_split_is_exclusive_contiguous_and_exactly_counted(self):
        root = self._workspace()
        try:
            output = self._build(root)
            split = load_json(output / "split-manifest.json")
            self.assertEqual([item["strategy"] for item in split["strategies"]], ["chronological"])
            items = split["strategies"][0]["splits"]
            self.assertEqual([item["record_count"] for item in items], [864, 288, 288])
            self.assertEqual(items[0]["start_timestamp"], "2020-02-21T00:01:00Z")
            self.assertEqual(items[-1]["end_timestamp"], "2020-02-22T00:01:00Z")
            rows = [json.loads(line) for line in (output / "observations.jsonl").read_text(encoding="utf-8").splitlines()]
            timestamps = [datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00")) for row in rows]
            covered = []
            for item in items:
                start = datetime.fromisoformat(item["start_timestamp"].replace("Z", "+00:00"))
                end = datetime.fromisoformat(item["end_timestamp"].replace("Z", "+00:00"))
                selected = [timestamp for timestamp in timestamps if start <= timestamp < end]
                self.assertEqual(len(selected), item["record_count"])
                self.assertEqual(selected[-1] + timedelta(minutes=1), end)
                covered.extend(selected)
            self.assertEqual(covered, timestamps)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_fingerprint_detects_observation_mutation(self):
        root = self._workspace()
        try:
            output = self._build(root)
            path = output / "observations.jsonl"
            lines = path.read_text(encoding="utf-8").splitlines()
            row = json.loads(lines[0])
            row["signals"]["tp3"]["value"] += 1
            lines[0] = json.dumps(row)
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(PublicDatasetQualityError, "fingerprint mismatch"):
                check_public_dataset(output, root)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_source_cadence_tampering_is_rejected_after_fingerprint_rehash(self):
        root = self._workspace()
        try:
            output = self._build(root)
            quality_path = output / "quality-report.json"
            quality_value = json.loads(quality_path.read_text(encoding="utf-8"))
            quality_value["source_cadence"]["last_timestamp_raw"] = "2020-02-21 23:59:58"
            import_metropt3._write_json(quality_path, quality_value)
            fingerprint_path = output / "fingerprint.json"
            fingerprint = json.loads(fingerprint_path.read_text(encoding="utf-8"))
            fingerprint["files"]["quality-report.json"] = import_metropt3._sha256(quality_path)
            canonical = "".join(f"{name}\n{digest}\n" for name, digest in sorted(fingerprint["files"].items())).encode("utf-8")
            fingerprint["dataset_fingerprint"] = hashlib.sha256(canonical).hexdigest()
            import_metropt3._write_json(fingerprint_path, fingerprint)
            with self.assertRaisesRegex(PublicDatasetQualityError, "source cadence"):
                check_public_dataset(output, root)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_manifest_paths_and_quality_report_are_fail_closed(self):
        for mutation, message in (
            (lambda value: value.update(data_path="../outside.jsonl"), "schema"),
            (lambda value: value.update(source_manifest_path="C:/outside.json"), "schema"),
        ):
            root = self._workspace()
            try:
                output = self._build(root)
                path = output / "dataset-manifest.json"
                value = json.loads(path.read_text(encoding="utf-8"))
                mutation(value)
                path.write_text(json.dumps(value), encoding="utf-8")
                with self.subTest(message=message), self.assertRaises(PublicDatasetQualityError):
                    check_public_dataset(output, root)
            finally:
                shutil.rmtree(root, ignore_errors=True)
        root = self._workspace()
        try:
            output = self._build(root)
            path = output / "quality-report.json"
            value = json.loads(path.read_text(encoding="utf-8"))
            value["dataset_fingerprint"] = "0" * 64
            path.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaisesRegex(PublicDatasetQualityError, "quality report"):
                check_public_dataset(output, root)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_binary_quality_and_label_input_leakage_are_rejected(self):
        for mutation in (
            lambda row: row["signals"].__setitem__("comp", {"unit": "binary", "value": 2}),
            lambda row: row["quality"].__setitem__("tp3", "missing"),
            lambda row: row.__setitem__("label", "fault"),
        ):
            root = self._workspace()
            try:
                output = self._build(root)
                path = output / "observations.jsonl"
                rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
                mutation(rows[0])
                path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
                with self.assertRaises(PublicDatasetQualityError):
                    check_public_dataset(output, root)
            finally:
                shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
