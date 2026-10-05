# v0.3 保存行→50,000 draw→writer・fresh readerの共有予算（2026-10-05）

状態: **架空保存controlの接続成功 / S4未採択 / 正式許可なし**。clean code `f06b8d1cb3a5a1149ef092d035e9d70f92bc3c66`、Windows 11 Pro 26H2/build26300/UBR9457・CPython3.14.0・local NTFSで実測した。追加agentなし。正式gate `s4_acceptance_not_frozen`、`formal_permission=false`、正式credit0、登録holdout40 seed未読を維持する。[受入範囲案 v3](../anomaly-v03-s4-acceptance-scope-draft-v3.md)の条件2/5に対する部分証拠である。

## 接続した範囲

[`run_saved_rows(..., publish_document=True)`](../../src/banto_ai/anomaly_v03_preformal_saved_row_document_budget.py)から、[新publication入口](../../src/banto_ai/anomaly_v03_saved_row_document_publication.py)へ接続した。架空480区間・2,880評価枠の保存control検証・40 cluster集約→50,000 draw計算→別process算術監査→文書・slice・件数監査→owned writer→writer終了後のfresh reader→最終照合を、同じsampler内で実行する。control rawの初期ロード、先行fixtureの生成、実保存readerの実行は予算外である。

writerは `calculation.json`、`audit.json`、`document.json`、`slices.json`、`slice-count-audit.json` の5 payloadを、新rootへ非上書きで保存する。元のcanonical JSON bytesにLFを1 byte付ける。writerとfresh readerは4 projection入力、projection、数値入力、計算・算術監査、文書・sliceのpinと由来を再照合し、主表の文書mappingとslice導出・別実装件数監査を再検証する。50,000 drawの再計算はしない。算術の独立検証は先行するaudit workerが行う。publicationのmarkerは既存local形式を使い、`.complete` と `marker-pending.json` の2 linkのみをsamplerの許可対象にする。

旧2 worker入口と既存数値fixtureの上限8 drawは維持した。新形式 `anomaly-v03-saved-row-document-publication-v1` は、4 workerの終了、全mapping出力、資源予算が揃うまで `measured` にしない。資源停止、writer失敗、reader失敗、未回収worker、改変入力、旧root再利用を成功へ読み替えない。未回収例外は元process ownerとreceiptを保持してcallerへ返す。

焦点12試験は45.360秒でpass、追加したfresh reader identity再利用拒否1試験は0.004秒でpass。既存の保存行・contiguous経路27試験は38.137秒でpass。これらは別runで、単一40試験runとして合算しない。新payload試験は小さい算術結果の形式を使い、実50,000 drawの証拠にはしない。compile、repository safety、diff checkもpass。凍結計画・registryのbytes/SHAは変更なし。

## 実機結果

新root `artifacts/anomaly-v03-preformal-saved-row-document-budget/trial-20261005-03`、helper root `artifacts/anomaly-v03-saved-row-publication-20261005-a1`。以前の架空control 4,800 files／129,026,491 Bを外部pinで読んだ。fixtureは歴史的sourceを架空 `aaaa…` と宣言し、最後の区間のfailed attempt1／latest attempt2を保持する。producer実行由来を認証したreceiptには変換しない。

| 項目 | 結果 |
|---|---|
| 共有wall | **277.961143秒 / 1,200秒**、stopなし、sampler終了確認 |
| preflight投影 | 47.721秒時点で完了 |
| analysis | PID12292、59.926秒、private peak126,779,392 B、exit0・回収 |
| arithmetic audit | PID20516、135.651秒、private peak29,593,600 B、exit0・回収 |
| writer | PID3040、15.363秒、private peak65,630,208 B、exit0・回収 |
| fresh reader | PID38416、7.344秒、private peak65,265,664 B、exit0・回収 |
| parent / root | private peak224,907,264 B、root最大9,564,530 B・43 entries・depth2 |
| 最小余裕 | commit14,478,139,392 B、RAM14,004,576,256 B、disk384,758,308,864 B |
| 内容 | 40 cluster、50,000 draw、9主表／117主推定／72paired推定／180 gate、1,233 slice／2,835 diagnostic rows／9診断表 |
| coverage | 2,879 success／1 inconclusive、旧failed attemptを保持、正式credit0 |

writerとreaderのparent PIDは3748。creation time／start token／PIDを元handleの起動観測と子返信で照合した。両者のPIDとtokenは異なり、writerの回収報告264.874秒の後、readerの回収報告272.229秒を記録した。root測定は最後のresult・resource-budgetを含まず、128 KiB／2 entriesを上限内に予約する。前回733秒の試行とは資源負荷が異なるため、今回の278秒を実装による速度改善の証拠にはしない。

## 保存証拠

pipeline root内の主要pin:

| 相対名 | bytes | SHA-256 |
|---|---:|---|
| result.json | 32628 | `4ff46697f017f86dc95753815f7d98d942a7262e220817dde55e908e7a585bde` |
| resource-budget.json | 6114 | `311f9675eb4574d6d31c618ae90f96044a3e4ab5c26bcb75ce7658660c3a8856` |
| projection.json | 554130 | `eb991adeb23f834dde7ce7eeab51a36a472e2b0dc453e48b7fcc25f72a964711` |
| input.json | 155375 | `77fd196ae7a48a1f52b7fef66984b4cb776a6c8e6cf237666e76a262fe4c3722` |
| calculation.json | 64525 | `fa63adc17d4e4c319aea4021ff9294a5df0bb3f8b6a7a848c8eba019a5dd0a12` |
| audit.json | 566 | `8d3b3144b519c0a6c0d8fa46b52742fcc3015cfa5ffefc5f29d936cb3ed446c4` |
| document.json | 121001 | `71d4dc159e5d7cca8a666158644122238bc76e5c378d4ed28b04df4d597ee075` |
| slices.json | 1928882 | `2f2c9b7695761a2dccf8ef1e96e3d2128c0763ac18fea44e2028831de7113a89` |
| slice-count-audit.json | 1244 | `847e244b1fa03e0c1eae43827ec20cfe1c089debbf56bfa0bd1141e53bbf1bfa` |
| writer/result.json | 7532 | `9285c3848a5aae11bf78eca188a4132b4a0228ec24b9dd72c7a7618ca4fbd34b` |
| writer/supervision.json | 2196 | `0dba7b38c3ce9d9b7da3b4984f168d9b73939cb115b73a69b7a638c366c8710b` |
| reader/result.json | 7440 | `31c115481bf73317319f133fab729bf2b79fb0479ea47c2aa2f197153a28c869` |
| reader/supervision.json | 2196 | `066b47aa4e7ff270b591a15cc2ae3b9860d80dc03f4870313b217b5ee272c0e8` |
| published/.complete | 1281 | `b4251e4437ce32c745e65d917dbcfa0b7850ae51c8e6874a2c49a6520b092155` |

公開payloadのLF込みpinはresultの `payload_pins` とpostcheckに固定した。5 payload・marker inventory/hash・markerの同一inode/2 link・全control集約・数値/文書対応・4終了receipt・37選択sourceのdisk/Git一致を、product moduleをimportしない別stdlib手順で照合した。4,840 rawの全pinを記録しpass。50,000 drawの再計算とraw観測由来の検証はこのpostcheckには含まない。

helper内: `run.py` 5,204 B／`e1560e89668ccbc1bef1b7df5c377bc9184c1910332a3657720ad584b3f7fec9`、`request.json` 1,123 B／`013496d746931d2d39ee4fde9fc3a2d67daa8389c563aa1393da01e9bc4838e0`、`capacity-preflight.json` 278 B／`db11baab1878b341a13fe131a0a0aaf30eedcc6d575df26084aaa83fad4e31b9`、`execution.json` 524 B／`5ce520cc62633a7df2683eeb39193e8291cbf8f536954989e19710a5b2eaaf57`、`postcheck.py` 20,296 B／`36bd8558e2c7bd5df319c51671282fd688aafc1847342a19e6676d7c95901e8d`、`postcheck.json` 843,760 B／`f938fbcb27b30b6cb0ecd6a2edc9eae57251a810bbca22cff017ddafce1af0b1`。これらはignored local証拠で、Git pushによる保存対象はsource・試験・本文である。旧failed trialと前回成功rootは保持する。

## 先行CI

先行文書保存点 `a7fc363965df5be4adb06b06d437c6dffec6ee2b` の [CI 37311338257](https://github.com/tyaro/banto-ai/actions/runs/37311338257) は全3job成功。Ubuntu24.04のPython3.12/3.14各2,933件・fail0/error0/skip237、共有29 fixture一致、必須28試験pass。外部HEAD/workflow/run/attemptを指定した全journalのローカル再検証もpass。8 raw、API job logのimage `ubuntu-24.04`／`20260927.320.1` を保存した。digest未取得、runner代替同定は未採択。今回の `f06b8d1` のCIや最終受入の成功へ読み替えない。[CI診断](anomaly-multiseed-v0.3-preformal-ubuntu-ci-triage-2026-10-05.md)にpinとjobを記録した。

## 残る受入

同じ予算へ実producer・実保存readerのロード／由来検証を結ぶ工程、raw観測→profile/score/ledgerの独立再導出、共通campaign実行認証、正式同形の容量2倍が残る。現在のsamplerは標本・協調停止で、正式全工程やhard quotaの受入ではない。analysis/auditは既存2 handle supervisor、writer/readerはplatform fixture supervisor。Gitはbare PATH呼出しで、5役の専用Git Job経路や全子孫回収、stdlib/拡張/DLL/CRT/外部programの実ロード在庫は未接続。37選択source照合は完全なsource/runtime closureではない。

26H2・公開保証A/B・runner同定・schema/root・再登録契約の版付き採択、最終revisionのLinux3.12/3.14とWindows native・正式dev8/smoke2・独立受入も必要。実データ作業は保存済み合成dev8/smoke2のengineering読取り・記述まで、実設備・顧客データは対象外。S4採択・最終受入までS5を開始しない。
