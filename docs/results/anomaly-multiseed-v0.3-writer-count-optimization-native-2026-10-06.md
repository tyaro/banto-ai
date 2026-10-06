# v0.3 writerのcount検証整理と限定再測定（2026-10-06）

## 結果と対象

clean `fa333143ee92eecf9b436fb31320f2a0c722b65d` で、保存済みe03の11入力 / 8,076,367 Bを旧pinのまま使うwriter限定試行を1件実行した。既存 **60秒 / private 512 MiB / stdout・stderr合計64 KiB** のまま、supervisor **9.681秒**、writer内9.164秒で完了。PID2044・exit0、元handleによるidentity・終了・回収、5 payloadのローカル公開を確認した。上限の余裕は50.319秒だった。

数値由来は `8cac6fae93242747675fa67853a30a5e17ccef06`、今回worker revisionは `fa33314` と別欄で保持した。5 payloadのframed pinとmarker SHAは[先行writer計測](anomaly-multiseed-v0.3-writer-timing-native-2026-10-06.md)と一致した。4回のretained検証・slice mapping・独立count監査、marker前の2境界と公開後の最終境界を維持した。

この試行は生成・raw観測再導出・50,000 draw計算を繰り返さず、owned fresh readerと共通全工程の外側予算を測定していない。前回e03の全工程failedは維持する。正式gate `s4_acceptance_not_frozen`、正式許可false・credit0、登録holdout40 seedは未読。

## 変更と回帰確認

- [analysis input検証](../../src/banto_ai/anomaly_v03_analysis_inputs.py)から、固定inventoryの生countを読む共通検証 `_validate_slice_raw` を切り出した。分母、非負整数、delay histogram、検出数、score subsets、欠測・offset参照、partition、profile件数、equipment exposureの検証を維持する。既存の記述表readerはrow inventoryと導出fraction／null／delay等の照合も維持する。
- [slice fixture](../../src/banto_ai/anomaly_v03_slice_fixture.py)は、240 count cellごとに記述表を作って生countへ復元する往復を直接count検証へ置換した。raw shape、joint/marginal、primary／profile／delayの対応、pooled table、全出力schemaの検証は維持。整数leafのdeepcopyと、直後に全fieldを上書きする一時copyも整理した。入力を変更しない。
- [独立slice監査](../../src/banto_ai/anomaly_v03_fixture_slice_audit.py)はfull-target baselineをraw table内で一度集計し、同じ入力に対するcanonical digestの重複計算を整理した。各coordinate・全主row／sidecar／detailの再導出・照合は維持。依存は引き続きstdlibのhashlib/jsonのみで、計算側の集約・検証関数を呼ばない。
- 焦点21件の初回は20件pass・1件fail。新しいdelay改変テストが元の0を再代入していたため、必ずbinを増やすよう修正した。製品codeをこの失敗に合わせて緩和していない。
- 修正後のraw／legacy slice接続／legacy独立監査30件はpass（25.857秒）。最終copy整理後のraw検証3件も別runでpass（0.041秒）。初回runではprecomputed mapping／独立監査、analysis input、4回監査を通るwriter共通経路もpassした。実行数を一つの受入runへ合算しない。

## 時間と実機観測

同じ保存入力と同じ個別上限を使用した2つの限定試行。各工程は4回分の合計。秒。

| 観測 | 先行 `a8df865` | 今回 `fa33314` |
| --- | ---: | ---: |
| supervisor全体 | 56.561 | **9.681** |
| writer内全体 | 55.842 | 9.164 |
| retained検証全体 | 48.529 | 7.915 |
| slice mapping | 28.509 | **3.810** |
| 独立count監査 | 11.966 | **2.053** |
| 入力読取り | 2.593 | 0.854 |
| payload読取り | 2.451 | 0.614 |
| 主mapping | 1.009 | 0.200 |
| 上限までの余裕 | 3.439 | **50.319** |

先行と今回のOS負荷は同一ではなく、読取り等の未変更工程も短くなっている。従って時間差全体をcode変更の効果と断定しない。反復性能や共通全工程の安定成功も今回の1件では未確認。境界での再導出を省略するcacheは導入していない。

runtimeはWindows11 Pro 26H2 / build26300 / UBR9457、CPython3.14.0 / AMD64 / MSC v.1944、local NTFSで前後一致。peak worker private69,468,160 B、stdout7,976 B、stderr0 B、observation errorなし。終了後空きRAM13,050,650,624 B・disk354,145,976,320 Bは限定試行の観測値であり、正式同形容量2倍の根拠ではない。helper全体14.544秒にはwriter時計外のコピー／Git事前・終了後照合を含む。

## 保存照合

新rootは `artifacts/anomaly-v03-preformal-saved-row-document-budget/trial-20261006-profile03/`、helperは `artifacts/anomaly-v03-writer-profile-20261006-p3/`。旧e03・profile01/02は保全した。別checkerは171 raw／43 selected Git source、コピーした11入力、旧数値／新worker revision、request／reply／元handle identity、exit0・runtime一致、worker82 event / 14,438 B・parent12 event / 1,883 Bの順序・nesting・全終了を照合してpass。markerと5 payloadの普通の保存読戻しはchecker時計内で実施したが、owned fresh readerではない。checker自身はmappingや50,000 drawを再計算していない。

| 保存raw | bytes | SHA-256 |
| --- | ---: | --- |
| `result.json` | 47,085 | `d25c2c7ace7c008d0033683d8c3286d4fef86f9918f387f7d11e8a04d3249ecf` |
| `writer/request.json` | 8,746 | `b926947244e0455ffa3f8a214db14ca207f773883c1d430f79cac32738c3cb95` |
| `writer/supervision.json` | 2,191 | `6e2cbbeaebd455bcd31d4ab32e26c4cf2bd8cf671744cbc4725ffbfc4af2f25e` |
| `writer/launch.json` | 135 | `44172f9435fe53fe84ff1ffd89f67805dfee4aca4debfdfa7723989e18852de5` |
| `writer/worker/report.json` | 7,976 | `e83b0f29c250d1cec58337504e33911a2f5f1962ec81b5ee85cc579a720e565e` |
| helper `execution.json` | 479 | `9e9d76e931fe740a4f5ebb4a8ace9528e724c193ebe8185c29911a914169fa42` |
| helper `check.json` | 38,258 | `990c6ddf9dbc65eedf35009a0babd39238bdbfd4cb489290fe3b0b4b036dcaf3` |

marker SHAは `7a9a5f675e85931197115f961e70de2c92bafde03398cf152cffa247f74a0b2b`。PID2044のcreation tokenは `d73d1a4b42420b3870ba3715ea0b4f18d6d6f39201ff00a0c86eb57c2993020c`。science plan／freeze registryの既存hash一致もcheckerで確認した。rawはignoredのローカル保存。

## CIと次の範囲

先行 `a8df865` の [CI37398623472](https://github.com/tyaro/banto-ai/actions/runs/37398623472) は全3job成功。両minor各2,998件・fail0/error0/skip237、共有29 fixture・必須28試験pass、9 rawと全journalの外部HEAD/workflow/run/attemptを固定した保存再検証pass。今回の変更と異なるrevisionの結果として保持する。[CI診断](anomaly-multiseed-v0.3-preformal-ubuntu-ci-triage-2026-10-05.md)。

今回 `fa33314` の [CI37419094201](https://github.com/tyaro/banto-ai/actions/runs/37419094201) は記録時点で実行中。次はこのCIの完了・保存照合と、共通全工程の1回再試行に向けたpin・資源・停止条件の固定へ進む。長い全工程を自動反復する段階へは拡張していない。

正式受入には共通全工程成功、容量2倍、改訂契約採択、source/runtime全在庫、最終revisionのLinux/Windows・正式dev8/smoke2・独立受入が残る。追加agentなし、今回起動したworkerは1件で、writer・checkerとも終了済み。
