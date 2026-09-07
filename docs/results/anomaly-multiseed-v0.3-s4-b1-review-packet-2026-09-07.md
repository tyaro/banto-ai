# S4-B1 cleanup / replacement evidence 独立レビュー用資料

状態: **review prepared / independent review pending / all acceptance gates no**。
資料作成は実装者による整理であり、独立レビュー結果ではない。

## 固定対象

- 候補実装: `f2f2d95`（branch `codex/s4-b1-windows-engineering`）。
- 比較基準: 最後の独立監査済み実装 `16a037f`。
- 本流基準: `889cfc3d5e1fd6dd7fc6c9656273d16d7d56d64e`。
- 対象差分: cleanup snapshot/状態遷移、native adapter、result evidence所有、
  replacement trace、child protocol `b1.2`、その後のfailure-path修正。
- 既知残件: required restricted-childが`0xC0000142`で停止する問題。
  このレビューでE2E成功や起動障害解消を仮定しない。

レビュー開始時にHEADとdirty状態を確認する。資料だけの後続commitは許容するが、
実装が変わっていれば対象hashを明示し、未確認の変更まで承認しない。

## 最小読取順

1. [引継書](anomaly-multiseed-v0.3-s4-b1-handoff-2026-09-07.md) §6〜7と§11以降。
2. [記録契約](../anomaly-v03-cleanup-evidence-design.md)。冒頭の最新状態と各checkpointを区別する。
3. `git diff 16a037f f2f2d95 -- src/banto_ai/_anomaly_v03_windows.py tests/fixtures/anomaly_v03_native_child.py`
4. 下表に対応する実装・試験。必要な既存calleeだけ追加で読む。

| 境界 | 実装 | 主な回帰試験 |
| --- | --- | --- |
| immutable snapshotと進捗 | CapturedObject / CleanupJournal | test_anomaly_v03_cleanup.py |
| 変更前検証、ACL→削除→close→absence | _Fixture.capture_cleanup / cleanup / close | test_anomaly_v03_cleanup_native.py |
| primary failureとprivate evidence寿命 | run_control_harness / _ControlOutcome / _finish_outcome | CleanupAdapterTests、PureWindowsControls |
| source/置換先の原状と部分操作 | _ReplaceTrace / _replace_control | test_anomaly_v03_replace_trace.py |
| untrusted bytesの受理境界 | _validate_replace_trace / _capture_replace_trace | ReplacementTraceTests |
| childの停止と証跡回収 | _child_main、child wrapper、harness | bootstrap MemoryError / exit 80 / capture fault試験 |
| 正常・拒否・異常の区別 | _operations | PureWindowsControls、同一parent native controls |

## 必ず反証を試す契約

1. 最初のACL変更前に全snapshotが確定し、元ledgerとmutable参照を共有しない。
2. 削除済みobjectの元bytes/SD/identityがresult寿命まで残る。digestだけで代替しない。
3. ACL変更、disposition、close、absenceを区別し、権限不足・親不存在をabsenceにしない。
4. mutation成功直後の失敗をunknownにする。失敗後にrepair・再cleanup・foreign object採用をしない。
5. resource stop後はfilesystem read/hash/scanを追加しない。handle/process teardownは継続し、
   一次失敗を二次失敗で上書きしない。report生成はresource handlerの安全性を仮定しない。
6. replacementのintentをmutation前に記録する。write/flush失敗でmutationへ進まない。
   targetの元identity/content/SDとsource位置の不確実性を区別し、成功扱いを早めない。
7. traceのnonce、順序、chain、型、snapshot pins、全tail bytesを検証する。
   chainを再計算できる入力でもpinとの不一致を受理しない。
8. child resource exitでは回収しない。通常child failureの回収失敗でもchild原因を保持する。
9. public JSON/reprへprivate SID/SD/content/絶対temp pathを出さない。
10. overall/control/cleanup/teardownの状態を混同しない。失敗時のtop-level residue 0を残さない。

特に、テストが実装を写しただけで反証できていない境界、実行前に例外が起きるallocation、
handle所有権が失われる経路、実APIとfake modelの意味の違いを探す。

## 実行範囲と既存検証

まずread-onlyレビューとpure/fault試験に限定する。実childやnative mutationは実行しない。
テストfixtureのfakeはWindows E2Eの証明ではない。全suiteはrequired childを含むため実行しない。

```powershell
python -B -m unittest tests.test_anomaly_v03_replace_trace.ReplacementTraceTests tests.test_anomaly_v03_cleanup_native tests.test_anomaly_v03_cleanup tests.test_anomaly_v03_windows.PureWindowsControls -q
```

既存結果: 98/98 pure/fault、同一parent native 2/2、D2 exact inventory 1/1、safety pass。
Windows 3.12、full suite、restricted-child成功は未確認。
既存artifact/failure rootは変更・削除・ACL復元・再利用しない。
追加production source file、D2 pin更新、science config変更、formal run、merge/pushは対象外。

## レビュー結果に必要な形式

- 調査した実装hashと比較基準、実際に実行したテスト。
- actionable findingごとにP0〜P3、file/line、成立条件、影響、具体的な反例。
- findingsがない場合も、未確認範囲と既知起動blockerを明記する。
- cleanup/evidenceの各契約について「確認済み／問題あり／未確認」を区別する。
- 保存可能性、追加診断準備、main統合、native acceptance、formal permissionを分ける。
  起動blockerが残る間、main統合・native acceptance・formal permissionはno。

起動障害のread-only調査は[別記録](anomaly-multiseed-v0.3-s4-b1-startup-triage-2026-09-07.md)を参照。
