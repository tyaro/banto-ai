# analysis役割の保存結果準備と実行証拠の接続

2026-09-26 JST（9月25日開始）。実装 `2db441e44a65857f288f800a104ba436339358b9`。[API](../anomaly-v03-analysis-evidence.md)。OUTは開始時の `artifacts/analysis-observed-evidence-2026-09-25` を維持。成功例はobserved-example/。文書保存revisionと各pinは最上位savepoint-evidence.json。

## 完了した接続

prepare_with_evidenceを追加。role=analysis、operation=prepare-saved-descriptive-resultに限定して、7保存fileの認証と4payloadの準備を実childへ分離した。親は外部anchorから期待payloadを先に保持し、Git/source/runtime、元handleのprocess identity、前後入出力を共通evidence validatorへ結合する。readerの役割やprofileを受け付けない。

保存例の架空入力は7file/6,622bytes。request/invocation込み9file/11,272bytesから、4payload/5,237bytesを準備。child PID17940、exit0/reaped、観測error0、監視1.546秒、stdout240,554bytes。親と子の生成時刻・PIDが一致し、保持expectedと全出力pinが一致。数値再計算、新評価、登録データ読取、公開完了marker発行は0。

事前期待への結合はselected source12本/Python2file。補助観測はsource29本、全233file/178modules/48loaded images、47,594,659bytes。準備前後の追加/消失/変更0、親のdisk/Git照合も一致。全依存の事前profile/完全closureを受け入れたわけではない。

## 試験と資源

全47試験pass、failure/error/skip0、36.157秒。内訳は新API15、既存engineering consumer16、既存pure evidence16で、今回は47件を実際に実行した。役割/mode/operation違い、reader profile混入、source/anchor不一致、出力の再封印・余分なfile、runtime/生成token/保存expectedの変更、依存source欠落、未終了ownerと記録保存失敗を確認した。元入力のbytesは成功/失敗とも保全。

試験harnessのpeak private 50.52MiB、保存例childのpeak 36.24MiB。資料作成前の空きRAM 10.59GiB、commit余裕 19.29GiB、C/D空き 125.95/326.57GiB。 最終保存値はsave-checks.json。30秒/512MiB/監視output1MiB、payload各4/1/2/1MiB・合計8MiBの接続枠で検証した。正式全体予算を変更していない。

候補checkout C:/Users/TKent/.codex/worktrees/ao01/banto-ai はclean2db441e44a65857f288f800a104ba436339358b9。750tracked files/8,498,798bytesをGit blobへ照合済み。前工程rp01を保全。元70b0の既知CRLF差とdirty文書は保持。架空入力原本はtemp cleanup済み、4payload・観測・期待値・monitor/reportを保存した。

## 残件

今回のanalysisは**保存済み記述結果の認証と準備**に限定する。数値consumer/独立auditの実行証明ではない。analysis専用の依存候補profileを別に準備し、後続の小さな保存結果準備が、起動前から保持した全依存一覧に一致するかを検査する。reader profileは使い回さない。 その後の公開、正式文書provenance、独立audit、完全資源予算も未完了。

旧56code/18dataは不変、新module/test2本追加。旧境界/dirty guard/closed/banto-24 PAUSED維持。document_draft.analysis_consumer=null、formal/promotion/S6/trust/execution_authenticated/full closure=false。正式gate/holdout/freeze、principal/UAC/ACL、push/mergeなし。Phase2/3全体は未完了。
