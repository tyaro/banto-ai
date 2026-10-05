# v0.3 保存reader行からanalysis・独立auditへの接続（2026-10-05）

状態: **架空固定入力の接続試験が成功 / S4未採択 / 正式許可なし**。clean source `a9f1882dc7a7068a540dabc80a6574c4f29a8529`、branch `codex/preformal-acceptance-scope`、Windows 11 Pro 26H2/build26300/UBR9457・CPython3.14.0・local NTFSで実施した。追加agentは起動していない。[S4受入範囲案 v3](../anomaly-v03-s4-acceptance-scope-draft-v3.md)の条件2に対する部分証拠であり、正式gate `s4_acceptance_not_frozen`、`formal_permission=false`、正式credit0を維持する。登録holdout40 seedは未読である。

## 実装と確認した範囲

[純粋projection](../../src/banto_ai/anomaly_v03_saved_row_fixture_projection.py)は、480区間の各10保存raw/controlを外部pinから読み、既存のcoverage・lineage・seed寄与検査を通して40 clusterへ集約する。全分母、delay histogram、effective clean seconds、profile状態、coverage、slice/diagnostic countsを既存worker用の4入力へ変換する。欠落、重複、順序違い、raw pin不一致、古いattempt、上限違反を拒否し、失敗した旧attemptを保持する。projection自体はprocessを起動しない。

[pipeline入口 `run_saved_row_pipeline`](../../src/banto_ai/anomaly_v03_bound_fixture_pipeline.py)は、外部に保存した期待文書pinを受け取り、projectionを既存の標本・協調予算内で実行し、analysisと別processのauditを各1回起動する。親6 sourceのGit/raw pinを実行前後で照合し、導出した入力pinをworker証跡へ結ぶ。失敗時のconsumer自動再実行は行わず、既存receiptを保全する。旧 `run_pipeline` の公開入口も維持する。

今回の入力は、テスト用に発明した40 seed identity・480区間・2,880評価枠の**保存制御fixture**である。実観測を生成しておらず、実際のcampaign実行・producer/PID由来を認証しない。保存controlsの歴史的revisionは架空の `aaaa…`、今回の導出・consumer sourceは上記 `a9f1882` である。両者を同じ実行由来とは扱わない。

最終codeの関連24試験（projection11件・既存pipeline13件）は182.175秒でpassした。固定入力の別数値・slice監査、失敗拒否、analysis→auditの順序、失敗時再実行なしも対象とした。前段の43試験193.599秒passは途中版の関連確認であり、24件と合算した単一runの件数にはしない。

## Windows native結果

非上書きrootは `artifacts/anomaly-v03-saved-row-projection-20261005-a1/`。480区間の4,800制御rawは合計129,026,491 B。fixture構築と期待文書の準備101.869秒はpipeline予算の外にある。その後、未変更の製品projectionとnative consumerを実行した。

- terminal `native-attempt/result.json` は `verified`、analysis1回・audit1回、数値監査・slice監査とも成功。1 drawのみで、正式bootstrapは未実施。
- coverageは成功2,879枠・inconclusive1枠。profileの正当なinconclusiveを保持し、区間479のfailed attempt1とlatest attempt2を区別した。
- 別auditは40 cluster、9 candidate tables、117 primary estimates、72 paired estimates、180 gates、main slice1,233行・diagnostic2,835行・9 diagnostic tablesを照合した。昇格・候補選択は許可していない。
- analysis文書は事前保存した1,927,123 Bの外部期待pinと一致した。actual registered observations、raw observationからのprofile/score/ledger再導出、完全S6は対象外である。

| role | 実worker PID / 親PID | start token | wall秒 | peak private B | 終了 |
| --- | --- | --- | ---: | ---: | --- |
| analysis | 8080 / 34124 | `bd0ca304e187f24209acc654b9ecdfcec97dcf28e425e874c51ea4aa754bdc9d` | 5.895318 | 66,637,824 | 元handleでexit0・回収確認 |
| audit | 35068 / 34124 | `df0910daa62bf9db4d104689d157c06a2bf0f4bdb4040d56918ad6d293c0ef6f` | 4.767819 | 69,255,168 | 元handleでexit0・回収確認 |

両roleの選定source各27件は実行前後で一致した。観測依存43件・293 file・194 module・47 native fileの記録は限定在庫であり、全source/runtime閉包の認証ではない。この入口は2つのowned worker rootを使う既存fixture経路で、source確認のGitはbare Gitである。[先行の専用Git Job試行](anomaly-multiseed-v0.3-git-private-job-native-2026-10-05.md)の382 private Git Jobや5役Job全子孫回収の成果を、この試行へ読み替えない。

共有fixture予算は **82.461151 / 120秒、271標本、pass、monitor終了確認**。最大新root10,288,250 B・51 entries、親peak private232,525,824 B、最小system commit headroom14,334,181,376 B、free RAM12,470,460,416 B、free disk398,427,488,256 Bだった。標本・協調監視でありhard quotaではない。fixture準備とindexロードは予算外、producer・writer・fresh readerはこの時計に含まず、正式同形の全工程測定や容量2倍の根拠にはしない。

## 別helperによる保存後照合と失敗保全

pipeline本体の成功後、`run.py` の後処理が結果に存在しない `supervision_pin` を参照して停止した。続く `postcheck.py` も `launch.json` に存在しない `parent_pid` を仮定して停止した。両helperと失敗metadataを保全した。製品result・receiptを変更せず、consumerも再実行していない。

新しい `postcheck_a2.py` は保存形式を確認して、process全体をexpected証跡へ、launchのPID/start tokenを実記録へ、`worker/stderr.json` を監督pinへ照合した。製品moduleをimportせず、stdlibで480保存区間の全count・delay・exposure・profile・coverage・sliceを再集計した。外部固定terminalと準備pinから4,847 rawのpinが一致し、親6件と両role27件の選定sourceは重複を除く33件が実disk/Git blobへ一致した。保存済みの監督記録・入力・数値監査を結ぶ照合であり、新しい独立S6実行ではない。

次の値はroot相対の **bytes / SHA-256**。`artifacts/`はGit対象外なので、commitだけではrawを別マシンへ移せない。

| ファイル | bytes | SHA-256 |
| --- | ---: | --- |
| `preparation.json` | 1,380 | `ce1e5720e83933f1f28947968bc68d480e8c97e651023287cd35d02c1e0d45a4` |
| `pinset.json` | 690,985 | `67032c5e61102b2063ece1674e4445d0b2811953132a6074b4ff93adb5ae2ab5` |
| `native-attempt/result.json` | 6,976 | `bf79a177f2f2bda62d5b60910a6acb0ecde929a24d544cd75b0e3104ee8f1ca6` |
| `native-attempt/projection.json` | 554,131 | `68e7822815aba0f3ea209582edf6b3fc18b2eac69043cecd6592dfbec3a83d0c` |
| `native-attempt/inputs/input.json` | 203,781 | `55caf4692f95039a355c98a980973824454c47a8ef711a864b7846aaf1140e9e` |
| `native-attempt/inputs/slices.json` | 4,328,001 | `d27800e6cec05d865c86eaec926e9def793e0063dcb10ce2f59996111b239105` |
| `native-attempt/inputs/coverage.json` | 36,612 | `49f403510b849187a400dc9880b6945f0da792b75fe092b63697e172700adbd7` |
| `native-attempt/inputs/operation.json` | 175 | `16982ef3f7da11af9af25d0b5f6b5e1fd6dcc0f4cf88fbb9116253d5a2493e78` |
| `native-attempt/analysis/payload/document.json` | 1,927,123 | `136481509e26ce75da681e8208596fb093b4f81eb13798c553830c13cbee8fc9` |
| `native-attempt/analysis/supervision.json` | 2,205 | `01645ee1df6ddda4d19e9dd77ab1b312cc6e43d4ac9250bf4236ec3de3ae651c` |
| `native-attempt/audit/payload/primary-and-slices-audit.json` | 2,384 | `ae34db4b22fac132c9ef192f94062ea31ca01627c9096960a6b1975fc7254049` |
| `native-attempt/audit/supervision.json` | 2,201 | `f69c00b6ef599a410325e4ad3e19d887675c41909eec9893ac1201b3d3f9a117` |
| `native-attempt/resource-budget.json` | 1,716 | `eaf04501cef91ed9b198a9f7a20bf826509b432d9dc6e55e9211b986f9f3bc46` |
| `postcheck-a1-failure.json` | 495 | `85f42f6875c025fa9960506f6b3fa34fcf92ab010819be72061adfb7e35f6ea3` |
| `postcheck-a2-failure.json` | 413 | `e9907cba91dc25e2908e73646f3c31ed565d56d9454a05c52d5510ed5f0e429c` |
| `postcheck-a2.json` | 582,969 | `e5b47d3549a150f57d4d09926e8b5a2090b3f0ec447ce7248ea9652ef2a6cb87` |

helper source pinは `prepare.py` 5,116 B / `f228bdd290172c4ac207cb4096f6271dd8ca7d18984c880f14bb554b2980683a`、初回 `run.py` 4,557 B / `ecc047dc312e3b4a26da0391e6c676a894d9c9124e2fe9b09b145c717ca0eb22`、失敗 `postcheck.py` 9,994 B / `f21c6b48b31d62ff5975c3da0d4f3ecd44b8cd018e941f94e22d5d57fdb6dc89`、成功 `postcheck_a2.py` 10,189 B / `fdf68077c1805c240c7b277c6b47ea1c2ebf71793de1ee9995773c11b6e95b5a`。

## CIと次の残件

先行source `52c896147246bfa067ddf070c2d40a3fae649e64` の [Ubuntu CI 37275249917](https://github.com/tyaro/banto-ai/actions/runs/37275249917) は3 job成功。Python3.12/3.14各2,908試験・failure0/error0/skip237、共有29fixture一致・必須28試験pass、8rawと全journalのローカル再照合がpassした。[CI診断と外部pin](anomaly-multiseed-v0.3-preformal-ubuntu-ci-triage-2026-10-05.md)へ記録済み。この成功を新source `a9f1882` のCI成功にはしない。

次はこの保存行入力を50,000 drawの正式文書候補へ結び、独立audit・writer・fresh readerとproducerを含む共通外側予算に接続する。既存数値fixtureの上限8 drawを自己判断で解除したり、今回1 drawを正式経路と扱ったりしない。raw観測からのprofile/score/ledger独立再導出、共通campaign実行由来、全source/runtime在庫と異常時回収、正式同形容量2倍、26H2・保証A・runner代替同定の版付き採択と独立監査、最終revisionのLinux/Windows・dev8/smoke2受入は残る。S4未了0の独立判定後にS5へ進む。
