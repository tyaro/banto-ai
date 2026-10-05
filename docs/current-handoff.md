# 次のタスク用の短い引継ぎ

2026-10-05 JST。branch `codex/preformal-acceptance-scope`、repository `D:\develop\banto-ai`。

## 現在の状態

- 最新code保存点: `d997020f6a399ff32f5156491aac191f3bc7e167`（control disk読取り・再照合→50,000 draw→writer/fresh reader）。初版 `a752257`、前段公開 `f06b8d1`。本書の証拠追記はcodeより後の文書commitに保存する。
- 正式gate `s4_acceptance_not_frozen`、`formal_permission=false`、正式credit0。登録holdout40 seedは未読。実設備・顧客データは対象外。
- 実データ作業は保存済み合成dev8/smoke2、120区間・240 dataset・720評価のengineering読取り・記述報告まで。新native試行は架空入力のみ。
- 容量への配慮として追加agentを起動していない。独立した有限の作業単位で保存する。

## 正式評価を始める条件

[凍結計画 §8–9](anomaly-multiseed-evaluation-plan-v0.3.md#v03-runtime-acceptance)と[受入範囲整理案 v3](anomaly-v03-s4-acceptance-scope-draft-v3.md)を参照する。v3は未採択の範囲整理で、S4合格や正式許可ではない。

1. **運用契約採択**: 現26H2/build26300/UBR9457、公開保証A/B、root/schema、revision、slice/sidecar、失敗・再登録規則、runner同定を版付き改訂・独立監査へ結ぶ。旧25H2正式pinは不一致のまま。
2. **入力/consumer接続**: 登録40 seed・480区間・960 dataset・2,880評価の保存形式、latest attempt、由来・終了を固定入力で検証し、全分母・slice/sidecar・50,000 draw・全文書へ接続する。
3. **source/runtimeと終了**: 5役の最終clean source、stdlib/拡張/DLL/CRT/外部program inventoryと実行境界、業務workerの元handle・identity・exit/reap、異常時子孫回収を照合する。
4. **最終受入**: 最終revisionでUbuntu24.04/Python3.12・3.14、Windows26H2/Python3.14 native、正式dev8/smoke2全layout/両層/3候補、独立受入を完了する。
5. **共通予算と容量**: 生成→保存reader→50,000 draw全文書→独立audit→staging/writer→fresh readerを同じ外側予算で測り、smokeに基づく正式同形見積りの2倍以上の空きを確認する。

採択後にS5の未使用holdout40 seedを新rootで一回実行し、S6独立再導出、S7結果文書へ進む。実S5成功/実S6完了をS4開始前の前提にしない。

v3では、メモリ内コードの完全認証、conhost等の全補助processの個別exit code、未採用prototypeの全統合、架空480区間完走を追加必須にしない案を提示した。実ロード依存在庫と業務worker終了・子孫回収は維持する。DACL/独立tokenは保証Bなら必要、保証Aへ変更するには版付き改訂・独立監査が必要。旧fixtureのfalse flagは変更しない。

## 最新の実装・証拠

[control disk読取りを含む50,000 draw公開予算](results/anomaly-multiseed-v0.3-saved-control-budget-native-2026-10-05.md): clean `d997020`で架空480区間control4,800 files/129,026,491 Bのdisk読取り→40 cluster→全主算術／別process監査→文書／slice→5 payload公開→終了後fresh reader→disk再照合を共有280.645/1,200秒で完了。4 worker exit0・回収、4,841 raw／39 sourceの別照合pass。全966 control checkpointのsample/probeを維持し履歴を集約、budget receipt6,745 B。初版はreceipt64 KiB超過でfailedを保持。初版41試験・修正後16試験は別runでpass。外部controlは新rootのdirectory測定外・256 MiB input上限内、先行生成/期待pin準備は予算外。実producer/実保存reader、raw観測再導出・共通campaign実行認証・全工程予算・容量2倍は未了。前段[公開のみの証拠](results/anomaly-multiseed-v0.3-saved-row-publication-native-2026-10-05.md)と旧成功/failed rootは保持する。

[専用Git Job実機証拠](results/anomaly-multiseed-v0.3-git-private-job-native-2026-10-05.md): 5役を含む382 Git callの専用Jobは全てactive0。8 manifest、1,244 rawの別照合、Git起動禁止の保存verifierがpass。関連55試験、実Git・CLI子孫の正常/timeout/非zero、Unicode明示環境読戻しを確認。初回helper期待値ミス2件は失敗rawを保持し別rootで確認済み。

5役共有標本予算148.005秒/240秒、Job698 process・active0。この小fixtureは全工程正式同形予算ではない。Gitのloaded依存在庫、source/runtime期待値の固定、正式経路と共通予算の接続が残る。

先行保存点 `a7fc363` の [CI 37311338257](https://github.com/tyaro/banto-ai/actions/runs/37311338257) は全3job成功、両minor各2,933件・fail0/error0/skip237、共有29fixture/必須28試験pass。8rawと全journalを保存・ローカル再検証済み。[CI診断](results/anomaly-multiseed-v0.3-preformal-ubuntu-ci-triage-2026-10-05.md)。後続 `d04d723` の [CI 37315729198](https://github.com/tyaro/banto-ai/actions/runs/37315729198) は両minor実行中。新code `d997020` のCI成功には読み替えない。

## 次の着手と履歴

次は実producer/実保存readerの観測payload・latest attempt・由来検証と4入力の接続を固定fixtureで確認し、共通外側予算と正式同形容量2倍へ進む。control readerは実保存readerの代替と扱わず、架空480区間の新規生成完走を自動追加の必須にしない。既存数値fixtureの上限8 drawは維持する。26H2・保証A・runner代替同定の改訂契約候補、正式source/runtime在庫、raw観測独立再導出も残る。最終revisionと独立受入の前にS5を開始しない。

詳細な残件と保存点は[受入表](results/anomaly-multiseed-v0.3-session-handoff-and-remaining-acceptance-2026-10-04.md)、過去408行の引継ぎは[保全した旧履歴](current-handoff-history-through-git-job-2026-10-05.md)。旧履歴は各保存時点の状態であり、最新判断は本書とv3を使う。
