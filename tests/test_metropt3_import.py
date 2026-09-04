"""MetroPT-3 streaming importer contract tests without the real 218 MB archive."""

from __future__ import annotations

import csv
from datetime import datetime, timedelta
import io
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
import zipfile
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from banto_ai.manifest import load_json, validate  # noqa: E402
from banto_ai.benchmark import _split_indices_for_rows  # noqa: E402
_SPEC = importlib.util.spec_from_file_location(
    "metropt3_import_tool", ROOT / "tools" / "public-data" / "import_metropt3.py"
)
assert _SPEC is not None and _SPEC.loader is not None
import_metropt3 = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(import_metropt3)


class MetroPT3ImportTests(unittest.TestCase):
    def _workspace(self) -> Path:
        root = Path(tempfile.mkdtemp())
        for relative in (
            "examples/configs/metropt3-public-2020-02-21.json",
            "datasets/manifests/metropt3-source.json",
            "schemas/public-transform-config.schema.json",
            "schemas/public-dataset-source.schema.json",
            "schemas/public-dataset-manifest.schema.json",
            "schemas/public-split-manifest.schema.json",
        ):
            destination = root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, destination)
        return root

    def _config(self) -> dict:
        return load_json(ROOT / "examples/configs/metropt3-public-2020-02-21.json")

    def _csv_zip(self, directory: Path, *, mutate_header=None, mutate_rows=None, rows_per_bin: int = 2) -> Path:
        config = self._config()
        header = list(config["expected_source_header"])
        if mutate_header:
            mutate_header(header)
        output = io.StringIO(newline="")
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(header)
        start = datetime(2020, 2, 21)
        for bin_index in range(1440):
            for sample_index in range(rows_per_bin):
                timestamp = start + timedelta(minutes=bin_index, seconds=30 if sample_index == 0 else 59)
                values = [
                    str(bin_index * rows_per_bin + sample_index),
                    timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    f"{1 + bin_index + sample_index}",
                    f"{2 + bin_index + sample_index}",
                    f"{3 + bin_index + sample_index}",
                    f"{4 + bin_index + sample_index}",
                    f"{5 + bin_index + sample_index}",
                    f"{6 + bin_index + sample_index}",
                    f"{7 + bin_index + sample_index}",
                    str(sample_index),
                    str((sample_index + 1) % 2),
                    str(sample_index),
                    str((sample_index + 1) % 2),
                    str(sample_index),
                    str((sample_index + 1) % 2),
                    str(sample_index),
                    "999",
                ]
                if mutate_rows:
                    mutate_rows(values, bin_index, sample_index)
                writer.writerow(values)
        archive = directory / "metropt+3+dataset.zip"
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
            bundle.writestr(import_metropt3.SOURCE_CSV_MEMBER, output.getvalue())
        return archive

    def _import(self, root: Path, archive: Path, *, config: dict | None = None) -> Path:
        config_path = "examples/configs/metropt3-public-2020-02-21.json"
        if config is not None:
            (root / config_path).write_text(json.dumps(config), encoding="utf-8")
        source_manifest = load_json(root / "datasets/manifests/metropt3-source.json")
        with patch.object(import_metropt3, "prepare_source", return_value={"archive": {"path": str(archive)}}) as prepared:
            with patch.object(import_metropt3, "verify_archive", return_value={}) as verified:
                output = import_metropt3.import_metropt3(
                    root.parent / "external-cache",
                    config_path,
                    accepted=True,
                    root=root,
                )
        prepared.assert_called_once()
        verified.assert_called_once()
        self.assertEqual(source_manifest["dataset_id"], "metropt3")
        return output

    def test_config_schema_and_signal_roles_are_fixed(self):
        config = self._config()
        validate(config, load_json(ROOT / "schemas/public-transform-config.schema.json"))
        self.assertEqual(config["output"]["sample_count"], 1440)
        self.assertEqual(config["binning"]["interval_ms"], 60000)
        self.assertEqual(config["excluded_source_columns"], ["Caudal_impulses"])
        self.assertEqual(config["known_future_covariate_ids"], [])
        self.assertEqual(
            [item["logical_signal_id"] for item in config["signals"] if item["role"] == "target"],
            ["tp3", "oil_temperature", "motor_current"],
        )
        self.assertEqual(
            [item["unit"] for item in config["signals"] if item["aggregation"] == "last"],
            ["binary"] * 7,
        )
        self.assertEqual(next(item for item in config["signals"] if item["source_name"] == "DV_eletric")["logical_signal_id"], "dv_electric")

    def test_acceptance_gate_precedes_config_cache_and_output_side_effects(self):
        root = self._workspace()
        try:
            cache = root.parent / "cache-before-accept"
            with patch.object(import_metropt3, "load_transform_config") as loaded:
                with self.assertRaisesRegex(import_metropt3.MetroPT3ImportError, "accept-cc-by-4.0"):
                    import_metropt3.import_metropt3(cache, accepted=False, root=root)
            loaded.assert_not_called()
            self.assertFalse(cache.exists())
            self.assertFalse((root / "artifacts").exists())
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_streaming_aggregation_bin_end_and_deterministic_artifacts(self):
        root = self._workspace()
        try:
            archive = self._csv_zip(root.parent)
            first = self._import(root, archive)
            first_bytes = {path.name: path.read_bytes() for path in first.iterdir()}
            observations = [json.loads(line) for line in (first / "observations.jsonl").read_text(encoding="utf-8").splitlines()]
            quality = load_json(first / "quality-report.json")
            fingerprint = load_json(first / "fingerprint.json")
            self.assertEqual(len(observations), 1440)
            self.assertEqual(observations[0]["timestamp"], "2020-02-21T00:01:00Z")
            self.assertEqual(observations[-1]["timestamp"], "2020-02-22T00:00:00Z")
            self.assertEqual(observations[0]["signals"]["tp2"]["value"], 1.5)
            self.assertEqual(observations[0]["signals"]["comp"]["value"], 1.0)
            self.assertNotIn("caudal_impulses", observations[0]["signals"])
            self.assertEqual(quality["source_cadence"], {"first_timestamp_raw": "2020-02-21 00:00:30", "last_timestamp_raw": "2020-02-21 23:59:59", "min_delta_ms": 29000, "max_delta_ms": 31000, "delta_ms_histogram": {"29000": 1440, "31000": 1439}, "min_observations_per_bin": 2, "max_observations_per_bin": 2})
            self.assertEqual(fingerprint["canonicalization"], import_metropt3.FINGERPRINT_CANONICALIZATION)
            self.assertEqual(set(path.name for path in first.iterdir()), {"source-manifest.json", "transform-config.json", "observations.jsonl", "split-manifest.json", "dataset-manifest.json", "quality-report.json", "fingerprint.json"})
            shutil.rmtree(first)
            second = self._import(root, archive)
            self.assertEqual(first_bytes, {path.name: path.read_bytes() for path in second.iterdir()})
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_chronological_split_strategies_boundaries_counts_and_benchmark_indices(self):
        root = self._workspace()
        try:
            output = self._import(root, self._csv_zip(root.parent))
            rows = [json.loads(line) for line in (output / "observations.jsonl").read_text(encoding="utf-8").splitlines()]
            split = load_json(output / "split-manifest.json")
            self.assertEqual([item["strategy"] for item in split["strategies"]], ["chronological"])
            chronological = split["strategies"][0]
            self.assertEqual(
                [(item["split_id"], item["record_count"]) for item in chronological["splits"]],
                [("train", 864), ("validation", 288), ("test", 288)],
            )
            timestamps = [datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00")) for row in rows]
            for item, expected_count in zip(chronological["splits"], (864, 288, 288)):
                start = datetime.fromisoformat(item["start_timestamp"].replace("Z", "+00:00"))
                end = datetime.fromisoformat(item["end_timestamp"].replace("Z", "+00:00"))
                covered = [timestamp for timestamp in timestamps if start <= timestamp < end]
                self.assertEqual(len(covered), expected_count)
                self.assertEqual(covered[-1] + timedelta(minutes=1), end)
            self.assertEqual(_split_indices_for_rows(rows, chronological, "metropt3-apu-01"), {"train": (0, 864), "validation": (864, 1152), "test": (1152, 1440)})
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_existing_output_is_rejected_before_source_prepare(self):
        root = self._workspace()
        try:
            output = root / "artifacts/public-datasets/metropt3-public-2020-02-21"
            output.mkdir(parents=True)
            sentinel = output / "sentinel"
            sentinel.write_text("keep", encoding="utf-8")
            with patch.object(import_metropt3, "prepare_source") as prepared:
                with self.assertRaisesRegex(import_metropt3.MetroPT3ImportError, "overwrite"):
                    import_metropt3.import_metropt3(
                        root.parent / "cache",
                        root / "examples/configs/metropt3-public-2020-02-21.json",
                        accepted=True,
                        root=root,
                    )
            prepared.assert_not_called()
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_publish_lock_contention_fails_before_source_prepare_or_transform(self):
        root = self._workspace()
        try:
            parent = root / "artifacts/public-datasets"
            parent.mkdir(parents=True)
            lock = parent / ".metropt3-public-2020-02-21.publish.lock"
            lock.write_text("owner", encoding="utf-8")
            with patch.object(import_metropt3, "prepare_source") as prepared, patch.object(import_metropt3, "_stream_transform") as transformed:
                with self.assertRaisesRegex(import_metropt3.MetroPT3ImportError, "already in progress"):
                    import_metropt3.import_metropt3(
                        root.parent / "cache",
                        root / "examples/configs/metropt3-public-2020-02-21.json",
                        accepted=True,
                        root=root,
                    )
            prepared.assert_not_called()
            transformed.assert_not_called()
            self.assertEqual(lock.read_text(encoding="utf-8"), "owner")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_artifacts_or_intermediate_parent_symlink_is_rejected(self):
        root = self._workspace()
        try:
            outside = root.parent / "outside-public-data"
            outside.mkdir()
            try:
                (root / "artifacts").symlink_to(outside, target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"directory symlink is unavailable: {exc}")
            with patch.object(import_metropt3, "prepare_source") as prepared:
                with self.assertRaises(import_metropt3.MetroPT3ImportError):
                    import_metropt3.import_metropt3(root.parent / "cache", accepted=True, root=root)
            prepared.assert_not_called()
            self.assertFalse((outside / "public-datasets").exists())
        finally:
            shutil.rmtree(root, ignore_errors=True)
            shutil.rmtree(root.parent / "outside-public-data", ignore_errors=True)

    def test_header_missing_nonfinite_reverse_empty_bin_gap_and_timezone_fail_closed(self):
        cases = {
            "header": lambda values, _bin, _sample: None,
            "missing": lambda values, bin_index, sample: values.__setitem__(2, "") if bin_index == 10 and sample == 0 else None,
            "nonfinite": lambda values, bin_index, sample: values.__setitem__(2, "nan") if bin_index == 10 and sample == 0 else None,
            "timezone": lambda values, bin_index, sample: values.__setitem__(1, "2020-02-21T00:00:30Z") if bin_index == 0 and sample == 0 else None,
        }
        for name, mutate in cases.items():
            with self.subTest(name=name):
                root = self._workspace()
                try:
                    archive = self._csv_zip(root.parent, mutate_header=(lambda header: header.__setitem__(2, "WRONG")) if name == "header" else None, mutate_rows=mutate)
                    with self.assertRaises(import_metropt3.MetroPT3ImportError):
                        import_metropt3._stream_transform(archive, self._config())
                finally:
                    shutil.rmtree(root, ignore_errors=True)

        for name, mutate_rows in {
            "reverse": lambda values, bin_index, sample: values.__setitem__(1, "2020-02-20 23:59:59") if bin_index == 10 and sample == 0 else None,
            "duplicate": lambda values, bin_index, sample: values.__setitem__(1, "2020-02-21 00:10:30") if bin_index == 10 and sample == 1 else None,
            "large_gap": lambda values, bin_index, sample: values.__setitem__(1, "2020-02-21 00:03:00") if bin_index == 2 and sample == 0 else None,
            "empty_bin": lambda values, bin_index, sample: values.__setitem__(1, "2020-02-21 00:02:00") if bin_index == 1 else None,
        }.items():
            with self.subTest(name=name):
                root = self._workspace()
                try:
                    archive = self._csv_zip(root.parent, mutate_rows=mutate_rows)
                    with self.assertRaises(import_metropt3.MetroPT3ImportError):
                        import_metropt3._stream_transform(archive, self._config())
                finally:
                    shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
