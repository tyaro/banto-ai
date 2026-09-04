from __future__ import annotations

import json
import hashlib
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from banto_ai.generator import GeneratorError, _resolve_output, generate_synthetic
from banto_ai.manifest import ManifestValidationError, load_json, validate_manifest
from banto_ai.quality import DatasetQualityError, check_dataset


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "examples" / "configs" / "synthetic-motor-small.json"


class Phase1GeneratorTests(unittest.TestCase):
    def _config(self, directory: Path, seed: int = 42) -> Path:
        value = load_json(CONFIG)
        value["seed"] = seed
        path = directory / f"config-{seed}.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    @staticmethod
    def _refresh_fingerprint(output: Path) -> None:
        names = ("generator-config.json", "observations.jsonl", "events.jsonl", "split-manifest.json", "dataset-manifest.json")
        hashes = {name: hashlib.sha256((output / name).read_bytes()).hexdigest() for name in names}
        canonical = "".join(f"{name}\n{digest}\n" for name, digest in sorted(hashes.items())).encode("utf-8")
        fingerprint = load_json(output / "fingerprint.json")
        fingerprint["files"] = hashes
        fingerprint["dataset_fingerprint"] = hashlib.sha256(canonical).hexdigest()
        (output / "fingerprint.json").write_text(json.dumps(fingerprint), encoding="utf-8")
        summary = load_json(output / "summary.json")
        summary["dataset_fingerprint"] = fingerprint["dataset_fingerprint"]
        (output / "summary.json").write_text(json.dumps(summary), encoding="utf-8")

    def test_same_seed_is_byte_for_byte_and_seed_changes_fingerprint(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = self._config(root)
            first = generate_synthetic(config, root / "one", ROOT)
            second = generate_synthetic(config, root / "two", ROOT)
            names = sorted(path.name for path in first.iterdir())
            self.assertEqual(names, sorted(path.name for path in second.iterdir()))
            for name in names:
                self.assertEqual((first / name).read_bytes(), (second / name).read_bytes(), name)
            changed = generate_synthetic(self._config(root, seed=43), root / "three", ROOT)
            self.assertNotEqual((first / "fingerprint.json").read_bytes(), (changed / "fingerprint.json").read_bytes())

    def test_output_has_separate_events_and_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = generate_synthetic(CONFIG, Path(directory) / "dataset", ROOT)
            summary = load_json(output / "summary.json")
            self.assertEqual(summary["equipment_count"], 2)
            self.assertEqual(summary["event_count"], 6)
            self.assertEqual(set(summary["event_coverage"]), {"sensor_drift", "spike", "dropout", "overheating_trend", "jam_or_slip", "stuck_value", "stale_value"})
            self.assertEqual(summary["event_coverage"]["stale_value"], 0)
            self.assertNotIn("event_type", json.loads((output / "observations.jsonl").read_text(encoding="utf-8").splitlines()[0]))
            self.assertTrue(json.loads((output / "events.jsonl").read_text(encoding="utf-8").splitlines()[0])["event_id"])

    def test_effective_default_magnitude_is_recorded_and_spike_covers_interval(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            value = load_json(CONFIG)
            spike = next(event for event in value["events"] if event["event_type"] == "spike")
            del spike["magnitude"]
            value["dataset_id"] = "synthetic-default-spike"
            config = root / "default-spike.json"
            config.write_text(json.dumps(value), encoding="utf-8")
            output = generate_synthetic(config, root / "with-spike", ROOT)
            event_rows = [json.loads(line) for line in (output / "events.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertEqual(next(row for row in event_rows if row["event_id"] == spike["event_id"])["magnitude"], 4.0)
            with_rows = [json.loads(line) for line in (output / "observations.jsonl").read_text(encoding="utf-8").splitlines()]
            value["dataset_id"] = "synthetic-no-spike"
            value["events"] = [event for event in value["events"] if event["event_type"] != "spike"]
            no_spike_config = root / "no-spike.json"
            no_spike_config.write_text(json.dumps(value), encoding="utf-8")
            no_spike = generate_synthetic(no_spike_config, root / "without-spike", ROOT)
            without_rows = [json.loads(line) for line in (no_spike / "observations.jsonl").read_text(encoding="utf-8").splitlines()]
            for index in (46, 47):
                self.assertAlmostEqual(with_rows[index]["signals"]["vibration_feature"]["value"] - without_rows[index]["signals"]["vibration_feature"]["value"], 4.0)
            self.assertEqual(with_rows[48]["signals"]["vibration_feature"], without_rows[48]["signals"]["vibration_feature"])

    def test_stale_value_event_is_fixed_stale_and_fingerprinted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            value = load_json(CONFIG)
            value["dataset_id"] = "synthetic-stale-value"
            value["events"].append({
                "event_id": "motor-01-load-stale",
                "event_type": "stale_value",
                "equipment_id": "motor-01",
                "signal_id": "load_proxy",
                "start_sample": 50,
                "end_sample": 54,
                "enabled": True,
            })
            config = root / "stale-value.json"
            config.write_text(json.dumps(value), encoding="utf-8")
            validate_manifest(config, ROOT / "schemas" / "synthetic-generator-config.schema.json")
            output = generate_synthetic(config, root / "dataset", ROOT)
            self.assertEqual(check_dataset(output, ROOT)["status"], "pass")
            rows = [json.loads(line) for line in (output / "observations.jsonl").read_text(encoding="utf-8").splitlines()]
            motor_rows = [row for row in rows if row["equipment_id"] == "motor-01"]
            stale_rows = motor_rows[50:54]
            stale_values = [row["signals"]["load_proxy"]["value"] for row in stale_rows]
            self.assertEqual(len(set(stale_values)), 1)
            self.assertTrue(all(row["quality"]["load_proxy"] == "stale" for row in stale_rows))
            self.assertTrue(all(value is not None for value in stale_values))
            events = [json.loads(line) for line in (output / "events.jsonl").read_text(encoding="utf-8").splitlines()]
            stale_event = next(event for event in events if event["event_id"] == "motor-01-load-stale")
            self.assertEqual(stale_event["event_type"], "stale_value")
            summary = load_json(output / "summary.json")
            self.assertEqual(summary["event_coverage"]["stale_value"], 1)
            fingerprint = load_json(output / "fingerprint.json")
            self.assertEqual(fingerprint["files"]["events.jsonl"], hashlib.sha256((output / "events.jsonl").read_bytes()).hexdigest())
            conveyor_rows = [row for row in rows if row["equipment_id"] == "conveyor-01"]
            stuck_rows = conveyor_rows[49:55]
            self.assertEqual(len({row["signals"]["load_proxy"]["value"] for row in stuck_rows}), 1)
            self.assertTrue(all(row["quality"]["load_proxy"] == "ok" for row in stuck_rows))
            dropout_row = next(row for row in rows if row["equipment_id"] == "conveyor-01" and row["signals"]["motor_temperature"]["value"] is None)
            self.assertEqual(dropout_row["quality"]["motor_temperature"], "missing")

    def test_quality_gate_rejects_stale_null_and_ok_null_but_accepts_finite_stale(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            value = load_json(CONFIG)
            value["dataset_id"] = "synthetic-stale-quality"
            value["events"].append({
                "event_id": "motor-01-load-stale",
                "event_type": "stale_value",
                "equipment_id": "motor-01",
                "signal_id": "load_proxy",
                "start_sample": 50,
                "end_sample": 54,
                "enabled": True,
            })
            config = root = Path(directory) / "stale-quality.json"
            config.write_text(json.dumps(value), encoding="utf-8")
            output = generate_synthetic(config, root.parent / "dataset", ROOT)
            self.assertEqual(check_dataset(output, ROOT)["status"], "pass")
            observation_path = output / "observations.jsonl"
            rows = [json.loads(line) for line in observation_path.read_text(encoding="utf-8").splitlines()]
            stale = next(row for row in rows if row["equipment_id"] == "motor-01" and row["quality"]["load_proxy"] == "stale")
            stale["signals"]["load_proxy"]["value"] = None
            observation_path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
            with self.assertRaises(DatasetQualityError):
                check_dataset(output, ROOT)
            clean_config = Path(directory) / "ok-null.json"
            clean_value = load_json(CONFIG)
            clean_value["dataset_id"] = "synthetic-ok-null"
            clean_config.write_text(json.dumps(clean_value), encoding="utf-8")
            clean_output = generate_synthetic(clean_config, Path(directory) / "ok-null-dataset", ROOT)
            clean_observation_path = clean_output / "observations.jsonl"
            clean_rows = [json.loads(line) for line in clean_observation_path.read_text(encoding="utf-8").splitlines()]
            clean_rows[0]["signals"]["load_proxy"]["value"] = None
            clean_observation_path.write_text("\n".join(json.dumps(row) for row in clean_rows) + "\n", encoding="utf-8")
            with self.assertRaises(DatasetQualityError):
                check_dataset(clean_output, ROOT)

    def test_quality_changing_overlap_is_rejected_disabled_is_ignored_and_touching_is_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = load_json(CONFIG)
            base["dataset_id"] = "synthetic-quality-event-boundaries"
            dropout = {
                "event_id": "motor-01-current-dropout",
                "event_type": "dropout",
                "equipment_id": "motor-01",
                "signal_id": "motor_current",
                "start_sample": 10,
                "end_sample": 14,
                "enabled": True,
            }
            stale = {
                "event_id": "motor-01-current-stale",
                "event_type": "stale_value",
                "equipment_id": "motor-01",
                "signal_id": "motor_current",
                "start_sample": 13,
                "end_sample": 16,
                "enabled": True,
            }
            overlap = json.loads(json.dumps(base))
            overlap["events"].extend((dropout, stale))
            overlap_path = Path(directory) / "overlap.json"
            overlap_path.write_text(json.dumps(overlap), encoding="utf-8")
            with self.assertRaisesRegex(GeneratorError, "quality-changing event intervals overlap"):
                generate_synthetic(overlap_path, Path(directory) / "overlap-dataset", ROOT)

            disabled = json.loads(json.dumps(overlap))
            disabled["dataset_id"] = "synthetic-quality-event-disabled"
            disabled["events"][-1]["enabled"] = False
            disabled_path = Path(directory) / "disabled-overlap.json"
            disabled_path.write_text(json.dumps(disabled), encoding="utf-8")
            disabled_output = generate_synthetic(disabled_path, Path(directory) / "disabled-dataset", ROOT)
            self.assertEqual(check_dataset(disabled_output, ROOT)["status"], "pass")

            touching = json.loads(json.dumps(base))
            touching["dataset_id"] = "synthetic-quality-event-touching"
            touching_stale = dict(stale, start_sample=14, end_sample=16)
            touching["events"].extend((dropout, touching_stale))
            touching_path = Path(directory) / "touching.json"
            touching_path.write_text(json.dumps(touching), encoding="utf-8")
            output = generate_synthetic(touching_path, Path(directory) / "touching-dataset", ROOT)
            self.assertEqual(check_dataset(output, ROOT)["status"], "pass")
            rows = [json.loads(line) for line in (output / "observations.jsonl").read_text(encoding="utf-8").splitlines()]
            motor_rows = [row for row in rows if row["equipment_id"] == "motor-01"]
            self.assertTrue(all(row["quality"]["motor_current"] == "ok" for row in (motor_rows[9:10] + motor_rows[16:17])))
            self.assertTrue(all(row["quality"]["motor_current"] == "missing" and row["signals"]["motor_current"]["value"] is None for row in motor_rows[10:14]))
            stale_rows = motor_rows[14:16]
            self.assertTrue(all(row["quality"]["motor_current"] == "stale" for row in stale_rows))
            self.assertEqual(len({row["signals"]["motor_current"]["value"] for row in stale_rows}), 1)

    def test_quality_gate_rejects_quality_status_outside_event_and_rehashed_stale_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            value = load_json(CONFIG)
            value["dataset_id"] = "synthetic-quality-tamper"
            value["events"].append({
                "event_id": "motor-01-load-stale",
                "event_type": "stale_value",
                "equipment_id": "motor-01",
                "signal_id": "load_proxy",
                "start_sample": 50,
                "end_sample": 54,
                "enabled": True,
            })
            config = Path(directory) / "tamper.json"
            config.write_text(json.dumps(value), encoding="utf-8")
            output = generate_synthetic(config, Path(directory) / "dataset", ROOT)
            rows = [json.loads(line) for line in (output / "observations.jsonl").read_text(encoding="utf-8").splitlines()]
            motor_rows = [row for row in rows if row["equipment_id"] == "motor-01"]
            motor_rows[49]["quality"]["load_proxy"] = "stale"
            motor_rows[49]["signals"]["load_proxy"]["value"] = 123.0
            (output / "observations.jsonl").write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
            self._refresh_fingerprint(output)
            with self.assertRaises(DatasetQualityError):
                check_dataset(output, ROOT)

            value["dataset_id"] = "synthetic-quality-stale-tamper"
            config.write_text(json.dumps(value), encoding="utf-8")
            output = generate_synthetic(config, Path(directory) / "stale-dataset", ROOT)
            rows = [json.loads(line) for line in (output / "observations.jsonl").read_text(encoding="utf-8").splitlines()]
            motor_rows = [row for row in rows if row["equipment_id"] == "motor-01"]
            motor_rows[51]["signals"]["load_proxy"]["value"] += 1.0
            (output / "observations.jsonl").write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
            self._refresh_fingerprint(output)
            with self.assertRaisesRegex(DatasetQualityError, "stale_value must remain fixed"):
                check_dataset(output, ROOT)

    def test_disabled_event_with_unknown_signal_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            value = load_json(CONFIG)
            value["events"][-1]["signal_id"] = "unknown_signal"
            path = Path(directory) / "invalid-disabled-event.json"
            path.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaises(GeneratorError):
                generate_synthetic(path, Path(directory) / "out", ROOT)

    def test_manifests_quality_and_splits(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = generate_synthetic(CONFIG, Path(directory) / "dataset", ROOT)
            validate_manifest(output / "dataset-manifest.json", ROOT / "schemas" / "dataset-manifest.schema.json")
            validate_manifest(output / "split-manifest.json", ROOT / "schemas" / "split-manifest.schema.json")
            result = check_dataset(output, ROOT)
            self.assertEqual(result["status"], "pass")

    def test_clean_checkout_entrypoints_generate_and_check_quality(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "clean-checkout-dataset"
            environment = os.environ.copy()
            environment.pop("PYTHONPATH", None)
            generate = subprocess.run(
                [sys.executable, "tools/data-generator/generate.py", "--config", "examples/configs/synthetic-motor-small.json", "--output", str(output)],
                cwd=ROOT,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(generate.returncode, 0, generate.stdout + generate.stderr)
            quality = subprocess.run(
                [sys.executable, "tools/data-generator/check_quality.py", "--dataset", str(output)],
                cwd=ROOT,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(quality.returncode, 0, quality.stdout + quality.stderr)

    def test_overwrite_and_unsafe_output_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = generate_synthetic(CONFIG, root / "existing", ROOT)
            with self.assertRaises(GeneratorError):
                generate_synthetic(CONFIG, output, ROOT)
            with self.assertRaises(GeneratorError):
                _resolve_output(ROOT, Path("..") / "outside", "synthetic-motor-small")
            with self.assertRaises(GeneratorError):
                _resolve_output(ROOT, "../outside", "synthetic-motor-small")
            with self.assertRaises(GeneratorError):
                _resolve_output(ROOT, "..\\outside", "synthetic-motor-small")

    def test_quality_checker_detects_duplicate_gap_unit_and_leakage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = generate_synthetic(CONFIG, Path(directory) / "dataset", ROOT)
            observation_path = output / "observations.jsonl"
            lines = observation_path.read_text(encoding="utf-8").splitlines()
            original = lines[1]
            lines[1] = lines[0]
            observation_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            with self.assertRaises(DatasetQualityError):
                check_dataset(output, ROOT)
            observation_path.write_text("\n".join([lines[0], original] + lines[2:]), encoding="utf-8")
            row = json.loads(original)
            row["signals"]["conveyor_speed"]["unit"] = "A"
            observation_path.write_text("\n".join([json.dumps(row)] + lines[1:]) + "\n", encoding="utf-8")
            with self.assertRaises(DatasetQualityError):
                check_dataset(output, ROOT)

    def test_quality_checker_detects_unexpected_gap(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = generate_synthetic(CONFIG, Path(directory) / "dataset", ROOT)
            path = output / "observations.jsonl"
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            rows[1]["timestamp"] = "2026-01-01T00:00:03.000Z"
            path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
            with self.assertRaises(DatasetQualityError):
                check_dataset(output, ROOT)

    def test_quality_checker_uses_catalog_sampling_interval(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = generate_synthetic(CONFIG, Path(directory) / "dataset", ROOT)
            path = output / "dataset-manifest.json"
            manifest = load_json(path)
            for signal in manifest["signals"]:
                signal["sampling_interval_ms"] = 2000
            path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaises(DatasetQualityError):
                check_dataset(output, ROOT)

    def test_quality_checker_reconstructs_catalog_from_generator_definition(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = generate_synthetic(CONFIG, Path(directory) / "dataset", ROOT)
            manifest_path = output / "dataset-manifest.json"
            manifest = load_json(manifest_path)
            target = next(item for item in manifest["signals"] if item["signal_id"] == "motor-01.motor_current")
            target.update(name="wrong current", unit="kA", role="covariate")
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            observation_path = output / "observations.jsonl"
            rows = [json.loads(line) for line in observation_path.read_text(encoding="utf-8").splitlines()]
            for row in rows:
                if row["equipment_id"] == "motor-01":
                    row["signals"]["motor_current"]["unit"] = "kA"
            observation_path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
            self._refresh_fingerprint(output)
            with self.assertRaises(DatasetQualityError):
                check_dataset(output, ROOT)

    def test_fingerprint_verification_rejects_mutations_and_bad_entries(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = generate_synthetic(CONFIG, Path(directory) / "dataset", ROOT)
            observation_path = output / "observations.jsonl"
            original = observation_path.read_bytes()
            rows = [json.loads(line) for line in original.decode("utf-8").splitlines()]
            rows[0]["signals"]["motor_current"]["value"] = 123.456
            observation_path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
            with self.assertRaises(DatasetQualityError):
                check_dataset(output, ROOT)
            observation_path.write_bytes(original)
            fingerprint_path = output / "fingerprint.json"
            fingerprint = load_json(fingerprint_path)
            fingerprint["files"]["unexpected.json"] = "0" * 64
            fingerprint_path.write_text(json.dumps(fingerprint), encoding="utf-8")
            with self.assertRaises(DatasetQualityError):
                check_dataset(output, ROOT)
            fingerprint["files"].pop("unexpected.json")
            fingerprint["files"].pop("events.jsonl")
            fingerprint_path.write_text(json.dumps(fingerprint), encoding="utf-8")
            with self.assertRaises(DatasetQualityError):
                check_dataset(output, ROOT)

    def test_fingerprint_verification_rejects_missing_file_and_summary_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = generate_synthetic(CONFIG, Path(directory) / "dataset", ROOT)
            (output / "events.jsonl").unlink()
            with self.assertRaises(DatasetQualityError):
                check_dataset(output, ROOT)

    def test_fingerprint_and_summary_structure_fail_closed(self) -> None:
        fingerprint_mutations = {
            "extra_key": lambda value: value.update(extra=True),
            "canonicalization": lambda value: value.update(canonicalization="arbitrary"),
            "invalid_digest": lambda value: value.update(dataset_fingerprint="A" * 64),
            "short_file_digest": lambda value: value["files"].update({"events.jsonl": "0" * 63}),
        }
        for name, mutate in fingerprint_mutations.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                output = generate_synthetic(CONFIG, Path(directory) / "dataset", ROOT)
                path = output / "fingerprint.json"
                value = load_json(path)
                mutate(value)
                path.write_text(json.dumps(value), encoding="utf-8")
                with self.assertRaises(DatasetQualityError):
                    check_dataset(output, ROOT)
        summary_mutations = {
            "extra_key": lambda value: value.update(extra=True),
            "schema_version": lambda value: value.update(schema_version="0.2"),
            "summary_type": lambda value: value.update(summary_type="other"),
            "count_type": lambda value: value.update(equipment_count="2"),
        }
        for name, mutate in summary_mutations.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                output = generate_synthetic(CONFIG, Path(directory) / "dataset", ROOT)
                path = output / "summary.json"
                value = load_json(path)
                mutate(value)
                path.write_text(json.dumps(value), encoding="utf-8")
                with self.assertRaises(DatasetQualityError):
                    check_dataset(output, ROOT)
        with tempfile.TemporaryDirectory() as directory:
            output = generate_synthetic(CONFIG, Path(directory) / "dataset", ROOT)
            summary_path = output / "summary.json"
            summary = load_json(summary_path)
            summary["dataset_fingerprint"] = "0" * 64
            summary_path.write_text(json.dumps(summary), encoding="utf-8")
            with self.assertRaises(DatasetQualityError):
                check_dataset(output, ROOT)

    def test_quality_checker_detects_split_overlap(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = generate_synthetic(CONFIG, Path(directory) / "dataset", ROOT)
            path = output / "split-manifest.json"
            value = load_json(path)
            chronological = next(item for item in value["strategies"] if item["strategy"] == "chronological")
            chronological["splits"][1]["start_timestamp"] = chronological["splits"][0]["start_timestamp"]
            path.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaises(DatasetQualityError):
                check_dataset(output, ROOT)

    def test_quality_checker_detects_split_id_gap_coverage_count_and_equipment(self) -> None:
        mutations = {
            "duplicate_id": lambda value: value["strategies"][0]["splits"][1].update(split_id="train"),
            "gap": lambda value: value["strategies"][0]["splits"][1].update(start_timestamp="2026-01-01T00:00:37.000Z"),
            "uncovered_start": lambda value: value["strategies"][0]["splits"][0].update(start_timestamp="2026-01-01T00:00:01.000Z"),
            "uncovered_end": lambda value: value["strategies"][0]["splits"][-1].update(end_timestamp="2026-01-01T00:00:59.000Z"),
            "wrong_count": lambda value: value["strategies"][0]["splits"][0].update(record_count=1),
            "wrong_equipment": lambda value: value["strategies"][0]["splits"][0].update(equipment_ids=["motor-01"]),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                output = generate_synthetic(CONFIG, Path(directory) / "dataset", ROOT)
                path = output / "split-manifest.json"
                value = load_json(path)
                mutate(value)
                path.write_text(json.dumps(value), encoding="utf-8")
                with self.assertRaises(DatasetQualityError):
                    check_dataset(output, ROOT)

    def test_quality_checker_rejects_observation_structure_and_event_structure(self) -> None:
        observation_mutations = {
            "quality_key": lambda row: row["quality"].pop("load_proxy"),
            "quality_status": lambda row: row["quality"].update(load_proxy="unknown"),
            "mode": lambda row: row.update(operating_mode="unknown"),
            "recipe": lambda row: row.update(recipe_step=""),
            "equipment_type": lambda row: row.update(equipment_type="conveyor"),
            "event_label": lambda row: row.update(event_id="ground-truth"),
        }
        for name, mutate in observation_mutations.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                output = generate_synthetic(CONFIG, Path(directory) / "dataset", ROOT)
                path = output / "observations.jsonl"
                rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
                mutate(rows[0])
                path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
                with self.assertRaises(DatasetQualityError):
                    check_dataset(output, ROOT)
        event_mutations = {
            "duplicate_id": lambda rows: rows[1].update(event_id=rows[0]["event_id"]),
            "unknown_equipment": lambda rows: rows[0].update(equipment_id="unknown"),
            "unknown_signal": lambda rows: rows[0].update(signal_id="unknown"),
            "outside_period": lambda rows: rows[0].update(start_timestamp="2025-12-31T23:59:59.000Z"),
            "nonfinite": lambda rows: rows[0].update(magnitude=float("nan")),
        }
        for name, mutate in event_mutations.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                output = generate_synthetic(CONFIG, Path(directory) / "dataset", ROOT)
                path = output / "events.jsonl"
                rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
                mutate(rows)
                path.write_text("\n".join(json.dumps(row, allow_nan=True) for row in rows) + "\n", encoding="utf-8")
                with self.assertRaises(DatasetQualityError):
                    check_dataset(output, ROOT)

    def test_empty_event_file_is_supported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            value = load_json(CONFIG)
            value["dataset_id"] = "synthetic-no-events"
            value["events"] = []
            path = Path(directory) / "no-events.json"
            path.write_text(json.dumps(value), encoding="utf-8")
            output = generate_synthetic(path, Path(directory) / "dataset", ROOT)
            self.assertEqual(check_dataset(output, ROOT)["status"], "pass")

    def test_synthetic_manifest_requires_generated_fields(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = generate_synthetic(CONFIG, Path(directory) / "dataset", ROOT)
            path = output / "dataset-manifest.json"
            value = load_json(path)
            del value["fingerprint_path"]
            path.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaises(ManifestValidationError):
                check_dataset(output, ROOT)

    def test_quality_checker_rejects_config_semantic_mismatches_after_rehashed_fingerprint(self) -> None:
        mutations = {
            "start_timestamp": lambda config, summary: config.update(start_timestamp="2026-01-01T00:00:01Z"),
            "sample_count": lambda config, summary: (config.update(sample_count=59), [item.update(end_sample=min(item["end_sample"], 59)) for item in config["regimes"]]),
            "mode": lambda config, summary: config["regimes"][0].update(regime="nominal"),
            "summary_count": lambda config, summary: summary.update(observation_record_count=1),
            "event_magnitude": lambda config, summary: next(event.update(magnitude=99.0) for event in config["events"] if event["event_type"] == "spike"),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                output = generate_synthetic(CONFIG, Path(directory) / "dataset", ROOT)
                config_path = output / "generator-config.json"
                config = load_json(config_path)
                summary_path = output / "summary.json"
                summary = load_json(summary_path)
                mutate(config, summary)
                config_path.write_text(json.dumps(config), encoding="utf-8")
                summary_path.write_text(json.dumps(summary), encoding="utf-8")
                self._refresh_fingerprint(output)
                with self.assertRaises(DatasetQualityError):
                    check_dataset(output, ROOT)

    def test_invalid_config_fails_schema_validation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            value = load_json(CONFIG)
            del value["events"]
            path = Path(directory) / "invalid.json"
            path.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaises(GeneratorError):
                generate_synthetic(path, Path(directory) / "out", ROOT)
            with self.assertRaises(ManifestValidationError):
                validate_manifest(path, ROOT / "schemas" / "synthetic-generator-config.schema.json")


if __name__ == "__main__":
    unittest.main()
