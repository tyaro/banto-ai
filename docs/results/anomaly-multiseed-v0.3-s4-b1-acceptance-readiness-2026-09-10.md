# S4-B1 成功後の受入条件と追加回帰確認

日付: 2026-09-10。初回照合の基準HEAD `f9244a735dff982cfce7d1493efda9431bc31b42`。
補完テスト修正savepoint: `cdbc0a1`。Windows3.14.0一本化の実装savepoint: `9fd3490`。
2026-09-11追記: Linux CI固定・unittest記録の実装は `3c69f9e`。
[CI整備・実行記録](anomaly-multiseed-v0.3-s4-b1-ci-evidence-2026-09-11.md)を参照。
本流 `889cfc3` は変更なし。

限定Windows engineering controlの成功は[前回結果](anomaly-multiseed-v0.3-s4-b1-operation-context-result-2026-09-10.md)を参照。
今回native controlを追加実行していない。最大3回枠は前回の1回目成功で終了している。

## 現行の受入条件と到達範囲

[計画§8](../anomaly-multiseed-evaluation-plan-v0.3.md#v03-runtime-acceptance)、
`_anomaly_v03_runtime.acceptance_requirements()`、CI定義を照合した。
以下はWindows3.14.0への一本化を適用した現行条件。以前のWindows3.12要件を復活させない。

| 境界 | 必須条件 | 現在の証拠・残件 |
| --- | --- | --- |
| B1 engineering control | 子のruntime/source/token、実AccessCheck、全操作、置換証跡、所有物cleanup/teardown | 実装 `0b30e63` / 実行HEAD `f15af39` / Windows 26200.9445 / Python 3.14.0で限定成功。全48期待値、9対象削除、残存0。全S4受入とは別 |
| Linux共通契約 | Ubuntu 24.04 x86_64、Python 3.12/3.14、共通契約と既存stdlib全回帰、safety、実patch/build・image・source・各test結果の記録 | `ubuntu-24.04`へ固定し、両minorのCIと逐次unittest記録を準備。候補3c69f9eのCI run 34514721185が進行中。VM image digestは未収集。過去の本流CI greenは候補の証拠に代用しない |
| Windows native受入 | 正式3.14.0の1 runtime。共通回帰、publisher、DACL、独立token/process、競合・非上書き・失敗証跡 | Windows3.12要件を削除済み。各必須検査自体は維持し、全native受入は未完了 |
| B2 publisher/marker | 新規fixtureで公開・非上書き・競合・marker・失敗証跡を検証 | B1のcontrol成功で完了扱いにしない。未実装・未受入の残件として分離 |
| S4全体 | 必須platform受入、完全runtime inventory、producer/consumer revision凍結、正式pin上のdev/smoke | 未完了。`require_campaign_acceptance()` は `s4_acceptance_not_frozen` を無条件に返す |
| 正式OS pin | 現行計画・registry・S3 runtimeは26200.9168。正式Pythonは3.14.0 | B1 engineeringではユーザー了承によりUBRを記録する方式へ緩和済み。9445での限定成功を正式pinの更新と扱わない。正式段階へ進む前に計画・実装・registryの整合と独立監査・受入が必要 |

Windowsで必須native試験をskip・未実行・失敗のまま受入passにしない。
Linuxの明示的なWindows項目skipは現行計画の許容範囲だが、Windows受入の代替ではない。
直近293件は `test_anomaly_v03_debug_*`、child diagnostics、startup events/preflight、
`PureWindowsControls` の選抜群であり、全repository回帰・全pure/fakeを網羅する数ではない。

## 追加検証と修正

既存選抜に含まれていなかった次の5クラスだけを明示して実行した。
隣接する `NativeReplacementTraceTests` / `NativeWindowsControls` は実行していない。

| クラス | 件数 | 性質 |
| --- | ---: | --- |
| `CleanupEvidenceTests` | 15 | pure evidence/cleanupモデル |
| `CleanupAdapterTests` | 13 | in-memory Win32モデルによるfake adapter。ファイル名のnativeは実機実行を意味しない |
| `ReplacementTraceTests` | 15 | fake trace、child wrapperの注入失敗、resource優先処理 |
| `OfflineSymbolTests` | 8 | 合成PDB bytes |
| `OfflineUnwindTests` | 16 | 合成PE/stack bytes、Capstone使用 |

初回67件は66 pass / 1 fail / skip0、0.343576秒。
`test_child_import_memory_failure_uses_resource_exit_before_classifier_is_available` が、
旧汎用exit1を期待していた。現行の固定bootstrap診断ではImportErrorは97である。
テストの期待値を97へ更新し、不在確認を既に使用しない `_resource_stop` から
実際の共有classifier `_child_failure_exit` へ変更した。MemoryErrorのexit80を維持する。
runtime・child wrapper・token・ACL・正式入口には変更がない。

修正後は上記67件＋既存 `ChildDiagnostics` 10件＋D2 current-only/historical exact inventory 1件の
計78件を実行し、全pass / failure0 / error0 / skip0 / expected failure0 / unexpected success0。
D2の1件はGit上のhistorical 88 pathsとcurrent-only 32 pathsの読み取り照合であり、
正式artifactへのアクセスやD2/S3の全長期回帰ではない。

最初の修正後78件は実環境Capstone 5.0.9で9.677579秒。
`pyproject.toml` のoptional extra固定5.0.7と差があったため、固定環境の受入証拠には数えなかった。
PyPIの5.0.7 Windows AMD64 wheelを専用ignoredフォルダーへ展開し、import元と版を確認して
同じ78件を再実行。**固定5.0.7で78/78 pass、10.504489秒**を今回の最終結果とする。
テスト時のPythonは既存3.14.0、base HEADはf9244a7、未commit差分はこのテスト修正1ファイルだけ。
検証したファイルのraw SHA-256は
`6b2816678d25aae0024edff293eac2e7de0a2a2ee2d3a7c1dcca4b1f0e409235`。
その差分を `cdbc0a1` へ保存した。

共有環境のCapstone 5.0.9は変更していない。wheelの追加依存取得・pip実行・PATH/registry変更なし。
取得元は[PyPI 5.0.7 metadata](https://pypi.org/pypi/capstone/5.0.7/json)。
wheel `capstone-5.0.7-py3-none-win_amd64.whl` は1,272,204 bytes、SHA-256
`4ab8bcb7da8f221ff45926ca168ca33e76f7237d06fbf3c10780002faa2670e1` を照合した。
展開前に件数・総サイズ・各pathの専用root内包を検査し、63 members / 8,409,204展開bytes。
取得wheel自体はメモリ内で検査し、展開物だけを保存した。

小さな実行記録は `artifacts/context-offline-2026-09-10/` に保存する。

| 記録 | bytes | SHA-256 |
| --- | ---: | --- |
| `acceptance-supplement-pure.json`（初回失敗） | 9734 | `1b75437afe36147120cb030dfe28e302eec086dde9156e415c4ff355500a9b24` |
| `acceptance-supplement-pure-fixed.json`（5.0.9） | 11157 | `da2fadc191637327fe716804770d6e3b432d5ef48a6afb1f33781b8000d88b52` |
| `acceptance-supplement-pure-pinned.json`（5.0.7最終） | 11269 | `e3ae54870d12bda5c218c40352dce8069c995cc75e89ea8e3cfaee98622ee334` |

各記録に正確なtest ID・選抜クラス・Python・source条件・pass/fail/skip・所要時間を保存した。
`acceptance-capstone-pin.json` は取得元・wheel hash・展開量の記録である。
これらは選抜回帰の証拠であり、全回帰・Windows native・完全runtime inventoryの代替ではない。
独立差分レビューは新規P0〜P3=0、レビュー担当の試験/native/API呼出/編集なし。進捗ポーリングなし。
repository safety / diff-check pass。

## Windows 3.14.0への一本化を採択

ユーザー「3.12必要？」に対し、現在の3.14.0での動作に追加3.12は不要と回答し、
Windows受入を3.14.0に一本化してLinuxの3.12/3.14 CIを維持する案を提示した。
その後の「続けてください」をこの方針への了承として受領し、実装を `9fd3490` へ保存した。
現在のWindows運用と同じPCの別project連続稼働を踏まえたplatform範囲の判断であり、
正式な性能結果に基づく事後選択ではない。3.12の導入・起動・source buildは行わない。

計画§8と `acceptance_requirements().windows_python` を `["3.14.0"]` にそろえた。
Linuxの2 jobs、`requires-python >=3.12`、科学config/schema/registryと歴史的な科学・status revision、
正式3.14.0のruntime/hash判定、正式OS pin9168、未受入を拒否する入口は維持する。
改訂した現行planはcandidate source inventoryに含め、過去の科学plan snapshotを上書きしない。

S4-A inspectionの要件・schema・pure validator・collectorにもWindows3.12が残っていたため同期した。
新しいreceipt revisionは **`s4-a.2`**。engineering schemaの既存pathはD2 current-onlyのexact pathsを保つため維持する。
旧`s4-a.1`や`windows-3.12`を含むreceiptは現validatorで拒否し、過去の記録を新形式へ自動変換しない。
新形式でも全項目は`not_completed`、formal permissionはfalseである。
collectorはWindows3.12および3.14.1などを対象path検査・source収集・native inventoryより前に拒否する。
Linux3.12/3.14のcompatibility-only観測は継続し、正式実行へ読み替えない。
Windows3.14.0では従来と同じ正式基本pin照合を要求する。B1の9445での限定成功はその受入証拠ではない。

関連25件をPython3.14.0で実行し、**25/25 pass、10.286753秒、failure/error/skip0**。
内訳はAcceptanceContractTests15、選抜ReadOnlyCollectorTests4、publication要件1、
runner拒否境界1、科学・歴史plan pin検証3、D2 exact inventory1。
旧receipt/旧要件拒否、Windows3.12拒否の順序、両Linux minorの継続、fresh collector結果、
科学pinと全未受入状態を確認した。full suite・native control・campaignは実行していない。
通常の小さなテスト用temp領域だけを作成・終了時清掃し、B1の既存失敗fixtureは操作していない。

実行時base HEADは `56f6a69`、検証対象は保存した8ファイルの差分。
`windows314-acceptance-tests.json` にtest IDs・各source hash・差分hash・各結果を保存した。
記録6268 bytes、SHA-256 `dbcc0b679aebae32423d5fe83cef65f3506ea2d6fbb685f804ad34c82da8c0c5`。
検証したstaged diff SHA-256は `ff6f998e990b37f27d1142e5071cc21384f4f9b4bde799b21692c61e7a7c4100`。
独立差分レビュー新規P0〜P3=0、担当の試験/native/編集なし。進捗ポーリングなし。
repository safety/diff-check pass。今回の一本化は必須native検査・B2/S4残件の完了ではない。

## 資源と保全

| 観測UTC | 空きRAM GiB | C空き GiB | D空き GiB |
| --- | ---: | ---: | ---: |
| 10:10:49 | 8.28 | 108.16 | 75.36 |
| 10:18:24 | 7.82 | 107.66 | 75.36 |
| 10:25:02 | 8.33 | 107.66 | 75.36 |
| 11:07:49（一本化作業前） | 8.60 | 107.64 | 75.36 |
| 11:17:01（一本化検証後） | 7.64 | 107.63 | 75.36 |

Windows build26200 / UBR9445、boot `2026-09-09T10:43:08.5000000+09:00` を記録する。
点の資源値の変化をこの作業のリークと断定しない。今回のPython検証processは終了を確認している。
一本化作業後の観測は`windows314-resources-final.json`へ保存した。
別project、既存失敗fixture、旧artifactへの操作なし。本流の変更・push/merge・formal実行なし。
