# 架空campaign controllerの次の実装契約案 v1（未採択）

状態: **proposal / 未採択**。この文書は、架空登録形式の保存行を区間間で結ぶ次の実装・native小試行の境界を定める。実登録holdout、S4採択、正式評価credit、40 clusterの完成を示さない。[共有anchor案](anomaly-v03-preformal-campaign-anchor-proposal-v1.md)と[現行の部分coverage](results/anomaly-multiseed-v0.3-preformal-saved-row-coverage-2026-10-04.md)を前提とする。

## 起動前に固定するもの

controllerは最初の生成CLI起動前に、凍結registry raw pinから再構成した順序付き480区間・2,880評価identityの計画hash、固定架空recipeとseed非消費、対象clean revision、選定source/runtimeの候補、campaign ID、専用root、区間・attempt命名、実行順と上限をcanonical anchorへ固定する。anchor raw pinは出力root外に保持する。今回実行する区間が0と1だけなら、その範囲も明示し、残り478区間を未開始とする。宣言された480計画や同じIDだけでは、producer実行や全件coverageを証明しない。

各`prepare`は新しい区間rootに対して22出力fileの期待pinを別directoryの`pins.json`へ先行保存する。controllerはそのraw bytes、SHA sidecar、正確な区間・root・revision・recipe・22 file inventoryを再読取りし、anchorの予定slotと照合する。期待pinは同じ決定的recipeから作るfixture用の事前値であり、実観測の独立oracleではない。`prepare`の時間・容量を後続CLI固有の予算に含めたと表示しない。

## 所有実行、journal、失敗

controllerは各CLIの起動前にanchor pin、区間、attempt、manifest pin、正確なargv/cwd/Python、出力rootと停止上限を含むinvocationを外部pin付きで保存する。元のprocess handleからPIDと作成時start tokenを観測し、終了code・wait/reap・stdout/stderr raw pinを保存する。`run-budget`の所有生成子・別reader子と、後続の保存raw再読取り子について、内側supervisionとworker replyのPID/start token/親PIDをcontrollerのCLI PIDに突き合わせる。親や子の自己申告だけを終了証拠にしない。

各境界で`pins.json`、`budgeted-result.json`、`resource-budget.json`、`owned-generator/result.json`、内側invocation/supervision/stdout、保存receipt/report/savepoint、22出力rawを正確な在庫と事前pinで再読取りする。`preformal_saved_row_reread_trial.py`へ渡す`--outer-result-pin`は**`owned-generator/result.json`**のpinであり、`budgeted-result.json`のpinではない。再読取り後はその`result.json`、`rows.json`、予算・supervision・stdoutをraw pinで保持し、６identityと最新attemptを現行coverage入口で再検査する。区間別budgeted resultのpinもjournalに残す。現行coverage入口自体は元22 payloadを再読取りせず、campaign由来を認証しない。

journalは起動前intentionと終了後outcomeを別recordとして非上書きで追記し、anchor pin、連番、`previous_sha256`、区間/attempt、各process観測、全証拠pin、状態・停止理由を連鎖させる。record countと最終head raw pinは**journal/root外**に保持し、開始前anchorと各起動前intentionもその時点で外部固定する。最後にまとめて作った自己申告journalを、起動順の証明に使わない。途中失敗、拒否、資源停止、未回収子、結果file未生成もrecord化し、元rootやattemptを上書きしない。最新attemptが失敗なら前成功へ戻さず、後続区間と集約を停止する。再試行は採択済み規則ができるまで別rootの新しいattemptとしてのみ扱う。

現行`run-budget`と保存raw再読取りCLIの**内側子invocationにはcampaign anchor pin欄がない**。外側controllerが元handleと親PID、manifest/raw pinを結べば、同じcontrollerが同じ事前計画の下でCLIを順に所有したという限定証拠にはなる。子自身がanchorを受け取って検証したとは主張できない。次版ではgenerator、最初のreader、後続の保存raw再読取り子のinvocationにanchor pin・区間・attemptを含め、replyでもechoさせて親が照合する。controllerと子のsource/実load閉包はこのechoだけでは完成しない。

外側controllerがCLIを監督しても、既存の単一process supervisorはその**子孫を所有しない**。CLIの強制停止や未回収時に内側子の終了を推定せず、新規CLIを起動しない。子孫停止・wait/reapを保証する所有方式または協調停止経路を実装・検証するまで、全process treeに対する停止保証は未成立とする。

metadata journalの`started`は起動前manifest pinを要求するため、`prepare`自身の失敗を現schemaのattempt記録にできない。controllerはanchor固定後の`prepare`失敗を別の外部pin付きpreflight receiptに保全し、後続区間を止める。次版でjournalに取り込むなら、manifest未生成を表す状態と順序を明示し、後から作ったmanifest pinで失敗を埋めない。またmetadata reducerの失敗理由と再試行番号は、所有子が全て終了・回収した証明ではない。owner不明・未回収の場合は再試行を許さず、元process handleと監督証拠を照合してから新しいattemptへ進む。

## ２区間native小試行のパスと結論

試行rootはすべて`artifacts/`直下の新規directoryとし、短い共通suffixを使う。例として区間0・attempt 1を`c001`、区間1・attempt 1を`c011`とする（`c`はroot用の短いalias、続く２桁は区間indexのbase36、末尾はattempt）。完全なcampaign IDはanchorへ保持する。各組は次のとおり。

| 区間 | 生成・保存root | 起動前pinset | 再読取りroot |
| --- | --- | --- | --- |
| 0 | `artifacts/anomaly-v03-preformal-registered-attempt-c001` | `artifacts/anomaly-v03-preformal-generated-pinsets-c001/pins.json` | `artifacts/anomaly-v03-preformal-saved-row-reread-c001` |
| 1 | `artifacts/anomaly-v03-preformal-registered-attempt-c011` | `artifacts/anomaly-v03-preformal-generated-pinsets-c011/pins.json` | `artifacts/anomaly-v03-preformal-saved-row-reread-c011` |

既存CLIは生成rootとpinsetをこの共通suffixで対応付け、生成rootが`artifacts/`直下であることを要求する。verboseな`c01-k000`は最深payload pathが現行245文字上限を超えて拒否される。上記４文字suffixでは両区間の最深pathは244文字。試行前に全root・pinset・sidecarが不存在であることを確認し、既存成果物を再利用しない。controllerのanchor/journal rootも別の新rootを使い、外部head/countはその外側に置く。

この小試行で到達できるのは、所有CLI・内側子の終了とraw保存を照合した**架空２区間・12/2,880評価の部分coverage**まで。残り478区間、40 cluster、診断、slice sourceは未成立で、現行collectorの`campaign_coherence_authenticated=false`、正式flag false/nullを維持する。２つの生成２役予算と２つの再読取り予算は別測定であり、値を足して単一外側予算のpassにしない。controllerの経過時間記録だけでも全工程共通の停止・子孫回収保証にはならない。

## S4/S5への適用境界

２区間試行の次に、anchorを子まで伝える契約、全区間の所有journalと保存raw由来、40 seed cluster導出、50,000 draw・全文書・完全別監査・公開後readerをまたぐ単一外側予算を検証する。ただし架空480区間の完走を自動的にS4の新しい先行必須条件へ加えない。26H2運用契約と公開保証、５役source/runtime閉包、対象revisionのLinux両jobとrunner同定、Windows native受入、最終dev８・smoke２と容量２倍検査も残る。S4採択前に実登録holdoutの成功や実S6を要求しない。未使用holdout40 seedのS5実行はS4採択後、実結果のread-only独立再監査はS6で行う。旧gate `s4_acceptance_not_frozen`、`formal_permission=false`、正式credit 0を維持する。
