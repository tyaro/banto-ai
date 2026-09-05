"""Deterministic, side-effect-free renderer for D2-A diagnostics results."""

from __future__ import annotations

from banto_ai.anomaly_failure_diagnostics import AnomalyFailureDiagnosticsError, VerifiedDiagnosticsResult


def render_summary(result: VerifiedDiagnosticsResult) -> bytes:
    """Render only a sealed, immutable result issued by the complete replay API."""
    if type(result) is not VerifiedDiagnosticsResult:
        raise AnomalyFailureDiagnosticsError("summary rendering requires a VerifiedDiagnosticsResult from the replay API")
    counts = result.get("counts", {})
    ledger = result.get("ledger", {})
    lines = [
        "# 異常検知マルチシード失敗診断 v0.1",
        "",
        f"- ステータス: `{result.get('status')}`",
        f"- 実行ステータス: `{result.get('run_status')}`",
        f"- エンジニアリング判定: `{result.get('engineering_status')}`",
        "- 性能判定: `not_evaluated`（D2-Aでは実施しない）",
        "- 探索専用: `true`",
        "- 昇格対象: `false`",
        "",
        "## 固定カウント",
        "",
    ]
    for key in ("cells", "eligible_incident_windows", "combined_incident_point_rows", "score_availability_source_points", "availability_group_rows", "calibration_profile_rows", "clean_aggregate_rows"):
        lines.append(f"- {key}: `{counts.get(key)}`")
    lines.extend([
        "",
        "## 台帳",
        "",
        f"- incident_windows: `{len(ledger.get('incident_windows', []))}`",
        f"- incident_points: `{len(ledger.get('incident_points', []))}`",
        f"- clean_source_alerts: `{len(ledger.get('clean_source_alerts', []))}`",
        f"- clean_equipment_alerts: `{len(ledger.get('clean_equipment_alerts', []))}`",
        f"- availability: `{len(ledger.get('availability', []))}`",
        f"- calibration_profiles: `{len(ledger.get('calibration_profiles', []))}`",
        "",
        "D2-Aは、固定された入力成果物の読み取り専用リプレイと、台帳・集計・照合の検証までを対象とする。公開、制御系書込み、性能評価、昇格判定は行わない。",
        "",
    ])
    return "\n".join(lines).encode("utf-8")
