# 次のタスク用の短い引継ぎ

更新: 2026-09-25 JST。**通常権限の別process readerと外側receiptを接続、13試験pass。実公開レポートを別processで確認済み。次は40-cluster入力・推論/full documentへのadapterを架空入力で準備。**

- [API/CLI](anomaly-v03-consumer-reader.md)、[結果](results/anomaly-multiseed-v0.3-consumer-separate-reader-2026-09-25.md)、長い引継書§170。
- 作業先C:/Users/TKent/.codex/worktrees/70b0/banto-ai、branch codex/s4-b1-windows-engineering。実装35842261a90b1efe475056dc9ef962c56773f1f1、OUT artifacts/consumer-separate-reader-2026-09-25。最終文書revision/pinはsavepoint-evidence.json。

## 今回の成果と次の作業

anomaly_v03_consumer_reader.check_in_subprocessとCLIを追加。呼出し側がwriter終了を保証してから、外部保持したmarker hash＋binding/reportの2pinと明示analysis入力で確認する。新しい確認directoryにrequest、worker出力、supervision、resultを保存。-I -Bの別Pythonへ明示srcを渡し、既存supervisorで30秒/private512MiB/log64KiB。6入口source/requestの前後hashと監視側runtime前後一致を確認する。完全dependency/runtime閉包ではない。

13新規試験pass（failure/error/skip0、3.291秒）。応答消失・再封印不整合・未完了・上書き/重複root・hash差・timeout・未終了owner保持を確認。旧保存/算術suiteは再実行なし。実公開物の子PID27688（親35884）はexit0/終了確認、監視error0。7file/7,896,608bytesから4payload/2,755,533bytesへの対応を確認。元4payloadと2marker名の6pin不変。reader0.826秒、外側1.055秒。

親peak33.34MiB/reader35.91MiB、最小RAM12.30GiB/commit余裕20.24GiB、C/D130.25/329.72GiB。監視側OS26200.9457/CPython3.14.0前後一致。今回の記録はverified/request.json、worker/report.json、supervision.json、result.json。子の完全runtime受入ではない。

T11/T12のengineering接続は完了。別processは独立数値監査の代替ではなくindependent_numerical_audit_performed=false。元publicationからmarker hashを自己採用せず、応答消失時も独立に保持した期待pinが必要。元結果へ追記/撤回しない。確認側の応答消失は新しい確認名で再読取。UnreapedWorkerのAPIは元ownerを保持し、呼出し側がreap。CLIは既存retain_until_exitを使い、古い未確認resultは書き換えない。

**次は正式consumerの40-cluster入力と推論・full documentへのadapterを、非登録の架空入力で準備する。** 既存算術・schema部品を使い、現工程のdev/smoke記述入口を緩和しない。実holdout/正式modeを起動せず、50,000回の実データbootstrapや新評価を行わない。source/runtime freeze・正式契約採択は別の残件。保留principal/UAC/ACL/同時書換え作業は再開しない。

前工程の対応/容量見積りはconsumer-coverage-budget-review-2026-09-25（16387bytes/SHA948751649d613e74af6930ee77d57824d9ecee8a8fbbcbec7b8ea3e7fd337cf3）。正式2880評価への単純外挿59.91GiB/活動178.17時間、producer枠240時間/96GiB＋空き32GiBは未採択・未適用の案。正式推論/最終audit予算は未確定。D等の空きは変動するため実行前確認が必要。

読取元はengineering-consumer-entry-2026-09-25（11477bytes/SHA830d2de2202166c7f3f735603c21b317cb18bb33809530d1f3bf8d8c87403219）のpublished-success。marker97c8bc637328cb173e6c1a678765c7785512fb2ad7b66ed8af15939e819c874e、receipt11507bytes/SHAe2ac5bb2b36d5121062dd8bdc790556cd767cd22a7168ec0579d5aab6570cf3a。旧未完了published/test-attempt-1/2は保全し再使用しない。

新評価・観測/score読取・再計算・bootstrap0。旧保存点・実計算c01d1c9・本流clean6f1285d・closed・dirty guard不変、banto-24 PAUSED。formal/promotion/S6/trust=false。Phase2/3全体の完了ではない。

## 前工程の受入残件

[残件表](results/anomaly-multiseed-v0.3-acceptance-gap-review-2026-09-25.md)。freeze前は運用契約、consumer接続、source/runtime固定、公開接続、容量時間予算の5まとまり。今回で全5完了とはしない。11保存点＋3receipt203,543bytesを照合済み、158source等比較中157一致、差分は旧READMEの追記だけ。720評価を再計算しない。

17モジュールの静的候補表にはmanifest.pyのworking CRLF/Git LF差が残る。正規化後同一だがraw不一致なので別clean checkoutでfreeze時に確認。旧Linux CI036ecb4からselected11本が変更/追加、古いpassは最新候補全回帰の代わりにならない。完全runtime/dependency closureは未完了。

本流は別作業でclean6f1285d（旧889cfc3）。temp native/互換試験のmain README記載はGit bytesまで照合し、raw/CI再検証・mergeなし。Windows3.12必須化なし。旧helper.boundariesのmain固定値は古いため、acceptance-gap-review/review.pyのboundary関数を参照。OS直近観測はProfessional25H2/26200/UBR9457、旧engineering9445から更新。formal pin9168と過去runtimeは維持。

## 前工程の記述表

[結果表・診断表](results/anomaly-multiseed-v0.3-descriptive-report-2026-09-25.md)、[閲覧用要約](../artifacts/descriptive-report-2026-09-25/report.md)。実装e0753ba4e1518706002cb3a51f9b5a3c891a4e7c。dev/smoke別18表・234主指標・5,670診断行を元入力とschema部分形式へ照合、27試験pass。manifest7932bytes/SHA25679364b641f8f7a047298ca73d46fcdc49b1931c23394a043cb8802255392af39。gate/CI/採択なし、formal/promotion/S6=false、selected=null、performance=not_evaluated。入力のreadinessは作成時点の文脈として保持。

## 前工程のseed集計

全120区間/720評価を5保存点のhashと全報告のidentity/最終attempt/入力pinで認証済み。seed90表・role18表の1404 counts、候補差12表144点が旧集計と一致。dev8/smoke2は各12layouts×両層×3候補。警報0の適合率46評価はnull診断を保持し、予定母数から除外していない。実装d48ecb4、文書c02e7b0、OUT artifacts/independent-seed-aggregation-2026-09-24、成功verified/。manifest7935bytes/SHA2563d03cdef2852e8432b7d1ca9de7cab25ff9b994fefa9819cb290263145426bb5。counts533126bytes/SHA256e6f3012a0a6fe622b5fc7d6365a7a1f2afadec16517f1bbe2cc423253ae68b2e。保存時点の監査連結であり、今日の全payload再検査ではない。

## 前工程の到達範囲

全120区間・240datasetsの正常生成/overlay/丸めは4,320,000保存観測行で完全一致。全720評価のprofile/score/ledger検算と入力pinで接続済み。旧C1/C2の記述統計は変わらない。生成検算の実装47dbc165f12fb1ce7608bb57625cb498bc4a4d04、文書31b73008828a52681f2ae9a887d88ddedecb516f、OUT artifacts/independent-generation-audit-2026-09-24、成功はverified/、manifest 29473bytes/SHA256322a7fe20b23febcb4467ba16034ab9bae5c209777590150c61bccbae09c90f8。

生成検算工程は既存10 seedを120 pairs分メモリ内で再構成し、新dataset/新評価は0だった。その次の算術検証は固定bootstrap indexと手例だけを計算した。前工程のseed集計は保存済み監査報告を読み、観測seed再構成/score再計算/bootstrapを行っていない。旧観測/score検算は不要に繰り返さない。

## 完走証拠と保全

起点は完走保存点0e02d04b0a5a2151664cda6e8518bf412ff70aab。`artifacts/chunk-119-retry-2026-09-24/savepoint-evidence.json`は8366bytes/SHA256 ca976322e0bb9e7b033b94948497a41acc79900668d01edbeebfc3fea8b22c8d。前回全件score検算保存点は26529bytes/SHA256 b591663d8026e348b81e427da8a169702625b160a1352cd7e7e2c07c6e43e9c9（文書commit64fa36c）。これら旧OUTは変更禁止。失敗chunk119/attempt1は保全し、verified attempt2だけを使用。

実計算sourceはC:/Users/TKent/.codex/worktrees/v03p/banto-ai / clean c01d1c978f78bab51391392d56cdcb7aab5afaab、出力artifacts/v03-runs/r1。本流D:/develop/banto-aiは別作業でclean 6f1285d28a37edf486ba5c49b8dac3708c7f3067へ更新（旧保存点889cfc3）。今回merge/pushなし。既存dirty docs/results/anomaly-multiseed-v0.3-s4-b2-parent-policy-rename-2026-09-14.mdは8461bytes/SHA256443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保持・commit除外。

control000010は終了済み。journal362、全120区間/720評価、status=completed/next=null。closed SHA256 a716478fa46eddcab2300de2d1f06ba6982eb94f738ca794cfc4fc931b33028a。controller/所有worker終了確認済み、banto-24 PAUSED。旧保存点・元payloadを理由なく再計算しない。

## 継続する制約

- ユーザーは適度なsavepointを伴う自走を許可済み。必要な判断のみ相談する。独立レビュー委譲も許可済みで、依頼後の進捗ポーリングはしない。通常は自分で進め、委譲する場合も差分に限定する。
- 同じ出力先は単一writer。**専用principal/起動特権/P-U分離試験は§116で保留**。「続けて」から再開を推定しない。UAC/ACL/service/task/VMの変更、SAM/account照会・変更を行わない。
- **保護rootは参照も禁止**: `C:\ProgramData\BantoAI-S4B2-principal-20260915` と末尾b/c/d/e/f、`...-20260916g/h/i/j`。存在確認・列挙・hashも行わない。jと診断guardは消費済み。専用account `BantoS4Publisher` / SID末尾1010に触れない。
- 旧正式gateを開かず、停止済みcontrol000008を再使用せず、追加invocation/holdoutを自動起動しない。push/merge/CIはこの工程では行わない。
