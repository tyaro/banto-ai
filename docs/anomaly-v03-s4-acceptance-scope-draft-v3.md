# v0.3 S4受入範囲の整理案 v3（2026-10-05）

状態: **review draft / 未採択 / 正式実行許可なし**。ユーザーの受入条件確認と、進行を遅くする制約を整理する指示に対応する。[凍結計画 §8–9](anomaly-multiseed-evaluation-plan-v0.3.md#v03-runtime-acceptance)、[26H2改訂案 v2](anomaly-v03-s4-26h2-amendment-draft-v2.md)、[最新残件表](results/anomaly-multiseed-v0.3-session-handoff-and-remaining-acceptance-2026-10-04.md)の条件と追加技術案を分ける。科学仕様、旧計画・registry、保存証拠は変更しない。本書だけでS4を合格にせず、旧gate `s4_acceptance_not_frozen`、`formal_permission=false`、正式credit0、登録holdout未読を維持する。

## 正式開始前の5条件

| 条件 | 合格に必要なもの | 現在の残り |
| --- | --- | --- |
| 1. 運用契約 | OS/Python、公開保証、root/schema、固定revision、slice/sidecar対応、失敗・再登録規則を版付きで採択し独立再監査 | 旧正式pinは25H2/build26200/UBR9168。現26H2/build26300/UBR9457と保証A/Bは改訂案。Linux runnerの代替同定も未採択 |
| 2. 入力・consumer | 登録40 seed / 480区間 / 960 dataset / 2,880評価の予定identity・latest attempt・保存bytes・終了証拠を扱う固定入力試験。観測→profile/score/ledger→全分母・slice/sidecar→40 cluster / 50,000 draw / 全文書を接続 | 合成dev/smoke720評価の保存読取り、限定登録形式fixture、架空40 cluster算術は各々確認済み。同一の正式経路と失敗拒否の受入は残る |
| 3. 実行元と終了 | 最終clean source、stdlib・実ロード拡張/DLL/CRT・外部programを含むruntime inventoryを外部pinで固定。各役の実process、入出力、起動/終了、異常時の停止・回収を照合 | 実analysis/auditに71 source・stdlib2,559 file・loaded前後・元handle identity/exitを接続しnative確認。5役直接Git/382 Git Jobも部分証拠として保持。新b2a6065でwriter/fresh readerに75 source・全stdlib・loaded前後・元handle/exitを接続し限定native確認。4役の共通caller伝播と132 fixture試験pass（各2役は別HEAD、新4役/全7役native通し未実施）。残るproducer/初期/保存reader、外部program在庫・異常子孫回収と最終受入が必要 |
| 4. 最終revisionの受入 | Ubuntu24.04/Python3.12・3.14両job、選択保証のWindows26H2/Python3.14 native、正式dev8 seed・smoke2 seed全layout/両層/3候補。試験・runtime/runner由来・独立受入を対象revisionへ結ぶ | 過去revisionの成功は保持。最終対象の回帰とdev/smoke、改訂契約の独立受入は残る |
| 5. 資源と停止 | 生成・保存reader・50,000 draw全文書・独立audit・staging/writer・fresh readerの共通予算、停止・証拠保全を検証。smoke実測による正式同形見積りの2倍以上の空き容量 | 2026-10-06の限定e04は外側528.308/1,800秒で7 worker・最終照合まで完走。旧smoke24区間の部分容量20倍62.210 GiB／部分2倍124.421 GiBも照合済み。正式経路へ結ぶ受入、最終smokeのanalysis/追加audit/staging/診断予約を含む全容量2倍は残る |

S4では固定した架空入力で経路を検証する。実holdoutの成功receiptや実S6完了をS5開始前の前提にしない。S5はS4採択後、未使用登録40 seedをclean frozen revision・新rootで一度実行する。実結果のraw観測からの独立再導出はS6、全候補・全gateと制約の報告はS7で行う。

2026-10-06の進捗は[共通予算e04](results/anomaly-multiseed-v0.3-generation-publication-success-native-2026-10-06.md)と[旧smoke容量・runtime残件](results/anomaly-multiseed-v0.3-saved-smoke-capacity-and-runtime-scope-2026-10-06.md)を参照する。本draftと旧gateは未採択のまま。架空1区間＋479 metadataの完走、旧25H2 smokeの部分外挿を正式全観測・最終smoke・全容量へ代用しない。

同日後続の[実analysis/audit runtime接続](results/anomaly-multiseed-v0.3-arithmetic-runtime-observation-native-2026-10-06.md)は、clean `af3e7a5`の2算術役だけの確認。profileの採用そのものを追加必須にせず、実経路の期待値・在庫・元handle・終了を受入れる。全source/runtime、正式契約、最終dev/smoke、全容量2倍は未合格のまま。

## この先の実装に使う契約候補

既存v2案に沿い、研究用の**保証A（単一writer、終了後の別reader、非上書き、保存bytes・意味の再照合）**を改訂契約候補として使う。ユーザーの制約整理指示に対応し、実装は保証Aの候補へ集約する。保証Aは別主体の並行write/deleteをDACLで阻止する保証を持たず、その差を計画改訂と独立監査へ明示する。採択・native最終受入までは正式許可を出さない。

OS/Pythonはv2の26H2/build26300/UBR9457と固定CPython3.14.0のexact tupleを候補として保持する。Linux runnerはv2の3job外部log・image/version・同じtagの公式release/README pinによる代替同定を採択候補とする。VM image digest未取得の事実は保持する。これらは独立監査へ渡す実装方針であり、旧計画の条件を既に置換したという意味ではない。

## 追加案を必須条件へ拡張しない

以下を改訂契約の独立監査へ提示する。旧計画の要件を自己判断で合格にする操作ではない。

| 項目 | 凍結計画との関係とv3の案 |
| --- | --- |
| メモリ内コードの完全認証 | §8はclean sourceと完全runtime inventoryのhash pinを要求し、任意のメモリ内コードの完全認証は明記していない。v2案で追加した `in-memory code` の完全閉包は追加必須条件から外す。実ロード依存の在庫・disk raw pinと未認証の限界は維持 |
| 全補助processの個別exit code | 業務workerの元handle、PID/start token、終了code・reap、異常時の子孫停止・回収は必要。Job active0は所属processの全終了を示すが、個別成功やloaded codeは示さない。conhost等を含む全補助processの個別exit code認証は追加必須にしない |
| protected DACL・独立read-only token | 旧§8では必須。保証Bで維持するか、保証Aへの版付き改訂・独立監査で並行改変防止の保証を外すかを確定する。保証A採択後に独立token試験を追加必須扱いしない。非上書き、writer終了後fresh read、改変検出、失敗保全は必要 |
| 特定の事前profile wrapper | 必要なのは各役のsource/runtime期待値と実行時照合。既存候補profile wrapperや全prototype CLIの採用自体は条件にしない。正式経路で利用しないprototypeの統合は先行必須にしない |
| 架空480区間の新規完走 | 登録全inventoryの欠落・重複・latest attempt・由来の固定入力検査は必要。架空480区間の実生成完走は自動追加しない。最終dev8/smoke2実生成とS5の正式全inventory保存・照合は必要 |
| 実holdoutによる完全S6予行 | S4では固定入力で独立consumer・監査経路を検証する。正式holdoutを予行用に読まない。50,000 draw、全条件別在庫、raw観測再導出の範囲を明示し、限定算術試験を完全S6へ読み替えない |
| Windows Python3.12実機 | 2026-09-10の計画改訂で除外済み。Windowsは固定Python3.14.0、Linuxは3.12/3.14両jobを受け入れる |

既存限定fixtureの `loaded_code_authenticated=false` 等とraw receiptを保持する。この整理を理由に既存fixtureの `source_closure_complete` / `runtime_closure_complete` / `formal_permission` をtrueへ書き換えない。正式wrapperの保証・用語は版付き契約で定義し、実装・証拠を独立に受け入れる。

## 次の作業順

1. 26H2・保証A・runner代替同定・上表の受入範囲を含む一つの改訂契約候補を確定する。独立監査前のdraftであることを保持する。
2. 正式経路で使うsource/runtime在庫と入力/consumer接続を実装し、固定入力の正常・失敗を検証する。利用しないprototypeの追加統合は先送りする。
3. 同じ経路に50,000 draw、独立audit、writer/fresh readerと外側予算を接続して測る。smokeから容量2倍の根拠を保存する。
4. 最終revisionのLinux/Windows・dev/smokeと独立監査を受入記録へ結び、未了0を確認してS4を採択する。その後にS5へ進む。

本作業は受入範囲の整理であり、新たな実評価・全工程測定・契約採択・正式許可は実施していない。
