# S4-B1 成功後の受入条件と追加回帰確認

日付: 2026-09-10。基準HEAD `f9244a735dff982cfce7d1493efda9431bc31b42`。
今回のテスト修正savepoint: `cdbc0a1`。本流 `889cfc3` は変更なし。

限定Windows engineering controlの成功は[前回結果](anomaly-multiseed-v0.3-s4-b1-operation-context-result-2026-09-10.md)を参照。
今回native controlを追加実行していない。最大3回枠は前回の1回目成功で終了している。

## 現行の受入条件と到達範囲

[計画§8](../anomaly-multiseed-evaluation-plan-v0.3.md#v03-runtime-acceptance)、
`_anomaly_v03_runtime.acceptance_requirements()`、CI定義を照合した。
以下は今回の確認時点の現行条件であり、Windows 3.12を外す変更はまだ適用していない。

| 境界 | 必須条件 | 現在の証拠・残件 |
| --- | --- | --- |
| B1 engineering control | 子のruntime/source/token、実AccessCheck、全操作、置換証跡、所有物cleanup/teardown | 実装 `0b30e63` / 実行HEAD `f15af39` / Windows 26200.9445 / Python 3.14.0で限定成功。全48期待値、9対象削除、残存0。全S4受入とは別 |
| Linux共通契約 | Ubuntu 24.04 x86_64、Python 3.12/3.14、共通契約と既存stdlib全回帰、safety、実patch/build・image・source・各test結果の記録 | CIは両minorがあるが `ubuntu-latest`。候補revision上の所定環境・全回帰・証跡は未確認。過去の本流CI greenは候補の証拠に代用しない |
| Windows互換性/native受入 | 現行計画では3.12系と正式3.14.0の両方。共通回帰、publisher、DACL、独立token/process、競合・非上書き・失敗証跡 | 現coreは3.14.0専用。3.12を導入するだけでは通らない。現行条件の全native受入は未完了 |
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

## Windows 3.12要件の判断

ユーザーから「3.12必要？」との確認を受領した。
3.14.0でこの機能を動かすための技術的必須条件ではなく、既定の互換性受入要件であると回答した。
Windowsを3.14.0に一本化し、Linuxの3.12/3.14 CIは維持する案を提示して回答待ち。
この確認だけでは要件削除済みと扱わず、現行の計画・実装の受入リストを維持する。

一本化する場合の修正箇所は計画§8、`acceptance_requirements().windows_python`、
`test_anomaly_v03_publication.py` の対応する契約期待値、今回の受入記録/handoffである。
Linuxの2 jobs、`requires-python >=3.12`、正式3.14.0のruntime/hash判定、未受入を拒否する入口は維持する。
選抜した契約・拒否経路のpure/fake検証と独立レビューを行い、
Windows nativeの必須検査自体やB2/S4残件を削減したように扱わない。

3.12要件を維持する場合だけ、fixture専用の正確なpatch/build/exe/DLL pinと親子共通照合が必要になる。
新runtimeの導入だけでは現coreの3.14.0限定判定で拒否される。
`py -0p`では3.14と3.11のみ登録されている。全ディスクのportable runtime有無は走査していない。
3.12の導入・起動・source buildは未実施。
調査時点では[3.12.14公式release](https://www.python.org/downloads/release/python-31214/)は
2026-08-12公開のsource-only security releaseで、公式binary installerの最終版は3.12.10。
維持案では供給元・buildの選定も必要であり、版番号だけを設定して済ませない。

## 資源と保全

| 観測UTC | 空きRAM GiB | C空き GiB | D空き GiB |
| --- | ---: | ---: | ---: |
| 10:10:49 | 8.28 | 108.16 | 75.36 |
| 10:18:24 | 7.82 | 107.66 | 75.36 |
| 10:25:02 | 8.33 | 107.66 | 75.36 |

Windows build26200 / UBR9445、boot `2026-09-09T10:43:08.5000000+09:00` を記録する。
点の資源値の変化をこの作業のリークと断定しない。今回のPython検証processは終了を確認している。
別project、既存失敗fixture、旧artifactへの操作なし。本流の変更・push/merge・formal実行なし。
